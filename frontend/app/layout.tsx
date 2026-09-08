import type { Metadata } from "next";
import "./globals.css";
import { plexSans, plexMono } from "./fonts";
import { AuthProvider } from "@/lib/api/auth-store";

export const metadata: Metadata = {
  title: "Sentinel — SIF Precursor Monitor",
  description:
    "HSE review console for Serious Injury & Fatality precursor detection in near-miss safety reports.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${plexSans.variable} ${plexMono.variable}`}>
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
