"use client";

import {
  forwardRef, useCallback, useEffect, useLayoutEffect, useRef,
  type ComponentPropsWithoutRef, type ComponentProps, type CSSProperties,
} from "react";
import { create, type Figure, type HairlineOptions } from "@/components/ui/padlock-utils/mount";
import { mount as padlockEngine } from "@/components/ui/padlock-utils/padlock-figure";

/**
 * Hairline — Padlock. User-supplied 21st.dev wrapper, with optional controlled
 * opening and pause. Engine: MIT, Lucas Marques; pinned source and license
 * are recorded in padlock-utils/README.md.
 */
const useIsoLayoutEffect = typeof window === "undefined" ? useEffect : useLayoutEffect;
export type HairlinePadlockProps = HairlineOptions & Omit<ComponentPropsWithoutRef<"div">, "children" | keyof HairlineOptions>;

const HairlinePadlock = forwardRef<HTMLDivElement, HairlinePadlockProps>(function HairlinePadlock(props, ref) {
  const { intensity, theme, label, onRead, open, paused, style, ...attrs } = props;
  const named = label ?? props["aria-label"];
  const el = useRef<HTMLDivElement | null>(null);
  const figure = useRef<Figure | null>(null);
  const read = useRef(onRead);
  const set = useCallback((node: HTMLDivElement | null) => {
    el.current = node;
    if (typeof ref === "function") ref(node);
    else if (ref) ref.current = node;
  }, [ref]);

  useIsoLayoutEffect(() => { read.current = onRead; });
  useIsoLayoutEffect(() => {
    const f = create({
      id: "padlock",
      label: "A padlock whose shackle lifts and swings open.",
      rest: "rest",
      engine: padlockEngine,
    }, el.current!, { intensity, theme, label: named, open, paused, onRead: (text) => read.current?.(text) });
    figure.current = f;
    return () => { f.destroy(); figure.current = null; };
    // Mount once; all changing options reach the figure in the effect below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useIsoLayoutEffect(() => {
    figure.current?.update({ intensity, theme, label: named, open, paused });
  }, [intensity, theme, named, open, paused]);

  return <div {...attrs} ref={set} style={{ aspectRatio: "5 / 4", ...style }} />;
});
HairlinePadlock.displayName = "Padlock";

const tokens = {
  "--hairline-plate": "var(--background)",
  "--hairline-hi": "var(--foreground)",
  "--hairline-edge": "var(--muted-foreground)",
  "--hairline-mid": "color-mix(in oklab, var(--muted-foreground) 55%, var(--background))",
  "--hairline-lo": "var(--border)",
} as CSSProperties;

export default function Padlock({ style, ...props }: ComponentProps<typeof HairlinePadlock>) {
  return <HairlinePadlock style={{ ...tokens, ...style }} {...props} />;
}
