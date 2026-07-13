import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "IndustryOS | Knowledge Intelligence",
  description: "Enterprise-grade multi-agent reasoning operating system for high-performance industrial assets.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full bg-slate-950">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased h-full text-slate-100 bg-slate-950 font-sans selection:bg-blue-500/30`}
      >
        {/* Master Shell Layout: Establishes a full-viewport, flexible container grid layout */}
        <div className="flex min-h-screen w-full bg-slate-950">
          
          {/* 1. FUTURE WORKSPACE SIDEBAR ANCHOR LOCATION */}
          {/* We pre-fabricate a dark slate border frame panel line where Dhruvin will plant the layout sidebar next */}
          <div className="hidden md:flex md:w-64 md:flex-col md:fixed md:inset-y-0 z-20 bg-slate-900/60 border-r border-slate-800/80 backdrop-blur-md">
            <div className="flex flex-col flex-grow pt-5 overflow-y-auto px-4">
              <div className="flex items-center flex-shrink-0 px-2 py-3 border-b border-slate-800/50">
                <span className="text-xl font-black font-mono tracking-wider text-blue-500">
                  industry<span className="text-slate-100">OS</span>
                </span>
              </div>
              <div className="mt-6 flex-grow flex flex-col">
                <nav className="flex-1 space-y-1">
                  <div className="px-3 py-2 text-xs font-semibold font-mono text-slate-500 uppercase tracking-widest">
                    SYSTEM SHELL ACTIVE
                  </div>
                  <div className="w-full bg-slate-800/40 text-blue-400 group flex items-center px-3 py-2 text-xs font-medium font-mono rounded-lg border border-blue-500/20">
                    📂 Foundation Base Mesh
                  </div>
                </nav>
              </div>
            </div>
          </div>

          {/* 2. CORE APPARATUS WORKSPACE LAYER DISPLAY FRAME */}
          {/* Calculates the padding adjustment matrix offset (md:pl-64) to neatly slide content frames clear of our fixed sidebar */}
          <div className="flex flex-col flex-1 md:pl-64 w-0">
            <main className="flex-1 relative z-0 overflow-y-auto focus:outline-none py-8 px-6 md:px-8">
              <div className="w-full max-w-7xl mx-auto">
                {/* Outgoing page layout child contents are injected precisely right here inside this safety container slot */}
                {children}
              </div>
            </main>
          </div>

        </div>
      </body>
    </html>
  );
}