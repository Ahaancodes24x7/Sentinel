import React, { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  ShieldAlert,
  FileText,
  AlertTriangle,
  ShieldX,
  Layers,
  CheckSquare,
  Lightbulb,
  BarChart3,
  Cpu,
  History,
  Settings,
  ChevronLeft,
  ChevronRight,
  Shield,
  Building2,
  HardHat,
  Users,
  Eye,
} from 'lucide-react';
import { authService } from '../../services/authService';

export const Sidebar: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const user = authService.getCurrentUser();
  const location = useLocation();

  const mainNav = [
    { name: 'Overview', path: '/dashboard', icon: LayoutDashboard },
    { name: 'Risk Intelligence', path: '/risk-intelligence', icon: ShieldAlert },
    { name: 'Reports', path: '/reports', icon: FileText },
    { name: 'SIF Precursors', path: '/sif-precursors', icon: AlertTriangle },
    { name: 'Barrier Failures', path: '/barriers', icon: ShieldX },
    { name: 'Patterns', path: '/patterns', icon: Layers },
    { name: 'Life-Saving Rules', path: '/life-saving-rules', icon: CheckSquare },
    { name: 'Recommendations', path: '/recommendations', icon: Lightbulb },
    { name: 'Analytics', path: '/analytics', icon: BarChart3 },
  ];

  const workspaceNav = [
    { name: 'Sites', path: '/risk-intelligence', icon: Building2 },
    { name: 'Assets', path: '/risk-intelligence', icon: HardHat },
    { name: 'Teams', path: '/risk-intelligence', icon: Users },
  ];

  const systemNav = [
    { name: 'Review Queue', path: '/review-queue', icon: Eye },
    { name: 'Model Performance', path: '/model-performance', icon: Cpu },
    { name: 'Audit Log', path: '/audit-log', icon: History },
    { name: 'Settings', path: '/settings', icon: Settings },
  ];

  return (
    <aside
      className={`relative flex flex-col justify-between h-screen bg-slate-950 border-r border-slate-800 transition-all duration-300 z-40 select-none ${collapsed ? 'w-16' : 'w-64'
        }`}
    >
      {/* Brand Header */}
      <div>
        <div className="flex items-center justify-between h-16 px-4 border-b border-slate-800 bg-slate-950/80">
          <div className="flex items-center gap-3 overflow-hidden">
            <div className="p-2 rounded-lg bg-blue-600/20 text-blue-400 border border-blue-500/30 shrink-0">
              <Shield className="w-5 h-5 text-blue-400" />
            </div>
            {!collapsed && (
              <div>
                <div className="flex items-center gap-1.5">
                  <span className="text-base font-black tracking-wider text-white font-telemetry">
                    SENTINEL
                  </span>
                  <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-blue-500/10 text-blue-400 border border-blue-500/30 font-telemetry">
                    AI
                  </span>
                </div>
                <span className="text-[10px] font-medium text-slate-500 tracking-wider block">
                  SAFETY INTELLIGENCE
                </span>
              </div>
            )}
          </div>

          <button
            onClick={() => setCollapsed(!collapsed)}
            className="p-1 rounded text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        </div>

        {/* Navigation Sections */}
        <div className="p-2 space-y-6 overflow-y-auto max-h-[calc(100vh-140px)]">
          {/* Main Nav */}
          <div>
            {!collapsed && (
              <div className="px-3 mb-2 text-[10px] font-bold uppercase tracking-wider text-slate-500 font-telemetry">
                Core Command
              </div>
            )}
            <nav className="space-y-1">
              {mainNav.map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname === item.path;
                return (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    className={`flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-semibold transition-all ${isActive
                        ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30 font-bold shadow-sm'
                        : 'text-slate-400 hover:text-slate-100 hover:bg-slate-900'
                      }`}
                    title={collapsed ? item.name : undefined}
                  >
                    <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-blue-400' : 'text-slate-400'}`} />
                    {!collapsed && <span>{item.name}</span>}
                  </NavLink>
                );
              })}
            </nav>
          </div>

          {/* Workspace Nav */}
          <div>
            {!collapsed && (
              <div className="px-3 mb-2 text-[10px] font-bold uppercase tracking-wider text-slate-500 font-telemetry">
                Workspace
              </div>
            )}
            <nav className="space-y-1">
              {workspaceNav.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.name}
                    to={item.path}
                    className="flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium text-slate-400 hover:text-slate-100 hover:bg-slate-900 transition-colors"
                    title={collapsed ? item.name : undefined}
                  >
                    <Icon className="w-4 h-4 shrink-0 text-slate-500" />
                    {!collapsed && <span>{item.name}</span>}
                  </NavLink>
                );
              })}
            </nav>
          </div>

          {/* System Nav */}
          <div>
            {!collapsed && (
              <div className="px-3 mb-2 text-[10px] font-bold uppercase tracking-wider text-slate-500 font-telemetry">
                System Intelligence
              </div>
            )}
            <nav className="space-y-1">
              {systemNav.map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname === item.path;
                return (
                  <NavLink
                    key={item.name}
                    to={item.path}
                    className={`flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium transition-colors ${isActive
                        ? 'bg-purple-600/20 text-purple-300 border border-purple-500/30 font-bold'
                        : 'text-slate-400 hover:text-slate-100 hover:bg-slate-900'
                      }`}
                    title={collapsed ? item.name : undefined}
                  >
                    <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-purple-400' : 'text-slate-500'}`} />
                    {!collapsed && <span>{item.name}</span>}
                  </NavLink>
                );
              })}
            </nav>
          </div>
        </div>
      </div>

      {/* User Footer */}
      <div className="p-3 border-t border-slate-800 bg-slate-950/90">
        <div className="flex items-center gap-3">
          <div className="relative shrink-0">
            <img
              src={user.avatar}
              alt={user.name}
              className="w-8 h-8 rounded-full border border-slate-700 object-cover"
            />
            <span className="absolute bottom-0 right-0 w-2.5 h-2.5 rounded-full bg-emerald-500 ring-2 ring-slate-950" />
          </div>

          {!collapsed && (
            <div className="overflow-hidden">
              <div className="text-xs font-bold text-slate-200 truncate">{user.name}</div>
              <div className="text-[10px] text-slate-400 truncate uppercase font-telemetry">
                {user.role.replace('_', ' ')}
              </div>
              <div className="text-[10px] text-blue-400 truncate font-semibold">
                {user.organization}
              </div>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
};
