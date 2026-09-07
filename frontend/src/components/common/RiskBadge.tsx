import React from 'react';
import { AlertTriangle, AlertCircle, ShieldAlert, CheckCircle2 } from 'lucide-react';
import type { RiskLevel } from '../../types/sentinel';

interface RiskBadgeProps {
  level: RiskLevel | string;
  showIcon?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const RiskBadge: React.FC<RiskBadgeProps> = ({
  level,
  showIcon = true,
  size = 'md',
  className = '',
}) => {
  const normLevel = (level || 'LOW').toUpperCase();

  const getConfig = () => {
    switch (normLevel) {
      case 'CRITICAL':
        return {
          bg: 'bg-red-500/10 text-red-400 border-red-500/30',
          icon: ShieldAlert,
          label: 'CRITICAL SIF',
        };
      case 'HIGH':
        return {
          bg: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
          icon: AlertTriangle,
          label: 'HIGH RISK',
        };
      case 'MEDIUM':
        return {
          bg: 'bg-yellow-500/10 text-yellow-300 border-yellow-500/30',
          icon: AlertCircle,
          label: 'MEDIUM',
        };
      case 'LOW':
      default:
        return {
          bg: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
          icon: CheckCircle2,
          label: 'CONTROLLED',
        };
    }
  };

  const config = getConfig();
  const Icon = config.icon;

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs font-semibold gap-1',
    md: 'px-2.5 py-1 text-xs font-bold gap-1.5',
    lg: 'px-3 py-1.5 text-sm font-extrabold gap-2',
  }[size];

  return (
    <span
      className={`inline-flex items-center rounded border font-telemetry tracking-wide uppercase ${config.bg} ${sizeClasses} ${className}`}
    >
      {showIcon && <Icon className={size === 'sm' ? 'w-3 h-3' : size === 'lg' ? 'w-4.5 h-4.5' : 'w-3.5 h-3.5'} />}
      {config.label}
    </span>
  );
};
