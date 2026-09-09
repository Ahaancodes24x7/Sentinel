import { motion } from 'framer-motion';
import { ScrollText } from 'lucide-react';
import { Chip, PanelHead, PulseDot, ScanPanel, type Tone } from '../components/kinetic';
import { EmptyPanel, PanelLoading, QueryError } from '../components/common/QueryState';
import { useAuditLog } from '../api/hooks';

const ACTION_TONE: Record<string, Tone> = {
  confirm: 'low',
  correct: 'medium',
  reject: 'critical',
  recompute_clusters: 'info',
};

export function AuditLogPage() {
  const { data, isLoading, error } = useAuditLog(80);
  const items = data?.items ?? [];

  return (
    <div className="space-y-4">
      <div>
        <div className="flex items-center gap-2">
          <PulseDot tone="info" size={6} />
          <span className="font-mono text-2xs tracked text-ink-4">APPEND-ONLY TRAIL</span>
        </div>
        <h1 className="mt-1.5 font-display text-4xl text-ink">Audit Trail</h1>
        <p className="mt-1.5 max-w-3xl text-sm text-ink-3">
          Every automated classification and every human action is recorded with actor and
          timestamp. There is no update path in the schema — entries can only be appended.
        </p>
      </div>

      <ScanPanel>
        <PanelHead
          title="EVENT LOG"
          right={<Chip tone="neutral">{data?.total ?? 0} ENTRIES</Chip>}
        />
        {isLoading ? (
          <PanelLoading rows={10} />
        ) : error ? (
          <QueryError error={error} />
        ) : items.length === 0 ? (
          <EmptyPanel
            icon={ScrollText}
            title="No audit entries yet"
            message="Actions taken in the review queue appear here immediately."
          />
        ) : (
          <div className="divide-y divide-line-faint font-mono">
            {items.map((entry, i) => (
              <motion.div
                key={entry.id}
                initial={{ opacity: 0, x: -6 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: Math.min(i * 0.015, 0.3) }}
                className="flex flex-wrap items-center gap-3 px-4 py-2 text-2xs"
              >
                <span className="tabular text-ink-4">
                  {entry.timestamp?.slice(0, 19).replace('T', ' ')}
                </span>
                <Chip tone={ACTION_TONE[entry.action] ?? 'neutral'}>
                  {entry.action.toUpperCase()}
                </Chip>
                <span className="text-ink-2">{entry.entity_type}</span>
                <span className="text-ink">{entry.entity_id}</span>
                <span className="ml-auto text-ink-3">{entry.actor}</span>
              </motion.div>
            ))}
          </div>
        )}
      </ScanPanel>
    </div>
  );
}
