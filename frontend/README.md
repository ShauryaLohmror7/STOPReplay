# STOPReplay — Electric Gaze intro

A black opening reveals the original 21st.dev Electric Gaze artwork when the viewer scrolls down. One gesture starts a four-second sequence. The finished state plays the exact supplied video, preserving its coarse ASCII texture and cyan eye light. Scrolling upward reverses the assembly. STOP/REPLAY sits at the top left and “A thousand traces. One human.” sits at the bottom right. No silhouette, controls, counters, or progress indicator are displayed.

## Run

Use Node.js 22.12+:

```sh
cd frontend
npm ci
npm run dev
```

The dedicated URL is **http://127.0.0.1:5188/**. The strict port setting prevents this app from silently selecting another port or overlapping a different project.

```sh
npm run build       # Strict TypeScript check and production build
npm run typecheck   # TypeScript only
npm run preview     # Production preview at http://127.0.0.1:5189/
```

## Implementation

- `components/ui/portrait-reveal.tsx`: gesture-triggered Motion timeline, four-second timing, reduced-motion handling, and original video finish.
- `lib/portrait-particles.ts`: WebGL texture fragments sampled from the supplied poster, preserving original RGB colors and ASCII gaps.
- `styles/globals.css`: full-viewport presentation, responsive typography, restrained interface chrome.
- `public/portraits/electric-gaze.webp` and `electric-gaze.mp4`: unmodified local downloads of the user-supplied 21st.dev assets.
- `components/ui/electric-gaze.tsx` and `components/demo.tsx`: retained original supplied component and its unmounted demo.

The former generated portrait is retained in the repository but is no longer displayed. No image generation was used for this revision.

Repeated gestures in the same direction do not accelerate or restart it. Reversing partway takes the proportional duration. Keyboard Page Down/Arrow Down/Space and upward equivalents also work. Touch swipe is supported. Reduced-motion users also start on black; the same gesture shows the original still immediately. Unavailable WebGL uses the same still fallback.

React, TypeScript, Tailwind v4, Motion, Lucide, and IBM Plex Mono are installed. shadcn conventions use `frontend/components/ui`, `components.json`, `@/*`, and `lib/utils.ts`. No backend or API credentials are required. This is the intro only; no disclosure metrics are displayed.

Changing the artwork requires replacing the poster and matching video. The poster prop is selected in `App.tsx`; the video is in `portrait-reveal.tsx`. Optional `children` reserve space below for future integration; no additional section is currently mounted.

## Asset sources

- [Original poster](https://assets.21st.dev/ascii-recipes/thumbnails/user_2nElBLvklOKlAURm6W1PTu6yYFh/ae758991-0c3f-4c6a-9296-33784c65d43b.webp)
- [Original video](https://assets.21st.dev/ascii-recipes/videos/user_2nElBLvklOKlAURm6W1PTu6yYFh/c458eb38-7f4e-4272-8711-59a86e20d624.mp4)

## Verification

Production build and strict TypeScript checks pass. Previous browser checks covered the original cyan-lit artwork and gesture-triggered sequence. The current revision retains only the two corner labels and a four-second reveal. Their placement was visually verified in Chrome.
