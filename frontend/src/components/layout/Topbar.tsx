import React, { useState, useEffect } from 'react';
import {
  Search,
  Bell,
  Building2,
  Calendar,
  Clock,
  LogOut,
  ChevronDown,
  Brain,
  FileQuestion,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { authService } from '../../services/authService';
import { CommandPalette } from '../common/CommandPalette';
import { HowSentinelThinksModal } from '../common/HowSentinelThinksModal';
import { ReportQualityModal } from '../common/ReportQualityModal';
import type { UserRole } from '../../types/sentinel';

interface TopbarProps {
  pageTitle: string;
  selectedSite: string;
  onSiteChange: (site: string) => void;
}

export const Topbar: React.FC<TopbarProps> = ({
  pageTitle,
  selectedSite,
  onSiteChange,
}) => {
  const [timeStr, setTimeStr] = useState('');
  const [dateStr, setDateStr] = useState('');
  const [cmdOpen, setCmdOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);
  const [methodologyOpen, setMethodologyOpen] = useState(false);
  const [reportQualityOpen, setReportQualityOpen] = useState(false);

  const currentUser = authService.getCurrentUser();
  const navigate = useNavigate();

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setTimeStr(
        now.toLocaleTimeString('en-US', {
          hour12: false,
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
          timeZoneName: 'short',
        })
      );
      setDateStr(
        now.toLocaleDateString('en-US', {
          day: '2-digit',
          month: 'short',
          year: 'numeric',
        })
      );
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const handleRoleSwitch = (role: UserRole) => {
    authService.setRole(role);
    setProfileOpen(false);
    window.location.reload();
  };

  const handleLogout = () => {
    authService.logout();
    navigate('/login');
  };

  const sites = [
    'All Sites',
    'North Refinery',
    'Processing Unit 4',
    'Rig 4',
    'Deepwater Alpha',
    'Plant C',
    'Offshore Platform B',
  ];

  return (
    <>
      <header className="h-16 bg-slate-950/90 border-b border-slate-800 px-6 flex items-center justify-between z-30 sticky top-0 backdrop-blur-md">
        {/* Left: Page Title & Governance Badge */}
        <div className="flex items-center gap-3">
          <h1 className="text-base font-bold text-slate-100 tracking-wide font-telemetry uppercase">
            {pageTitle}
          </h1>
          <span className="text-slate-700">|</span>
          {/* Transparency disclosure badge */}
          <div className="hidden lg:flex items-center space-x-1.5 px-2.5 py-0.5 rounded bg-blue-500/10 border border-blue-500/20 text-[11px] font-telemetry text-blue-300">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
            <span className="font-bold">SYNTHETIC DEMONSTRATION DATASET</span>
            <span className="text-slate-400">| Approved Interfaces</span>
          </div>
        </div>

        {/* Center: Global Search Bar */}
        <div className="flex-1 max-w-md mx-4 hidden md:block">
          <button
            onClick={() => setCmdOpen(true)}
            className="w-full flex items-center justify-between px-3.5 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:border-slate-700 hover:text-slate-200 text-xs transition-colors"
          >
            <div className="flex items-center gap-2">
              <Search className="w-3.5 h-3.5 text-blue-400" />
              <span>Search reports, hazards, sites, SIF patterns...</span>
            </div>
            <kbd className="px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-[10px] font-telemetry font-bold text-slate-300">
              ⌘K / Ctrl+K
            </kbd>
          </button>
        </div>

        {/* Right Controls */}
        <div className="flex items-center gap-3">
          {/* Methodology Trigger */}
          <button
            onClick={() => setMethodologyOpen(true)}
            className="hidden sm:flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-cyan-500/10 hover:bg-cyan-500/20 border border-cyan-500/30 text-cyan-300 text-xs font-telemetry font-bold transition-colors"
            title="How Sentinel Thinks"
          >
            <Brain className="w-3.5 h-3.5" />
            <span>How Sentinel Thinks</span>
          </button>

          {/* Report Quality Trigger */}
          <button
            onClick={() => setReportQualityOpen(true)}
            className="hidden xl:flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 text-amber-300 text-xs font-telemetry font-bold transition-colors"
            title="Report Quality & Completeness"
          >
            <FileQuestion className="w-3.5 h-3.5" />
            <span>Report Quality</span>
          </button>

          {/* Site Selector */}
          <div className="relative">
            <div className="flex items-center gap-1.5 bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1 text-xs">
              <Building2 className="w-3.5 h-3.5 text-amber-400" />
              <select
                value={selectedSite}
                onChange={(e) => onSiteChange(e.target.value)}
                className="bg-transparent text-slate-200 text-xs font-semibold focus:outline-none cursor-pointer"
              >
                {sites.map((s) => (
                  <option key={s} value={s} className="bg-slate-900 text-slate-200">
                    {s}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Date / Time Telemetry */}
          <div className="hidden 2xl:flex items-center gap-3 text-xs font-telemetry text-slate-400 bg-slate-900/60 border border-slate-800 px-3 py-1 rounded-lg">
            <span className="flex items-center gap-1">
              <Calendar className="w-3.5 h-3.5 text-blue-400" />
              {dateStr}
            </span>
            <span className="text-slate-700">|</span>
            <span className="flex items-center gap-1 text-slate-200 font-bold">
              <Clock className="w-3.5 h-3.5 text-emerald-400" />
              {timeStr}
            </span>
          </div>

          {/* Notification Bell */}
          <div className="relative">
            <button
              onClick={() => setNotifOpen(!notifOpen)}
              className="relative p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
            >
              <Bell className="w-4 h-4" />
              <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full ring-2 ring-slate-950" />
            </button>

            {notifOpen && (
              <div className="absolute right-0 mt-2 w-80 rounded-xl bg-slate-900 border border-slate-700 shadow-2xl p-3 z-50 animate-in fade-in zoom-in-95">
                <div className="flex items-center justify-between pb-2 border-b border-slate-800 text-xs font-bold uppercase tracking-wider text-slate-300">
                  <span>Live Safety Alerts</span>
                  <span className="text-[10px] text-red-400 font-telemetry font-extrabold">2 NEW</span>
                </div>
                <div className="mt-2 space-y-2 text-xs">
                  <div className="p-2 rounded bg-red-950/30 border border-red-900/40 text-red-200">
                    <div className="font-bold text-red-400">CRITICAL SIF PRECURSOR</div>
                    <p className="text-[11px] text-slate-300 mt-0.5">
                      Working at Height unclipped lanyard detected at North Refinery (SR-10482).
                    </p>
                    <span className="text-[10px] text-slate-500 font-telemetry">18 minutes ago</span>
                  </div>
                  <div className="p-2 rounded bg-amber-950/30 border border-amber-900/40 text-amber-200">
                    <div className="font-bold text-amber-400">Barrier Degradation Alert</div>
                    <p className="text-[11px] text-slate-300 mt-0.5">
                      Energy Isolation failure rate exceeded baseline by +131% at Rig 4.
                    </p>
                    <span className="text-[10px] text-slate-500 font-telemetry">1 hour ago</span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* User Profile Dropdown */}
          <div className="relative">
            <button
              onClick={() => setProfileOpen(!profileOpen)}
              className="flex items-center gap-2 p-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-200 hover:bg-slate-800 transition-colors"
            >
              <img
                src={currentUser.avatar}
                alt={currentUser.name}
                className="w-6 h-6 rounded-full border border-slate-700 object-cover"
              />
              <span className="text-xs font-bold truncate max-w-[100px] hidden md:inline-block">
                {currentUser.name.split(' ')[0]}
              </span>
              <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
            </button>

            {profileOpen && (
              <div className="absolute right-0 mt-2 w-64 rounded-xl bg-slate-900 border border-slate-700 shadow-2xl p-3 z-50">
                <div className="pb-2 mb-2 border-b border-slate-800">
                  <div className="text-xs font-bold text-slate-100">{currentUser.name}</div>
                  <div className="text-[11px] text-blue-400 font-telemetry uppercase font-semibold">
                    {currentUser.role.replace('_', ' ')}
                  </div>
                  <div className="text-[11px] text-slate-400">{currentUser.organization}</div>
                </div>

                <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-1 font-telemetry">
                  Switch Demo Role
                </div>
                <div className="space-y-1 mb-2 text-xs">
                  <button
                    onClick={() => handleRoleSwitch('hse_manager')}
                    className="w-full text-left px-2.5 py-1.5 rounded text-slate-300 hover:bg-slate-800 hover:text-white flex items-center justify-between"
                  >
                    <span>HSE Manager</span>
                    {currentUser.role === 'hse_manager' && <span className="text-emerald-400 font-bold">✓</span>}
                  </button>
                  <button
                    onClick={() => handleRoleSwitch('hse_analyst')}
                    className="w-full text-left px-2.5 py-1.5 rounded text-slate-300 hover:bg-slate-800 hover:text-white flex items-center justify-between"
                  >
                    <span>HSE Analyst</span>
                    {currentUser.role === 'hse_analyst' && <span className="text-emerald-400 font-bold">✓</span>}
                  </button>
                  <button
                    onClick={() => handleRoleSwitch('hse_reviewer')}
                    className="w-full text-left px-2.5 py-1.5 rounded text-slate-300 hover:bg-slate-800 hover:text-white flex items-center justify-between"
                  >
                    <span>HSE Reviewer</span>
                    {currentUser.role === 'hse_reviewer' && <span className="text-emerald-400 font-bold">✓</span>}
                  </button>
                  <button
                    onClick={() => handleRoleSwitch('auditor')}
                    className="w-full text-left px-2.5 py-1.5 rounded text-slate-300 hover:bg-slate-800 hover:text-white flex items-center justify-between"
                  >
                    <span>Auditor</span>
                    {currentUser.role === 'auditor' && <span className="text-emerald-400 font-bold">✓</span>}
                  </button>
                </div>

                <div className="pt-2 border-t border-slate-800">
                  <button
                    onClick={handleLogout}
                    className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded text-xs font-semibold text-red-400 hover:bg-red-950/40 transition-colors"
                  >
                    <LogOut className="w-3.5 h-3.5" />
                    Sign Out
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Global Modals */}
      <CommandPalette isOpen={cmdOpen} onClose={() => setCmdOpen(false)} />
      <HowSentinelThinksModal isOpen={methodologyOpen} onClose={() => setMethodologyOpen(false)} />
      <ReportQualityModal
        isOpen={reportQualityOpen}
        onClose={() => setReportQualityOpen(false)}
        onViewInsufficientReports={() => navigate('/review-queue?bucket=NEEDS_MORE_INFO')}
      />
    </>
  );
};

