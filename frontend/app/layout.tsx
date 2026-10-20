import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "../styles/globals.css";
import { ThemeProvider } from "@/providers/ThemeProvider";

const geistSans = Geist({
  variable: "--font-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Rinti AI",
  description: "A calm, articulate AI assistant for questions, writing, code and research.",
};

export const viewport: Viewport = {
  colorScheme: "dark light",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#e8f0ec" },
    { media: "(prefers-color-scheme: dark)", color: "#030504" },
  ],
};

// Runs before first paint so there is no flash of the wrong theme. Mirrors the
// logic (and storage keys) of providers/ThemeProvider.tsx.
const themeScript = `(function(){var d=document.documentElement;try{var t=localStorage.getItem('rinti-theme');if(t!=='light'&&t!=='dark'){t=window.matchMedia('(prefers-color-scheme: light)').matches?'light':'dark'}d.dataset.theme=t;if(localStorage.getItem('rinti-reduce-motion')==='1'){d.dataset.motion='reduce'}}catch(e){d.dataset.theme='dark'}})();`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      data-theme="dark"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className="min-h-full bg-page text-fg">
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  );
}
