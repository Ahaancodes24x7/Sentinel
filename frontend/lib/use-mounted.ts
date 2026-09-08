"use client";

import { useEffect, useState } from "react";

/**
 * Flips to true on the next animation frame after mount. Used to trigger CSS
 * chart draw-in transitions from a collapsed initial state. The global
 * `prefers-reduced-motion` rule in globals.css neutralises the transition, so
 * reduced-motion users get the final state with no animation.
 */
export function useMounted(): boolean {
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    const raf = requestAnimationFrame(() => setMounted(true));
    return () => cancelAnimationFrame(raf);
  }, []);
  return mounted;
}
