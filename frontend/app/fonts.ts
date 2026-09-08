import localFont from "next/font/local";

/**
 * IBM Plex Sans / Mono — self-hosted (woff2 vendored in ./fonts, latin subset
 * from @fontsource). No external font fetch at build or runtime; the demo works
 * fully offline. `fallback` covers the swap window and any glyph gaps.
 */
export const plexSans = localFont({
  src: [
    { path: "./fonts/IBMPlexSans-400.woff2", weight: "400", style: "normal" },
    { path: "./fonts/IBMPlexSans-500.woff2", weight: "500", style: "normal" },
    { path: "./fonts/IBMPlexSans-600.woff2", weight: "600", style: "normal" },
    { path: "./fonts/IBMPlexSans-700.woff2", weight: "700", style: "normal" },
  ],
  variable: "--font-plex-sans",
  display: "swap",
  fallback: ["Segoe UI", "system-ui", "-apple-system", "Roboto", "sans-serif"],
});

export const plexMono = localFont({
  src: [
    { path: "./fonts/IBMPlexMono-400.woff2", weight: "400", style: "normal" },
    { path: "./fonts/IBMPlexMono-500.woff2", weight: "500", style: "normal" },
    { path: "./fonts/IBMPlexMono-600.woff2", weight: "600", style: "normal" },
  ],
  variable: "--font-plex-mono",
  display: "swap",
  fallback: ["Cascadia Mono", "Consolas", "ui-monospace", "monospace"],
});
