"use client";

import React, { useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import { Server, ShieldCheck, Database, RefreshCw, AlertTriangle } from "lucide-react";

// Structural TypeScript interface defining our expected server telemetry envelope
interface HealthTelemetry {
  api_engine: string;
  transactional_database_route: string;
  telemetry_handshake: string;
}

export default function Home() {
  const [telemetry, setTelemetry] = useState<HealthTelemetry | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Asynchronous fetch routine to execute our front-to-back handshake check
  const fetchSystemTelemetry = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Hit Rudra's live FastAPI health telemetry endpoint
      const response = await apiClient.get("/api/health");
      setTelemetry(response.data);
    } catch (err: any) {
      setError(err.response?.data?.message || "Failed to establish a network connection link to the API Engine.");
    } finally {
      setLoading(false);
    }
  };

  // Trigger telemetry check immediately when the dashboard view mounts on screen
  useEffect(() => {
    fetchSystemTelemetry();
  }, []);

  return (
    <div className="space-y-6">
      {/* Executive Welcome Dashboard Banner */}
      <div>
        <h1 className="text-3xl font-black tracking-tight text-slate-100">
          Operational Core Control
        </h1>
        <p className="text-sm text-slate-400 mt-1">
          Real-time diagnostics and orchestration grid for IndustryOS multi-agent clusters.
        </p>
      </div>

      {/* Main Core Tracking Frame Container */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3 mt-6">
        
        {/* Card 1: Core API Gateway Status */}
        <div className="p-5 bg-slate-900/40 border border-slate-800/80 rounded-2xl backdrop-blur-md shadow-xl flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono font-bold text-slate-500 uppercase tracking-wider">API Core Router</span>
            <Server className={`h-5 w-5 ${loading ? 'text-slate-500 animate-spin' : error ? 'text-red-400' : 'text-blue-400'}`} />
          </div>
          <div className="mt-4">
            <div className="text-2xl font-black tracking-tight font-mono">
              {loading ? "SCANNING..." : error ? "OFFLINE" : telemetry?.api_engine.toUpperCase()}
            </div>
            <p className="text-xs text-slate-500 mt-1 font-sans">FastAPI Gateway Interface Layer</p>
          </div>
        </div>

        {/* Card 2: Relational Postgres Vault Status */}
        <div className="p-5 bg-slate-900/40 border border-slate-800/80 rounded-2xl backdrop-blur-md shadow-xl flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono font-bold text-slate-500 uppercase tracking-wider">SQL Data Layer</span>
            <Database className={`h-5 w-5 ${loading ? 'text-slate-500 animate-spin' : error ? 'text-red-400' : telemetry?.transactional_database_route === "Online" ? 'text-emerald-400' : 'text-amber-400'}`} />
          </div>
          <div className="mt-4">
            <div className="text-2xl font-black tracking-tight font-mono">
              {loading ? "SCANNING..." : error ? "UNKNOWN" : telemetry?.transactional_database_route.toUpperCase()}
            </div>
            <p className="text-xs text-slate-500 mt-1 font-sans">PostgreSQL Connection Pool Status</p>
          </div>
        </div>

        {/* Card 3: Security Validation Handshake */}
        <div className="p-5 bg-slate-900/40 border border-slate-800/80 rounded-2xl backdrop-blur-md shadow-xl flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono font-bold text-slate-500 uppercase tracking-wider">CORS Perimeter</span>
            <ShieldCheck className={`h-5 w-5 ${loading ? 'text-slate-500 animate-spin' : error ? 'text-red-400' : 'text-purple-400'}`} />
          </div>
          <div className="mt-4">
            <div className="text-2xl font-black tracking-tight font-mono">
              {loading ? "VERFYYNG..." : error ? "REFUSED" : telemetry?.telemetry_handshake.toUpperCase()}
            </div>
            <p className="text-xs text-slate-500 mt-1 font-sans">Cross-Origin Authorization Tokens</p>
          </div>
        </div>

      </div>

      {/* Network Control Interactive Bar */}
      <div className="mt-8 p-4 bg-slate-900/20 border border-slate-800/50 rounded-xl flex items-center justify-between max-w-xl">
        <div className="flex items-center space-x-3">
          <div className={`h-2.5 w-2.5 rounded-full ${error ? 'bg-red-500 animate-pulse' : loading ? 'bg-amber-400 animate-pulse' : 'bg-emerald-400'}`} />
          <span className="text-xs font-mono text-slate-400">
            {error ? "System perimeter handshake disrupted." : loading ? "Synchronizing system telemetry matrix streams..." : "All foundational infrastructure tracks operating nominal."}
          </span>
        </div>
        <button 
          onClick={fetchSystemTelemetry} 
          disabled={loading}
          className="p-2 border border-slate-700 hover:border-slate-500 bg-slate-800/40 hover:bg-slate-800 rounded-lg text-slate-300 transition-all active:scale-95 disabled:opacity-40 disabled:pointer-events-none"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Display Explicit Transport Mismatch Muted Error Warnings */}
      {error && (
        <div className="p-4 border border-red-900/30 bg-red-950/20 rounded-xl max-w-xl flex items-start space-x-3 text-red-400">
          <AlertTriangle className="h-5 w-5 flex-shrink-0 mt-0.5" />
          <div>
            <h4 className="text-sm font-bold font-mono">Transport Connection Disrupted</h4>
            <p className="text-xs text-red-400/80 mt-1 font-sans">{error}</p>
          </div>
        </div>
      )}
    </div>
  );
}