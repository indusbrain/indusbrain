import React from "react";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-6 bg-slate-900">
      <h1 className="text-5xl font-extrabold text-blue-500 mb-2">IndustryOS</h1>
      <p className="text-xl text-slate-400 mb-6">The Operating System for Industrial Knowledge Intelligence</p>
      <div className="p-4 border border-slate-700 bg-slate-800 rounded-xl">
        <span className="text-emerald-400 font-bold">🟢 PRESENTATION PERIMETER: ACTIVE</span>
      </div>
    </main>
  );
}