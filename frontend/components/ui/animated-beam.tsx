"use client";

import { useId, useState, useEffect, useCallback, type RefObject } from "react";
import { motion, useReducedMotion } from "motion/react";

// Adapted from the user-supplied AnimatedBeam. Original geometry, gradient,
// and traveling SVG dash are retained; palette, visibility and motion are scoped.
import { cn } from "@/lib/utils";
import "./animated-beam.css";

/* -------------------------------------------------------------------------- */
/*                            ANIMATED BEAM CORE                              */
/* -------------------------------------------------------------------------- */

export interface AnimatedBeamProps {
  className?: string;
  active?: boolean;
  /** One finite pulse; pauses with the page and resets only when unmounted. */
  singlePass?: boolean;
  containerRef: RefObject<HTMLElement | null>;
  fromRef: RefObject<HTMLElement | null>;
  toRef: RefObject<HTMLElement | null>;
  curvature?: number;
  reverse?: boolean;
  pathColor?: string;
  pathWidth?: number;
  pathOpacity?: number;
  beamOpacity?: number;
  glow?: boolean;
  pixelated?: boolean;
  gradientStartColor?: string;
  gradientStopColor?: string;
  delay?: number;
  duration?: number;
  startXOffset?: number;
  startYOffset?: number;
  endXOffset?: number;
  endYOffset?: number;
}

export function AnimatedBeam({
  className,
  active = true,
  singlePass = false,
  containerRef,
  fromRef,
  toRef,
  curvature = 0,
  reverse = false,
  duration = 2.5,
  delay = 0,
  pathColor = "#6bbed2",
  pathWidth = 1.5,
  pathOpacity = 0.14,
  beamOpacity = 1,
  glow = true,
  pixelated = false,
  gradientStartColor = "#6bbed2",
  gradientStopColor = "#6bbed2",
  startXOffset = 0,
  startYOffset = 0,
  endXOffset = 0,
  endYOffset = 0,
}: AnimatedBeamProps) {
  const id = useId().replace(/:/g, "");
  const reducedMotion = useReducedMotion();
  const [pathD, setPathD] = useState("");
  const [svgDimensions, setSvgDimensions] = useState({ width: 0, height: 0 });
  const [gradientCoords, setGradientCoords] = useState({
    x1: "0%",
    y1: "0%",
    x2: "100%",
    y2: "0%",
  });

  const updatePath = useCallback(() => {
    if (containerRef.current && fromRef.current && toRef.current) {
      const containerRect = containerRef.current.getBoundingClientRect();
      const rectA = fromRef.current.getBoundingClientRect();
      const rectB = toRef.current.getBoundingClientRect();

      setSvgDimensions({
        width: containerRect.width,
        height: containerRect.height,
      });

      const startX = rectA.left - containerRect.left + rectA.width / 2 + startXOffset;
      const startY = rectA.top - containerRect.top + rectA.height / 2 + startYOffset;
      const endX = rectB.left - containerRect.left + rectB.width / 2 + endXOffset;
      const endY = rectB.top - containerRect.top + rectB.height / 2 + endYOffset;

      const controlX = (startX + endX) / 2;
      const controlY = (startY + endY) / 2 - curvature;
      const d = `M ${startX},${startY} Q ${controlX},${controlY} ${endX},${endY}`;
      setPathD(d);

      setGradientCoords({
        x1: `${startX}px`,
        y1: `${startY}px`,
        x2: `${endX}px`,
        y2: `${endY}px`,
      });
    }
  }, [containerRef, fromRef, toRef, curvature, startXOffset, startYOffset, endXOffset, endYOffset]);

  useEffect(() => {
    updatePath();
    const resizeObserver = new ResizeObserver(() => updatePath());
    if (containerRef.current) {
      resizeObserver.observe(containerRef.current);
      if (fromRef.current) resizeObserver.observe(fromRef.current);
      if (toRef.current) resizeObserver.observe(toRef.current);
    }
    window.addEventListener("resize", updatePath);
    return () => {
      resizeObserver.disconnect();
      window.removeEventListener("resize", updatePath);
    };
  }, [updatePath, containerRef]);

  return (
    <svg
      aria-hidden="true"
      fill="none"
      width={svgDimensions.width}
      height={svgDimensions.height}
      xmlns="http://www.w3.org/2000/svg"
      className={cn("pointer-events-none absolute inset-0 z-0", className)}
      viewBox={`0 0 ${svgDimensions.width} ${svgDimensions.height}`}
    >
      <defs>
        <linearGradient
          id={id}
          gradientUnits="userSpaceOnUse"
          x1={gradientCoords.x1}
          y1={gradientCoords.y1}
          x2={gradientCoords.x2}
          y2={gradientCoords.y2}
        >
          <stop offset="0%" stopColor={gradientStartColor} stopOpacity="0" />
          <stop offset="25%" stopColor={gradientStartColor} stopOpacity="0.8" />
          <stop offset="60%" stopColor={gradientStopColor} stopOpacity="1" />
          <stop offset="100%" stopColor={gradientStopColor} stopOpacity="0" />
        </linearGradient>

        <filter id={`glow-${id}`} x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="2" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* Static Subdued Baseline Path */}
      <path
        d={pathD}
        stroke={pathColor}
        strokeWidth={pathWidth}
        strokeOpacity={pathOpacity}
        strokeLinecap={pixelated ? "square" : "round"}
        strokeDasharray={pixelated ? "1 7" : undefined}
      />

      {/* Framer Motion Animated Beam Path */}
      {pathD && active && !reducedMotion && singlePass && (
        <path
          className="beam-single-pass"
          d={pathD}
          pathLength={100}
          stroke={gradientStopColor}
          strokeWidth={pathWidth}
          strokeOpacity={beamOpacity}
          strokeLinecap="round"
          strokeDasharray="12 200"
          strokeDashoffset={12}
          filter={glow ? `url(#glow-${id})` : undefined}
          style={{ animationDuration: `${duration}s`, animationDelay: `${delay}s` }}
        />
      )}
      {pathD && active && !reducedMotion && !singlePass && (
        <motion.path
          d={pathD}
          stroke={`url(#${id})`}
          strokeWidth={pathWidth * (pixelated ? 1.5 : 1.8)}
          strokeOpacity={beamOpacity}
          strokeLinecap={pixelated ? "square" : "round"}
          strokeDasharray={pixelated ? "2 198" : "45 155"}
          filter={glow ? `url(#glow-${id})` : undefined}
          initial={{ strokeDashoffset: reverse ? 0 : 200 }}
          animate={{ strokeDashoffset: reverse ? 200 : 0 }}
          transition={{
            duration,
            delay,
            ease: [0.45, 0.05, 0.55, 0.95],
            repeat: Infinity,
            repeatType: "loop",
          }}
        />
      )}
    </svg>
  );
}
