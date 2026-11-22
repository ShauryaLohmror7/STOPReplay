# STOPReplay — architecture and replay frontend

The app lives in `frontend/` on branch `frontend`.

## Open

- Intro and transition: **http://127.0.0.1:5190/**
- Direct architecture: **http://127.0.0.1:5190/?view=architecture**
- Direct replay: **http://127.0.0.1:5190/?view=replay**

```sh
cd frontend
npm ci
npm run dev
```

Use Node.js 22.12+. `npm run build` checks TypeScript and builds production assets; `npm test` checks replay semantics. `npm run preview` serves the build on port 5191.

## Interaction

The first downward scroll reveals the original Electric Gaze portrait over four seconds. After it completes, a light downward scroll disperses the portrait leftward over 2.4 seconds. Cyan eye-light fragments reform into the opening headline, “Replay the breach.” The borderless channel network appears first, with full-color brand logos, faint white connections and the isometric Hairline padlock. Teams messaging and calls share one logo; generic symbols have small labels. A 16px scroll opens the lock fully and sends one brief cyan pulse to Telegram. Returning to the top resets that pulse. The architecture diagram follows below. The original two corner labels retain their cyan color and appear only when the portrait is complete.

Arrow Down, Page Down, and Space provide keyboard equivalents; clicking the portrait surface or activating its accessible button is another option. No extra control text is visible unless keyboard focus is used. Reduced motion shows a still and enters the workspace immediately. The STOP/REPLAY wordmark returns to the black intro.

The architecture presents Research → Store → Analyze → Decide → Contact, a reaction feedback loop, and versioned history feeding read-only replay. Select a module for its responsibility and handoff. The supplied AnimatedBeam component connects all 21 challenge channels to a compact lock tile with static white lines. The lock opens with scrolling. Familiar colored logos lead both sides, while visible channel labels and detail copy are removed. The cyan “Try it for yourself” button opens the replay room. The architecture pause control and reduced-motion preference stop decorative motion.

The persistent navigation links Intro, Architecture, and Replay. The architecture page also links to replay from “Enter the replay” and “Try it for yourself.” Direct links and browser Back/Forward work across all three views.

In replay, choose a run and use the sticky ruler, arrow keys, or playback controls to move through its turns. Agent actions shows each recorded operation, followed by a demo annotation that explains the chosen action and alternatives. Conversation and Artifact show the messages and what appeared on screen. Analysis marks disclosure and verification events and links to the exact source evidence. The pixel memory cube and moving signal packets provide visual feedback and respect the motion toggle and reduced-motion preference. Run 03 demonstrates the empty state. Your position is saved on this device when local storage is available.

## Scope and data

This is a frontend demo with two fictional AI-twin recordings (six and three turns) and an empty recording slot. It makes no model, storage-service, or simulator requests. The log displays recorded sample operations; it does not execute them. The only persistence is the selected run and turn on this device. Source and checkpoint data are fixtures, not a connected database.

`lib/replay-model.ts` and `lib/replay-runs.ts` contain local presentation types, fixtures, and historical projections. These do not establish a shared backend contract. Coordinate the reporting projection with Gary and Shaurya, and historical storage reads with Cem before integration. See [UI structure and handoff](docs/ui-spec.md).

## Files

- `components/architecture/`: architecture presentation, module interactions, channel network, and styles.
- `components/ui/animated-beam.tsx`: adapted from the supplied component, retaining its geometry and animated SVG beam.
- `docs/architecture-plan.md`: presentation structure and scope.
- `components/ui/portrait-reveal.tsx`: reveal and exit choreography, keyboard/touch controls, motion preference.
- `lib/portrait-particles.ts`: WebGL tiles sampled from the exact supplied poster, including cyan light.
- `components/replay/replay-workspace.tsx`: the synchronized recording desk, event index, conversation, artifact view, and execution log.
- `components/replay/trace-workspace.css`: pixel typography, segmented ruler, and responsive recording-desk layout. `replay.css` retains the shared navigation, supplied animation, and fallback primitives.
- `lib/replay-model.ts`: deterministic historical projection and synthetic recording.
- `lib/replay-runs.ts`: isolated run snapshots, incident deduplication, and versioned position restoration.
- `components/ui/run-navigation.tsx`, `components/ui/cursor-cards.tsx`: supplied lamp and cursor-light animations, adapted to the existing theme.
- `lib/replay-insights.ts`: human-authored demo annotations and historical signal markers.
- `tests/replay*.test.mjs`: 14 checks covering historical replay, run isolation, persistence, action order, and signal visibility.

The original artwork and its RGB values are unchanged. Local assets are the supplied [21st.dev poster](https://assets.21st.dev/ascii-recipes/thumbnails/user_2nElBLvklOKlAURm6W1PTu6yYFh/ae758991-0c3f-4c6a-9296-33784c65d43b.webp) and [video](https://assets.21st.dev/ascii-recipes/videos/user_2nElBLvklOKlAURm6W1PTu6yYFh/c458eb38-7f4e-4272-8711-59a86e20d624.mp4). No generated replacement portrait is displayed.

## Verification

TypeScript/production build and all 11 semantic replay tests pass. Safari checks confirmed entry from the intro, the desktop architecture, module selection, channel selection, all 21 channels, cyan button, and a 390px-wide responsive layout. Static WebGL frames at departure 0, 0.76 and 0.9 verified the original portrait, cyan-only travel, and readable particle headline; each reported zero GL errors. The temporary visual-check page was removed after use.

Native scroll injection returns `noWindowsAvailable` in this environment, so precise real-time scroll timing remains a manual check. Reduced-motion and missing-WebGL branches are implemented; OS preference toggling was not part of this verification. Existing replay behavior is covered by its semantic tests and prior browser checks.

The frontend has its own working tree at `/Users/shaur/STOPReplay-frontend` on branch `frontend`, so switching the backend checkout to `integration` does not remove preview source files.


### Borderless channel diagram verification

The production build passes. Safari inspection confirmed the borderless desktop layout, one Teams logo, generic channel captions, the brief explanation, and a 390px layout without horizontal overflow. A small page movement (about 21px) switched the lock to its open target. The preview document reported `visibilityState: hidden`, suspending animation frames, so final spring settling was checked separately with the actual padlock engine: closed → fully open, pause/resume, reduced motion and cleanup all passed. The temporary responsive page and debug attributes were removed. No simulator calls or shared data contracts changed.


### Architecture refinement verification

The pixel departure now takes 2.4 seconds (75% of 3.2 seconds); the initial four-second reveal is unchanged. The architecture uses five unboxed modules, fine static connections and one shared detail readout. Safari checks confirmed desktop, 390px and 320px layouts, no horizontal overflow, module selection and history revision selection. Opening the lock creates exactly one cyan pulse with one animation iteration; returning to the top removes it. The browser preview can suspend animation timing while hidden, so no wall-clock visual playback measurement is claimed. Production build passes; the temporary verification page was removed.

### Replay room — local demo

Open `http://127.0.0.1:5190/?view=replay` or use the architecture page’s “Try it for yourself” button. The supplied spring-lamp navigation selects recordings; its small range control supports dragging between runs. The second range scrubs turns, with previous/next buttons and keyboard arrows. An event index, central conversation/artifact view, and evidence/adaptation inspector share one selected turn. Outcome remains visible below the inspector; scoring context and the execution log expand for detail. The supplied cursor light is retained on the main reading surface.

Run 01 and Run 02 are fictional local recordings; Run 03 demonstrates the empty state. These are not scoring runs or live simulator results. Contacts use the brief’s 10-contact budget. Topic-hit rate, own-angle flags, craft ratings, and official scores remain unavailable until actual scoring records exist. Demo incident classification is not a jury determination. Page opening alone is not counted as a disclosure. No percentage leaked is invented.

Run selection resets to that run’s first turn; the current run/turn is saved locally, including migration from the original single-session position. Rewind hides later evidence, corrections, and outcomes. Scrubbing performs no API, model, or storage-service calls (only local browser position persistence). The cursor light uses MotionValues and a single animation-frame pointer update; reduced-motion and touch users receive static cards. The portrait and architecture animation are unchanged.

Replay browser verification: architecture CTA → replay, switching recordings, range-track selection, keyboard/previous/next navigation, artifact and evidence expansion, empty slot, recovery log, and position restoration after reload all passed. At 390px and 320px, all three cards stack with no horizontal overflow; the temporary read-only diagnostics reported one selected tab, no captured runtime errors, and no fetch/XHR calls. Native drag injection returned `noWindowsAvailable`, so physical continuous dragging was not verified by automation. The native range controls were verified by track clicks and keyboard navigation. The temporary responsive harness was removed.

### Pixel design system

The replay and architecture share `styles/pixel-system.css`: an 8px cursor grid, stepped panel and button edges, Departure Mono labels, and custom 16px filled icons from `components/ui/pixel-icon.tsx`. Long messages and source quotations retain readable body typography. The cursor lighting is dithered into small squares and the supplied spring-lamp selector remains animated.

The event index is another way to select the same turn as the native ruler. Future events reveal only their number until selected; their content and incident/revision markers remain hidden. The ten contact-meter cells represent the current recorded contact count; they are not a decorative success score. Run tabs show their recorded turn counts as small cells. The brand logos and Hairline padlock remain their original artwork.

Pixel-pass verification: production build and all 11 existing replay tests pass. Safari showed the stepped frames, dithered cursor light, pixel icons, indexed timeline, and matching architecture button. Clicking a numbered turn synchronized the panels and hid later event labels. The 390px and 320px replay layouts and 390px architecture layout had no horizontal overflow; the read-only diagnostics reported one selected turn, matching contact cells, no captured errors, and zero fetch/XHR requests. The temporary preview was removed. No commit was created.


### Recording desk redesign

The replay is organized like a timeline inspector: a persistent segmented turn ruler above an event index, a wider conversation, and a detail inspector. Conversation / Rendered artifact and Adaptation / Evidence are independent keyboard-accessible view tabs. Outcome stays beneath the inspector. The header shows contact usage, historical incidents, revisions and recovered turns. All values still come from the same selected run/turn snapshot.

Departure Mono now extends through the replay interface, with discrete ruler ticks, square glyphs, dotted signal/response connections, dithered hover light, and a restrained black/cyan palette. Artifact previews keep their document typography. The original portrait and architecture are unchanged.

Design references: [Replay DevTools](https://docs.replay.io/reference/replay-devtools/overview) for the persistent timeline and event navigation; [Langfuse trace view](https://langfuse.com/changelog/2025-03-19-new-trace-view) for separating navigation from selected-event details; [LangSmith trace views](https://docs.langchain.com/langsmith/view-traces) for keeping conversation and inspection related. These informed the layout, not the visual theme or implementation.

Validation for this redesign: TypeScript/production build and all 11 replay semantic tests pass. Safari desktop review confirmed the new layout, event-index navigation to turn 04, synchronized contact/incident counts, and switching from Adaptation to source Evidence while Outcome remains visible. Browser automation subsequently lost access to windows (`cgWindowNotFound`), including after reconnecting, so the final spacing/type adjustments, responsive layouts, and remaining interactions have not been visually rechecked in this pass. Mobile/tablet rules are implemented, not newly browser-verified. The temporary responsive diagnostics page was removed. Changes remain uncommitted.
