import type { Metadata } from "next";
import { IBM_Plex_Sans, IBM_Plex_Mono } from "next/font/google";
import { Providers } from "./providers";
import "./globals.css";

const sans = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-plex-sans",
});

const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-plex-mono",
});

export const metadata: Metadata = {
  title: "LaunchGuard AI",
  description: "Deterministic rocket safety inspection and launchpad monitoring co-pilot",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning className={`${sans.variable} ${mono.variable}`}>
      <body suppressHydrationWarning className="min-h-screen bg-background text-foreground font-sans antialiased">
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  );
}
