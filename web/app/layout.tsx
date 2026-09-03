import type { Metadata } from "next";
import "@fontsource-variable/archivo";
import "@fontsource/fragment-mono";
import "@fontsource-variable/instrument-sans";
import "@fontsource-variable/newsreader";
import "./globals.css";

export const metadata: Metadata = {
  title: "EchoTrace | One timeline. Every perspective.",
  description: "Align fragmented evidence into one inspectable incident timeline, with the source behind every conclusion.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
