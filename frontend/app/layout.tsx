import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "../styles/globals.css";
import { ThemeProvider } from "@/providers/ThemeProvider";
import { LenisProvider } from "@/providers/LenisProvider";
import { AuthProvider } from "@/providers/AuthProvider";

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
  description: "A calm, futuristic desktop assistant.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} dark h-full antialiased`}
      suppressHydrationWarning
    >
      <body className="min-h-full bg-base-black">
        <ThemeProvider>
          <AuthProvider>
            <LenisProvider>{children}</LenisProvider>
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
