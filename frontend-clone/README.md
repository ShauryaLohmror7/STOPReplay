# STOPReplay — experimental replay frontend

Work in this clone. The preserved original remains in `../frontend/` at port 5188.

## Open

- Intro and transition: **http://127.0.0.1:5190/**
- Direct replay: **http://127.0.0.1:5190/?view=replay**

```sh
cd frontend-clone
npm ci
npm run dev
```

Use Node.js 22.12+. `npm run build` checks TypeScript and builds production assets; `npm test` checks replay semantics. `npm run preview` serves the build on port 5191.

## Interaction

The first downward scroll reveals the original Electric Gaze portrait over four seconds. After it completes, a fresh downward scroll disperses the portrait leftward over 2.4 seconds. Cyan fragments converge into the replay timeline while the workspace arrives from the right. The original two corner labels retain their cyan color and appear only when the portrait is complete.

Arrow Down, Page Down, and Space provide keyboard equivalents; a focus-only button also supports keyboard and screen-reader access. Reduced motion shows a still and enters the workspace immediately. The STOP/REPLAY wordmark returns to the black intro.

In replay, select a timeline marker, drag the scrubber, use previous/next, or press Left/Right. One turn drives the conversation, evidence, craft, reasoning, metrics, and execution log. The Evidence tab links the Room B correction back to its earlier Room A finding. The session selector includes an empty-state sample. Position is remembered in localStorage when available.

## Scope and data

This is a frontend demo using six synthetic turns for a fictional AI twin. It makes no model, storage-service, or simulator requests. The log displays recorded sample operations; it does not execute them. The only persistence is the selected turn on this device. Source and checkpoint data are fixtures, not a connected database.

`lib/replay-model.ts` contains local presentation types and fixtures. These do not establish a shared backend contract. Coordinate the reporting projection with Gary and Shaurya, and historical storage reads with Cem before integration. See [UI structure and handoff](docs/ui-spec.md).

## Files

- `components/ui/portrait-reveal.tsx`: reveal and exit choreography, keyboard/touch controls, motion preference.
- `lib/portrait-particles.ts`: WebGL tiles sampled from the exact supplied poster, including cyan light.
- `components/replay/replay-workspace.tsx`: the seven core replay views.
- `components/replay/replay.css`: black/cyan, IBM Plex Mono, responsive layout.
- `lib/replay-model.ts`: deterministic historical projection and synthetic recording.
- `tests/replay.test.mjs`: correction, incident, recovery, storage parsing, and immutable replay checks.

The original artwork and its RGB values are unchanged. Local assets are the supplied [21st.dev poster](https://assets.21st.dev/ascii-recipes/thumbnails/user_2nElBLvklOKlAURm6W1PTu6yYFh/ae758991-0c3f-4c6a-9296-33784c65d43b.webp) and [video](https://assets.21st.dev/ascii-recipes/videos/user_2nElBLvklOKlAURm6W1PTu6yYFh/c458eb38-7f4e-4272-8711-59a86e20d624.mp4). No generated replacement portrait is displayed.

## Verification

TypeScript/production build and the five semantic replay tests pass. Safari checks confirmed the desktop layout, timeline selection, Room B → Room A rewind across panels, recorded email view, incident reasoning, and expandable recovery details. Full scroll choreography and narrow-screen visual checks remain unverified: native browser automation returned `noWindowsAvailable` for scroll input. Responsive CSS and reduced-motion paths are implemented, but this is not a claim that those browser paths were visually checked.
