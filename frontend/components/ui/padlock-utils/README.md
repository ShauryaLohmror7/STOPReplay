# Hairline padlock

Vendored from [lucasmarkes/hairline](https://github.com/lucasmarkes/hairline), commit `bc782244216620434b14736df1d74daed2d05046`, under the MIT license in `LICENSE`.

The user-supplied 21st.dev wrapper references these utilities. The original isometric geometry, spring, shared frame loop, offscreen suspension and reduced-motion behavior are preserved. Local changes rename `figures/padlock.ts` to `padlock-figure.ts` and add optional `open` and `paused` controls through the mount contract. Omitting `open` retains upstream pointer interaction. The channel diagram supplies a closed/open pose after 16px of page scroll; it never changes simulator state.
