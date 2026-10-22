#!/usr/bin/env python3
"""Repeatable renderer microbenchmark; see docs/benchmark.md."""
import argparse
import json
import math
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]


def measure(root, layout, runs):
    os.environ['AGENT_THEME_CELL_RATIO'] = '2.12'
    os.environ['AGENT_THEME_GLYPHS'] = 'octant'
    os.environ['AGENT_THEME_LANG'] = 'zh-Hans'
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(root))
    from agent_theme import art, intro

    brand = art.BRANDS['claude']
    results = {'intro': [], 'ambient': []}
    geometry = None
    for _ in range(runs):
        for phase in results:
            start = time.perf_counter_ns()
            if layout == 'full':
                kwargs = {'lock': art.choose(brand, 111, 55), 'top': 5}
            else:
                # Explicit synthetic chrome, using the same band policy as
                # the observer. No predicted app-specific header geometry.
                occupied = [0] * 55
                for row in (0, 1, 2, 51, 52, 53, 54):
                    occupied[row] = 1
                if hasattr(art, 'choose_band'):
                    lock, start_row, end_row = art.choose_band(brand, 111, 55, occupied)
                else:
                    start_row, end_row = 3, 51
                    lock = art.choose(brand, 111, end_row - start_row)
                kwargs = {'lock': lock, 'top': art.place(lock, start_row, end_row)}
            scene = intro.Bloom(111, 55, art.DARK, brand, **kwargs)
            construction_ms = (time.perf_counter_ns() - start) / 1e6
            scene.rng.seed(7)
            geometry = {'logo': [scene.mark.logo_cols, scene.mark.logo_rows],
                        'word': [scene.mark.word_cols, scene.mark.word_rows],
                        'top': scene.top}
            if phase == 'ambient':
                # Begin with the settled mark already present, as on the home.
                scene.ansi(scene.frame(2.95)).encode('utf-8')
            stamps = ([n / 60 for n in range(177)] if phase == 'intro'
                      else [n / 60 for n in range(60)])
            costs = []
            total_bytes = 0
            for stamp in stamps:
                start = time.perf_counter_ns()
                if phase == 'intro':
                    cells = scene.frame(stamp)
                elif hasattr(scene, 'ambient_frame'):
                    cells = scene.ambient_frame(stamp)
                else:
                    # Historical revisions predate the dedicated ambient API.
                    cells = scene.frame(2.02 + stamp * 0.7)
                output = scene.ansi(cells).encode('utf-8')
                costs.append((time.perf_counter_ns() - start) / 1e6)
                total_bytes += len(output)
            ordered = sorted(costs)
            results[phase].append({
                'frames': len(costs), 'bytes': total_bytes,
                'construction_ms': round(construction_ms, 3),
                'total_ms': round(sum(costs), 3),
                'mean_ms': round(statistics.mean(costs), 3),
                'p95_ms': round(ordered[math.ceil(len(ordered) * 0.95) - 1], 3),
                'peak_ms': round(max(costs), 3),
            })
    return {'python': platform.python_version(), 'platform': platform.platform(),
            'workload': {'columns': 111, 'rows': 55, 'cell_ratio': 2.12,
                         'glyphs': 'octant', 'palette': 'dark',
                         'language': 'zh-Hans', 'seed': 7,
                         'intro_hz': 60, 'ambient_hz': 30,
                         'ambient_api': ('ambient_frame' if hasattr(intro.Bloom, 'ambient_frame')
                                         else 'frame')},
            'layout': layout, 'geometry': geometry, 'runs': results}


def snapshot(ref, destination):
    names = subprocess.check_output(
        ['git', 'ls-tree', '-r', '--name-only', ref, '--', 'agent_theme'],
        cwd=ROOT, text=True).splitlines()
    if not names:
        raise ValueError('ref has no agent_theme package: ' + ref)
    for name in names:
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(subprocess.check_output(
            ['git', 'show', ref + ':' + name], cwd=ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('refs', nargs='*', help='git refs or worktree (default)')
    parser.add_argument('--layout', choices=('full', 'home'), default='full')
    parser.add_argument('--runs', type=int, default=3)
    parser.add_argument('--worker', type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.runs < 1:
        parser.error('--runs must be positive')
    if args.worker is not None:
        print(json.dumps(measure(args.worker, args.layout, args.runs)))
        return
    for ref in args.refs or ['worktree']:
        with tempfile.TemporaryDirectory(prefix='huawei-bloom-benchmark-') as temp:
            source = ROOT if ref == 'worktree' else Path(temp)
            if ref != 'worktree':
                snapshot(ref, source)
            command = [sys.executable, str(Path(__file__).resolve()),
                       '--worker', str(source), '--layout', args.layout,
                       '--runs', str(args.runs)]
            result = json.loads(subprocess.check_output(command, text=True))
            result['ref'] = ref
            print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    main()
