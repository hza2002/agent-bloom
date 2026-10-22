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

## PTY transport baseline

Run the same synthetic TUI directly and through the real wrapper:

```sh
python3 tools/pty_benchmark.py --runs 3 > /tmp/bloom-pty.json
python3 tools/pty_benchmark.py --app codex --runs 3 > /tmp/bloom-codex-pty.json
```

The tool uses only the standard library, a temporary fake app on PATH and owned
PTYs/processes. It does not launch Claude/Codex, contact a model, read conversations
or change application settings. Each direct/wrapped pair uses the same 111 × 55
screen and workload; order alternates between runs. JSON records every session,
parameters, platform, Python version, Git revision and runtime source digest.

The four scenarios are:

- `intro`: control-byte roundtrips spread across the animation interval. The
  probe does not submit a prompt or stop animation. ACKs redraw one location in
  the prompt row so probes do not accidentally scroll and invalidate the screen.
- `home`: settle for 3.5 seconds, drain output for another 2 seconds, then sample
  roundtrip latency. The output count covers only the 2-second home interval;
  CPU still covers the entire session, including startup and the intro.
- `output`: emit 2 MiB of repeated cursor positioning, text and erase controls.
  Verify the expected text-byte count, then measure control-byte roundtrips.
- `paste`: send 2 MiB through the input path and verify the app's SHA-256 receipt,
  then measure control-byte roundtrips.

CPU comes from `wait4` for the owned session leader and descendants whose waited
usage the OS accumulates. App self CPU is also recorded as a cross-check. CPU
seconds and one-core percentages include startup, settling and shutdown; they
are not idle CPU or whole-machine percentages. Throughput measures the declared
workload bytes, including controls for the output workload, divided by the time
until receipt. Roundtrip includes input forwarding, app acknowledgement, output
forwarding and the reader; it is not keyboard-to-photon latency.

The reader continuously drains the outer PTY. This measures the proxy path,
including parsing and generated decoration, but excludes tmux, terminal emulation,
GPU rendering and actual Claude/Codex computation. It complements, rather than
replaces, live terminal checks. The slow-reader/backpressure contracts remain in
`tests/test_integration.py`. Timing is intentionally not a CI pass/fail threshold:
shared runners and desktop load make tight performance assertions unreliable.

## Recorded baseline: 2026-10-21

Apple M1 Max, macOS 26.7.1, Python 3.14.7; runtime commit `e97fe1b`.
Each profile ran three direct/wrapped pairs per scenario, sequentially. Desktop
background activity was not isolated. Values below are medians across runs;
p95 values are the median of each run's 30-sample p95, not a pooled percentile.

| Profile | Measurement | Direct | Wrapped |
| --- | --- | ---: | ---: |
| claude | Intro session CPU | 0.068 s | 0.843 s |
| claude | Intro roundtrip p95 | 1.208 ms | 2.707 ms |
| claude | Home roundtrip p95 | 0.339 ms | 1.634 ms |
| claude | 2 MiB output throughput | 19.603 MiB/s | 15.162 MiB/s |
| claude | 2 MiB paste throughput | 16.091 MiB/s | 5.605 MiB/s |
| codex | Intro session CPU | 0.066 s | 0.914 s |
| codex | Intro roundtrip p95 | 0.794 ms | 8.879 ms |
| codex | Home roundtrip p95 | 2.227 ms | 1.830 ms |
| codex | 2 MiB output throughput | 19.373 MiB/s | 16.097 MiB/s |
| codex | 2 MiB paste throughput | 15.770 MiB/s | 5.506 MiB/s |

Raw sessions: [Claude profile](benchmarks/claude-2026-10-21.json),
[Codex profile](benchmarks/codex-2026-10-21.json). These are synthetic workloads
selected by profile, not timing measurements of the real applications.

The measured overhead is not negligible during animation or sustained transfers.
Intro sessions consumed about 0.84–0.91 CPU seconds through the wrapper versus
0.07 directly, across roughly 3.7 seconds of wall time. Decoration generated
about 2 MB of terminal output per intro. The settled two-second home interval
still emitted about 10 KB for its ambient effect; this is not a zero-work idle.
The home session CPU includes the intro and cannot establish idle-only CPU.

Most roundtrips remain short in this workload, but the dispersion and the Codex
intro tail rule out a claim of universally invisible latency. Bulk paste is
slower through the proxy. These observations justify measuring before changing
frame rates, buffering or parser logic; they are not a machine-independent SLA.
The measurements do not establish visual smoothness or future app compatibility.

## Optimization follow-up: 2026-10-21

The follow-up keeps the same frame rate, artwork and transport queue limits.
Profiling identified repeated wordmark interpolation and gradient coordinate
work; the renderer now reuses settled wordmark cells and per-coordinate colors.
A live palette change updates the wordmark cache. A separate submission bug let
Claude repaint home decoration on each application update, only for the animation
tick to erase it again. Submitted sessions now stop painting until a fresh screen.

Five fixed-workload renderer runs per version, on the same machine:

| Workload | v0.4.2 median total | Optimized median total | Encoded bytes, both |
| --- | ---: | ---: | ---: |
| Intro, 177 frames | 657.770 ms | 559.960 ms | 2,525,119 |
| Ambient, 60 frames | 75.021 ms | 66.866 ms | 350,754 |

This is about 15% and 11% less renderer time respectively. A separate equivalence
experiment compared 64 scenes and 12,224 frames across both brands, light/dark
palettes, octant/quadrant glyphs, four terminal sizes and full/home layouts. Cell
maps and ANSI output matched the original implementation, including invalidation,
backwards time and palette changes. The palette-change regression remains in the
unit suite. [Raw renderer runs](benchmarks/renderer-optimization-2026-10-21.json).

The endpoint benchmark was repeated for both profiles, three runs per scenario:

| Profile | Wrapped output throughput | Wrapped paste throughput | Wrapped intro session CPU |
| --- | ---: | ---: | ---: |
| Claude | 15.645 MiB/s | 5.546 MiB/s | 0.925 s |
| Codex | 16.269 MiB/s | 5.587 MiB/s | 0.846 s |

[Claude sessions](benchmarks/claude-optimized-2026-10-21.json) and
[Codex sessions](benchmarks/codex-optimized-2026-10-21.json) retain the control runs,
all latencies and the exact runtime source hash. Host load was not isolated;
whole-session intro CPU and tail latencies did not improve consistently. The
renderer result therefore must not be advertised as a 15% end-to-end improvement.
The opening still sends roughly 2 MB of terminal output. Paste throughput remains
around 5.5 MiB/s versus roughly 16 MiB/s directly.

The Claude paste scenario includes 30 acknowledgements after submission. Its
terminal output fell from roughly 1.26 MB to 9 KB once repeated home repainting
was removed. A regression first failed on the original code, then verified no
repainting across those updates and successful rearming on `/clear`.

One candidate was deliberately rejected: processing printable input in bulk
reduced a 2 MiB observer microbenchmark from about 219 ms to 15 ms, but reduced
complete paste throughput from about 5.5 MiB/s to 3–4 MiB/s in repeated macOS
runs. Profiling showed more time in PTY writes; the precise kernel/scheduling
interaction is not established. Smaller writes, opportunistic batching and
waiting for the input queue to drain did not yield a stable endpoint benefit.
The original input observer and transport remain in place. No sleeps, platform
special cases or throughput-based correctness-test thresholds were introduced.

## Input protocol validation (2026-10-21)

The incremental input observer fixes split controls and bracketed paste. Its
first implementations regressed the existing 2 MiB ASCII paste scenario:
printable-run batching measured 3.54–4.03 MiB/s and a generic scalar state loop
3.33–3.36 MiB/s. Neither implementation was retained. The final implementation
decodes UTF-8 once per read and handles ordinary text before control states.
It keeps the bounded candidate and full protocol checks, without regex batching.

Three direct/wrapped pairs per version on the same host, using
`python3 tools/pty_benchmark.py --app claude --scenario paste --runs 3`:

| Runtime | Direct MiB/s (three runs) | Wrapped MiB/s (three runs) |
| --- | --- | --- |
| `ae30a79` | 16.010, 16.112, 16.069 | 5.595, 5.640, 5.618 |
| Input protocol + pending-wrap changes | 15.993, 16.163, 15.569 | 5.963, 5.977, 5.895 |

All paste hashes matched. This small synthetic comparison finds no throughput
regression in the retained implementation; it does not establish a general
performance improvement, real-editor responsiveness, or in-transfer latency.
The phase/transport attribution work described above remains necessary.

The later text-boundary safety change also updates the synthetic workload to
finish its home and ping output with an explicit input-cursor position, matching
the captured applications. This is required to keep animation eligible while
measuring it. Historical byte totals precede that workload adjustment; they are
not directly comparable to new results without rerunning both runtimes against
the same workload. No additional throughput optimization is claimed here.
