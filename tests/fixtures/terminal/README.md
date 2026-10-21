# Real terminal recordings

These fixtures were captured from fresh Claude Code 2.1.304 and Codex CLI
0.163.0 processes on macOS through tmux 3.8 `pipe-pane` on 2026-10-21.
They contain application output, not Bloom output or screenshots. Each starts
at 111 × 55 cells, resizes to 93 × 45, then receives `/clear` and Enter.
Claude's recording includes its response; Codex's ends while `/clear` remains
visible in its input. The fixtures do not prove Codex completed that command.

Letters and numbers in displayed text were masked with nonblank glyphs of the
same approximate codepoint width. CSI/ESC controls were retained; text inside
OSC payloads was masked. This preserves occupancy better than replacing text
with spaces, but does not preserve app-specific header recognition, grapheme
semantics, OSC payload semantics, or original byte lengths. These recordings
exercise the screen observer, not the header replacer or visual appearance.
No conversations, credentials, original paths or account names are retained.

Checkpoints assert alternate-screen entry and a known screen after the captured
clear operations. A resize checkpoint requires the observer to forget its screen
before the app repaints. Replay at 1, 7, 4096 and 1048576-byte chunk sizes checks
application-byte preservation and safety-state consistency. Extra synchronization
wrappers are allowed; their bytes are indistinguishable from identical app
wrappers, so this is not proof of arbitrary terminal-state transparency.

## Adding a version

1. Open a new disposable tmux session with a known size, in a non-sensitive
   working directory. Attach `tmux pipe-pane` before starting the real app.
   Do not record an existing conversation. Do not change application config to
   force a particular renderer; record whether the default is inline or full screen.
2. Record startup, resize, and local UI actions. Record output offsets at each
   action boundary and the sizes/inputs needed to reproduce them. A raw dump alone
   does not reconstruct input, resize, or timing events. Test resume and model
   submission separately with an explicitly disposable session when appropriate.
3. Review raw bytes privately, including OSC titles and hyperlinks. Import with
   `python3 tools/terminal_trace.py RAW FIXTURE --app claude --app-version VERSION
   --cols 111 --rows 55 --note 'method and covered actions'`. Exact `--redact`
   strings are a convenience, not automatic secret detection. Review decoded
   output before setting `--reviewed-sanitized`; base64 is not anonymization.
4. Split output events at recorded boundaries, add input/resize events and
   independent checkpoints using the version 1 format in the existing fixtures.
   Preserve provenance and explicitly label omissions. Never present invented
   sequences as recordings.
5. Run `python3 -B -m unittest discover -s tests -p test_replay.py -q`, then the
   full suite. Inspect a live terminal as well: replay does not emulate tmux or
   Ghostty and does not judge appearance.

Resume, model-response rendering, complex emoji, alternate terminal backends,
and real input-to-display latency are not covered by these two recordings.
