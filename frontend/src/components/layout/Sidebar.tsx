import { NavLink } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  BarChart3,
  Boxes,
  Camera,
  ClipboardCheck,
  FileText,
  Gauge,
  GitBranch,
  LayoutDashboard,
  ListChecks,
  MapPinned,
  PenSquare,
  Radar,
  ScrollText,
  Settings,
  ShieldAlert,
  Siren,
} from 'lucide-react';
import { SentinelLogo } from '../common/SentinelMark';
import { cn } from '../../lib/cn';
import { Counter, PulseDot } from '../kinetic';
import { Hint } from '../common/Hint';
import { useReviewQueue, useSummary } from '../../api/hooks';

interface NavItem {
  to: string;
  label: string;
  icon: typeof LayoutDashboard;
  /** One line explaining what the screen is for. Shown on hover. */
  hint: string;
  badge?: 'queue';
}

/* --------------------------------------------------------------------------
 * Three groups, ordered by how often they are used:
 *
 *   DAILY     what an HSE officer touches every shift
 *   ANALYSE   where the patterns and rankings live
 *   SYSTEM    reference and admin — rarely opened, so it sits at the bottom
 *
 * Every item carries a hint, because half these labels are domain jargon that
 * means nothing until someone explains it once.
 * ----------------------------------------------------------------------- */
const SECTIONS: { title: string; items: NavItem[] }[] = [
  {
    title: 'Daily',
    items: [
      {
        to: '/operations-map',
        label: 'Operations Map',
        icon: MapPinned,
        hint: 'Interactive site map for Duliajan, Digboi and Moran. Select a site to scope every screen to it.',
      },
      {
        to: '/dashboard',
        label: 'Action Center',
        icon: LayoutDashboard,
        hint: 'The landing view: what needs attention, where the risk is, and whether anything is trending worse.',
      },
      {
        to: '/live-vision',
        label: 'Live Safety Vision',
        icon: Camera,
        hint: 'Real-time YOLO object detection over a webcam or a demo video, with configurable safety-zone rules and live hazard events.',
      },
      {
        to: '/submit',
        label: 'File a Report',
        icon: PenSquare,
        hint: 'Write up something you saw. The engine analyses it immediately and shows you its reasoning.',
      },
      {
        to: '/review-queue',
        label: 'Review Queue',
        icon: ClipboardCheck,
        badge: 'queue',
        hint: 'Reports waiting for a human decision, oldest first so nothing ages out unseen.',
      },
      {
        to: '/reports',
        label: 'All Reports',
        icon: FileText,
        hint: 'Browse and filter the whole corpus by site, rule or routing bucket.',
      },
    ],
  },
  {
    title: 'Analyse',
    items: [
      {
        to: '/sif-precursors',
        label: 'SIF Precursors',
        icon: Siren,
        hint: 'Only the reports flagged as carrying credible fatal potential.',
      },
      {
        to: '/patterns',
        label: 'Patterns',
        icon: GitBranch,
        hint: 'Reports grouped by the underlying situation rather than by wording, so the same failure described ten ways lands in one cluster.',
      },
      {
        to: '/barriers',
        label: 'Barrier Failures',
        icon: ShieldAlert,
        hint: 'Which safety controls keep failing, and during which activity.',
      },
      {
        to: '/risk-intelligence',
        label: 'Site Risk',
        icon: Radar,
        hint: 'Sites ranked by precursor density, with the simple and composite metrics side by side.',
      },
      {
        to: '/analytics',
        label: 'Trends',
        icon: BarChart3,
        hint: 'Control charts that flag an unusual rise in the reported precursor rate. Not a prediction.',
      },
      {
        to: '/recommendations',
        label: 'Interventions',
        icon: ListChecks,
        hint: 'What to actually do about each pattern, ranked so engineering fixes outrank training.',
      },
    ],
  },
  {
    title: 'System',
    items: [
      {
        to: '/life-saving-rules',
        label: 'Life-Saving Rules',
        icon: Boxes,
        hint: 'The nine IOGP rules and which energy types map to each.',
      },
      {
        to: '/model-performance',
        label: 'Model',
        icon: Gauge,
        hint: 'What the deployed model is doing right now, and how its evaluation was framed.',
      },
      {
        to: '/audit-log',
        label: 'Audit Trail',
        icon: ScrollText,
        hint: 'Append-only record of every classification and every human action.',
      },
      {
        to: '/settings',
        label: 'Settings',
        icon: Settings,
        hint: 'Runtime status, the density-metric weights, and the taxonomy version in use.',
      },
    ],
  },
];

export function Sidebar() {
  const { data: queue } = useReviewQueue(undefined, 'oldest', 200);
  const { data: summary } = useSummary();
  const queueCount = queue?.total ?? 0;

  return (
    <aside className="relative z-10 flex h-screen w-56 shrink-0 flex-col border-r border-line bg-surface/60 backdrop-blur-xl">
      {/* Brand */}
      <div className="flex h-14 items-center border-b border-line px-4">
        <SentinelLogo caption="PS 26165 · OIL INDIA" size={26} />
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto px-2 py-3">
        {SECTIONS.map((section) => (
          <div key={section.title} className="mb-5">
            <div className="px-2 pb-1.5 font-mono text-[9px] tracked text-ink-4">
              {section.title}
            </div>
            <div className="space-y-0.5">
              {section.items.map((item) => (
                <Hint key={item.to} content={item.hint} side="right" delay={450} className="block w-full">
                  <NavLink
                    to={item.to}
                    className={({ isActive }) =>
                      cn(
                        'group relative flex w-full items-center gap-2.5 rounded-md px-2 py-1.5 text-sm transition-colors',
                        isActive
                          ? 'bg-hivis-wash text-hivis'
                          : 'text-ink-2 hover:bg-surface-2 hover:text-ink',
                      )
                    }
                  >
                    {({ isActive }) => (
                      <>
                        {isActive && (
                          <motion.span
                            layoutId="nav-active"
                            className="absolute left-0 top-1/2 h-4 w-0.5 -translate-y-1/2 rounded-full bg-hivis"
                            transition={{ type: 'spring', stiffness: 500, damping: 38 }}
                          />
                        )}
                        <item.icon className="h-4 w-4 shrink-0" strokeWidth={1.9} />
                        <span className="truncate">{item.label}</span>
                        {item.badge === 'queue' && queueCount > 0 && (
                          <span className="ml-auto rounded-sm bg-high-wash px-1.5 font-mono text-2xs tabular text-high">
                            {queueCount > 999 ? '999+' : queueCount}
                          </span>
                        )}
                      </>
                    )}
                  </NavLink>
                </Hint>
              ))}
            </div>
          </div>
        ))}
      </nav>

      {/* Live corpus counter */}
      <Hint content="Total reports that have been through the pipeline." side="right" className="block w-full">
        <div className="w-full border-t border-line px-4 py-3">
          <div className="flex items-center gap-2">
            <PulseDot tone="hivis" size={6} />
            <span className="font-mono text-[9px] tracked text-ink-4">CORPUS</span>
          </div>
          <div className="mt-1 font-display text-2xl text-ink">
            <Counter value={summary?.total_reports ?? 0} />
          </div>
          <div className="font-mono text-[9px] tracked text-ink-4">REPORTS ANALYSED</div>
        </div>
      </Hint>
    </aside>
  );
}
