import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
// Ingest the high-performance SVG vector icons from our library layer
import { 
  LayoutDashboard, 
  Activity, 
  Network, 
  Database, 
  Layers, 
  Cpu 
} from "lucide-react";

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
        {/* Master Shell Layout: Establishes a full-viewport container grid */}
        <div className="flex min-h-screen w-full bg-slate-950">
          
          {/* 1. PERSISTENT NAVIGATION SIDEBAR FRAME PANEL */}
          <div className="hidden md:flex md:w-64 md:flex-col md:fixed md:fixed md:inset-y-0 z-20 bg-slate-900/60 border-r border-slate-800/60 backdrop-blur-md">
            <div className="flex flex-col flex-grow pt-5 overflow-y-auto px-4">
              
              {/* Brand Header Identifier */}
              <div className="flex items-center flex-shrink-0 px-2 py-4 border-b border-slate-800/50 space-x-2">
                <Cpu className="h-6 w-6 text-blue-500 animate-pulse" />
                <span className="text-xl font-black font-mono tracking-wider text-blue-500">
                  industry<span className="text-slate-100">OS</span>
                </span>
              </div>

              {/* Navigation Elements Grid Mapping */}
              <div className="mt-8 flex-grow flex flex-col">
                <nav className="flex-1 space-y-2">
                  <div className="px-3 py-1 text-xs font-bold font-mono text-slate-500 uppercase tracking-widest">
                    Operational Control
                  </div>
                  
                  {/* Dashboard Route Hub Anchor */}
                  <div className="w-full bg-slate-800/50 text-blue-400 group flex items-center px-3 py-2.5 text-sm font-medium font-mono rounded-xl border border-blue-500/20 shadow-md cursor-pointer transition-all hover:bg-slate-800/80">
                    <LayoutDashboard className="mr-3 h-5 w-5 text-blue-500" />
                    Core Platform Panel
                  </div>

                  {/* Telemetry Status Monitoring Anchor */}
                  <div className="w-full text-slate-400 hover:text-slate-200 group flex items-center px-3 py-2.5 text-sm font-medium font-mono rounded-xl transition-all hover:bg-slate-800/40 cursor-pointer">
                    <Activity className="mr-3 h-5 w-5 text-slate-500 group-hover:text-emerald-400 transition-colors" />
                    Telemetry Status
                  </div>

                  {/* Relational Relational Graph Matrix Anchor */}
                  <div className="w-full text-slate-400 hover:text-slate-200 group flex items-center px-3 py-2.5 text-sm font-medium font-mono rounded-xl transition-all hover:bg-slate-800/40 cursor-pointer">
                    <Network className="mr-3 h-5 w-5 text-slate-500 group-hover:text-purple-400 transition-colors" />
                    Knowledge Graph
                  </div>

                  {/* Transactional / Vector Data Registry Anchor */}
                  <div className="w-full text-slate-400 hover:text-slate-200 group flex items-center px-3 py-2.5 text-sm font-medium font-mono rounded-xl transition-all hover:bg-slate-800/40 cursor-pointer">
                    <Database className="mr-3 h-5 w-5 text-slate-500 group-hover:text-amber-400 transition-colors" />
                    Database Vaults
                  </div>

                </nav>
              </div>

              {/* System Execution Context Footer Card */}
              <div className="flex-shrink-0 p-4 border-t border-slate-800/50 mb-4 bg-slate-950/40 rounded-xl border border-slate-800/80">
                <div className="flex items-center space-x-2">
                  <Layers className="h-4 w-4 text-emerald-500" />
                  <span className="text-xs font-mono text-slate-400">
                    Data Layer: <span className="text-emerald-400 font-bold">Secure</span>
                  </span>
                </div>
              </div>

            </div>
          </div>

          {/* 2. CORE APPARATUS WORKSPACE VIEWPORT LAYER DISPLAY FRAME */}
          <div className="flex flex-col flex-1 md:pl-64 w-0">
            <main className="flex-1 relative z-0 overflow-y-auto focus:outline-none py-8 px-6 md:px-8">
              <div className="w-full max-w-7xl mx-auto">
                {children}
              </div>
            </main>
          </div>

        </div>
      </body>
    </html>
  );
}