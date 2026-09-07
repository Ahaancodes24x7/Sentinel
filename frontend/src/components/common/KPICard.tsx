import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { ResponsiveContainer, LineChart, Line } from 'recharts';

interface KPICardProps {
  title: string;
  value: string | number;
  trend?: number;
  trendText?: string;
  comparison?: string;
  badgeText?: string;
  badgeType?: 'critical' | 'warning' | 'success' | 'info';
  icon: LucideIcon;
  sparklineData?: { value: number }[];
  accentColor?: string;
}

export const KPICard: React.FC<KPICardProps> = ({
  title,
  value,
  trend,
  trendText,
  comparison = 'vs previous period',
  badgeText,
  badgeType = 'critical',
  icon: Icon,
  sparklineData = [
    { value: 10 },
    { value: 15 },
    { value: 12 },
    { value: 20 },
    { value: 18 },
    { value: 24 },
    { value: 22 },
  ],
  accentColor = '#3b82f6',
}) => {
  const isPositiveTrend = trend !== undefined && trend > 0;
  const isNegativeTrend = trend !== undefined && trend < 0;

  const getBadgeStyle = () => {
    switch (badgeType) {
      case 'critical':
        return 'bg-red-500/15 text-red-400 border-red-500/30';
      case 'warning':
        return 'bg-amber-500/15 text-amber-400 border-amber-500/30';
      case 'success':
        return 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30';
      case 'info':
      default:
        return 'bg-blue-500/15 text-blue-400 border-blue-500/30';
    }
  };

  return (
    <div className="relative overflow-hidden rounded-lg bg-slate-900/90 border border-slate-800 p-4 shadow-lg hover:border-slate-700 transition-all duration-200">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          {title}
        </span>
        <div className="p-2 rounded bg-slate-800/80 text-slate-300 border border-slate-700/50">
          <Icon className="w-4 h-4 text-blue-400" />
        </div>
      </div>

      <div className="flex items-baseline justify-between">
        <div>
          <div className="text-2xl font-extrabold font-telemetry text-slate-100 tracking-tight">
            {typeof value === 'number' ? value.toLocaleString() : value}
          </div>
          {badgeText && (
            <div className={`mt-1 inline-flex items-center px-1.5 py-0.5 text-[11px] font-bold rounded border ${getBadgeStyle()}`}>
              {badgeText}
            </div>
          )}
        </div>

        {/* Small sparkline chart */}
        {sparklineData && sparklineData.length > 0 && (
          <div className="w-20 h-10">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={sparklineData}>
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke={accentColor}
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      <div className="mt-3 flex items-center gap-1.5 text-xs">
        {trend !== undefined && (
          <span
            className={`inline-flex items-center gap-0.5 font-bold font-telemetry ${isPositiveTrend
                ? 'text-red-400'
                : isNegativeTrend
                  ? 'text-emerald-400'
                  : 'text-slate-400'
              }`}
          >
            {isPositiveTrend ? (
              <TrendingUp className="w-3.5 h-3.5" />
            ) : isNegativeTrend ? (
              <TrendingDown className="w-3.5 h-3.5" />
            ) : (
              <Minus className="w-3.5 h-3.5" />
            )}
            {trend > 0 ? `+${trend}%` : `${trend}%`}
          </span>
        )}
        {trendText && <span className="text-slate-400 font-medium">{trendText}</span>}
        <span className="text-slate-500 font-normal">{comparison}</span>
      </div>
    </div>
  );
};
