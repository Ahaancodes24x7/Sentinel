import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield, ArrowRight } from 'lucide-react';
import { authService } from '../services/authService';
import type { UserRole } from '../types/sentinel';

export const LoginPage: React.FC = () => {
  const [email, setEmail] = useState('vance@shell.com');
  const [password, setPassword] = useState('••••••••••••');
  const [selectedRole, setSelectedRole] = useState<UserRole>('hse_manager');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await authService.login(email, selectedRole);
      navigate('/dashboard');
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen w-screen bg-[#0b0f17] text-slate-100 flex items-center justify-center p-4 bg-telemetry-grid relative overflow-hidden">
      {/* Glow Orbs */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-600/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-600/10 rounded-full blur-3xl pointer-events-none" />

      <div className="relative w-full max-w-md overflow-hidden rounded-2xl bg-slate-900/90 border border-slate-800 p-8 shadow-2xl space-y-6">
        {/* Brand Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex p-3 rounded-xl bg-blue-600/20 text-blue-400 border border-blue-500/30 mb-2">
            <Shield className="w-8 h-8 text-blue-400" />
          </div>
          <h1 className="text-2xl font-black tracking-wider text-white font-telemetry uppercase">
            SENTINEL
          </h1>
          <p className="text-xs text-slate-400 font-medium">
            AI-Powered Safety Intelligence & SIF Precursor Detection
          </p>
        </div>

        {/* Demo Role Fast Selector */}
        <div className="space-y-1.5">
          <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-400 font-telemetry">
            Select Enterprise Role Profile:
          </label>
          <div className="grid grid-cols-2 gap-2 text-xs font-telemetry">
            {[
              { role: 'hse_manager', label: 'HSE Manager (Shell)' },
              { role: 'hse_analyst', label: 'HSE Analyst (Exxon)' },
              { role: 'hse_reviewer', label: 'HSE Reviewer (BP)' },
              { role: 'auditor', label: 'Auditor (ONGC)' },
            ].map((item) => (
              <button
                key={item.role}
                type="button"
                onClick={() => setSelectedRole(item.role as UserRole)}
                className={`p-2 rounded-lg border text-left transition-all ${selectedRole === item.role
                    ? 'bg-blue-600/20 border-blue-500 text-white font-bold'
                    : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'
                  }`}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 mb-1 font-telemetry">
              Corporate Email:
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-200 focus:outline-none focus:border-blue-500 font-telemetry"
            />
          </div>

          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 mb-1 font-telemetry">
              Password:
            </label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-200 focus:outline-none focus:border-blue-500 font-telemetry"
            />
          </div>

          <div className="flex items-center justify-between text-xs text-slate-400">
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" defaultChecked className="rounded bg-slate-950 border-slate-800" />
              <span>Remember session</span>
            </label>
            <a href="#forgot" onClick={(e) => { e.preventDefault(); alert('Password reset link dispatched.'); }} className="text-blue-400 hover:underline">
              Forgot password?
            </a>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs shadow-lg uppercase tracking-wider font-telemetry transition-all flex items-center justify-center gap-2"
          >
            {loading ? 'Authenticating...' : 'Sign In to Command Center'} <ArrowRight className="w-4 h-4" />
          </button>
        </form>

        <div className="pt-2 text-center text-[10px] text-slate-500 font-telemetry">
          SENTINEL v2.4 • Oil & Gas Industrial Safety Intelligence Platform
        </div>
      </div>
    </div>
  );
};
