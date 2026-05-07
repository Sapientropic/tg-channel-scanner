# Demo Maintenance

The public demo artifacts are:

- `docs/demo.mp4` - full 49 second product demo with audio.
- `docs/demo.gif` - README preview generated from the same video.

The editable HyperFrames source lives in `docs/demo/index.html`,
`docs/demo/compositions/`, `docs/demo/assets/`, and `docs/demo/fixtures/`.
Ignored render folders and one-off agent handoff files are not source of truth.

Before replacing the public artifacts, verify from the repository root:

```bash
npx --yes hyperframes@0.5.3 lint --json
npx --yes hyperframes@0.5.3 inspect --at 20,32,33 --json
ffprobe docs/demo.mp4
```

HyperFrames rendering in this project does not currently include the final audio
track. If the visual track is re-rendered, mux the approved AAC audio back into
`docs/demo.mp4`, or add a maintained audio pipeline before replacing it.
