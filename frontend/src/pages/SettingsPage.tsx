import React, { useState } from 'react';
import { Settings, Server, Shield, CheckCircle2 } from 'lucide-react';
import { authService } from '../services/authService';

export const SettingsPage: React.FC = () => {
  const [apiUrl, setApiUrl] = useState(import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1');
  const [saved, setSaved] = useState(false);
  const currentUser = authService.getCurrentUser();

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  return (
    <div className="space-y-6 max-w-4xl font-telemetry">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-slate-800 font-sans">
        <div>
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
              <Settings className="w-5 h-5" />
            </div>
            <h2 className="text-xl font-black text-slate-100 uppercase tracking-tight font-telemetry">
              System Settings & Integration
            </h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Configure backend FastAPI connections, model inference parameters, and user roles.
          </p>
        </div>
      </div>

      {saved && (
        <div className="p-3 rounded-lg bg-emerald-950/40 border border-emerald-800 text-xs text-emerald-300 flex items-center gap-2 font-sans">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          Settings updated successfully!
        </div>
      )}

      <form onSubmit={handleSave} className="space-y-6 font-sans">
        {/* Backend API Connection */}
        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-4">
          <div className="flex items-center gap-2 font-telemetry text-sm font-extrabold uppercase text-slate-100 border-b border-slate-800 pb-2">
            <Server className="w-4 h-4 text-blue-400" />
            Backend FastAPI Integration
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-300 uppercase font-telemetry mb-1">
              Sentinel API Base URL:
            </label>
            <input
              type="text"
              value={apiUrl}
              onChange={(e) => setApiUrl(e.target.value)}
              className="w-full p-2.5 rounded bg-slate-950 border border-slate-800 text-xs text-slate-200 font-telemetry focus:outline-none focus:border-blue-500"
            />
            <p className="text-[11px] text-slate-500 mt-1">
              Default target is <code>http://localhost:8000/api/v1</code>. When unreachable, frontend automatically falls back to offline mock dataset.
            </p>
          </div>
        </div>

        {/* User Identity & Role */}
        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-4">
          <div className="flex items-center gap-2 font-telemetry text-sm font-extrabold uppercase text-slate-100 border-b border-slate-800 pb-2">
            <Shield className="w-4 h-4 text-purple-400" />
            Active Session Identity
          </div>

          <div className="grid grid-cols-2 gap-4 text-xs font-telemetry">
            <div>
              <span className="text-slate-500 block">User Name:</span>
              <span className="font-bold text-slate-100 text-sm">{currentUser.name}</span>
            </div>
            <div>
              <span className="text-slate-500 block">Role Scope:</span>
              <span className="font-bold text-purple-400 uppercase text-sm">{currentUser.role}</span>
            </div>
            <div>
              <span className="text-slate-500 block">Organization:</span>
              <span className="font-bold text-blue-400 text-xs">{currentUser.organization}</span>
            </div>
            <div>
              <span className="text-slate-500 block">Default Facility:</span>
              <span className="font-bold text-slate-200 text-xs">{currentUser.site}</span>
            </div>
          </div>
        </div>

        <div className="flex justify-end">
          <button
            type="submit"
            className="px-6 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs shadow-lg font-telemetry uppercase tracking-wide transition-all"
          >
            Save Settings
          </button>
        </div>
      </form>
    </div>
  );
};
