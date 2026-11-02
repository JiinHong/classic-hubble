"use client";

import { useLayoutEffect, useRef, type ComponentPropsWithoutRef } from "react";

type Props = Omit<ComponentPropsWithoutRef<"span">, "children"> & { children: string };

export function SingleLineText({ children, className = "", ...props }: Props) {
  const container = useRef<HTMLSpanElement>(null);
  const text = useRef<HTMLSpanElement>(null);

  useLayoutEffect(() => {
    const box = container.current;
    const label = text.current;
    if (!box || !label) return;
    let disposed = false;
    const fit = () => {
      if (disposed) return;
      // Measure at the inherited size so widening restores the original type size.
      label.style.fontSize = "";
      const available = box.clientWidth;
      const natural = label.getBoundingClientRect().width;
      if (available > 0 && natural > available) {
        const size = parseFloat(getComputedStyle(label).fontSize);
        label.style.fontSize = `${Math.floor(size * available / natural * 100) / 100}px`;
      }
    };
    fit();
    const observer = typeof ResizeObserver === "undefined" ? undefined : new ResizeObserver(fit);
    observer?.observe(box);
    document.fonts?.ready.then(fit);
    document.fonts?.addEventListener("loadingdone", fit);
    return () => {
      disposed = true;
      observer?.disconnect();
      document.fonts?.removeEventListener("loadingdone", fit);
    };
  }, [children]);

  return <span {...props} ref={container} className={`block min-w-0 overflow-hidden ${className}`}>
    <span ref={text} className="inline-block whitespace-nowrap">{children}</span>
  </span>;
}
