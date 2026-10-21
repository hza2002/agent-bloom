# Renderer benchmark

Run from the checkout with Python 3.9+ and Git:

```sh
python3 tools/benchmark.py v0.4.1 8bd48b7 worktree
python3 tools/benchmark.py --layout home --runs 5 worktree
```

The script uses only the standard library. Each source runs in a separate Python
process. Git refs are copied to a temporary directory; the checkout is untouched.
`worktree` uses the current package, including uncommitted changes. Output contains
one JSON object per source, with every run reported separately.

The fixed workload is Claude art at 111 columns × 55 rows, a 2.12 cell height/width
ratio, octant glyphs, the dark palette, simplified Chinese, and random seed 7.
The default `full` layout passes `art.choose(brand, 111, 55)` and `top=5` explicitly.
This is a renderer stress workload, not the actual available home area inside an
application. `--layout home` uses Bloom's default predicted header/input layout;
it produces a smaller mark. Geometry is included in the output.

Each run builds a fresh scene for each phase:

- Intro: 177 samples at `t=n/60`, for `0 <= n < 177` (2.95 seconds at 60 Hz).
- Ambient: 60 samples at `t=2.02 + (n/30/2)*0.7`, for `0 <= n < 60`
  (a two-second sweep at 30 Hz). A settled frame is rendered before measurement
  so that the home is already present in the diff cache.

Both old and new sources receive exactly these samples. This compares renderers,
not their historical scheduling frequencies. Each measured sample includes
`scene.frame(t)`, `scene.ansi(cells)`, and UTF-8 encoding. Byte counts are encoded
ANSI output, without the overlay's outer cursor-save/restore envelope. Scene
construction is timed separately. Frame times report arithmetic mean, nearest-rank
p95, peak, and total; all times are milliseconds. Compare all runs on the same
machine and Python build, avoiding other CPU-intensive work. Byte counts should
be stable; timing and first-run costs naturally vary.

This microbenchmark does not run a PTY, the screen model, deadline pacing, terminal
emulation, or actual display refresh. It cannot establish end-to-end frame latency,
input latency, or whether 30/60 Hz looks better. Those require a live terminal
workload. In particular, a peak below 16.67 ms here leaves only part of a 60 Hz
frame budget for the other work.
