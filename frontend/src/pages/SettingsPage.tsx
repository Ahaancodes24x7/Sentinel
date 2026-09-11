import { Chip, PanelHead, PulseDot, ScanPanel } from '../components/kinetic';
import { PanelLoading, QueryError } from '../components/common/QueryState';
import { useHealth, useOntology } from '../api/hooks';

export function SettingsPage() {
  const { data: health, isLoading, error } = useHealth();
  const { data: ontology } = useOntology();

  const weights = ontology?.density_metric?.weights ?? {};

  return (
    <div className="mx-auto max-w-4xl space-y-4">
      <div>
        <div className="flex items-center gap-2">
          <PulseDot tone="hivis" size={6} />
          <span className="font-mono text-2xs tracked text-ink-4">SYSTEM</span>
        </div>
        <h1 className="mt-1.5 font-display text-4xl text-ink">Settings</h1>
      </div>

      <ScanPanel>
        <PanelHead title="RUNTIME" />
        {isLoading ? (
          <PanelLoading rows={2} />
        ) : error ? (
          <QueryError error={error} />
        ) : (
          <div className="divide-y divide-line-faint">
            <Row label="Engine status" value={health?.status ?? 'unknown'} />
            <Row label="Database" value={health?.db ?? '—'} />
          </div>
        )}
      </ScanPanel>

      <ScanPanel>
        <PanelHead
          title="PRECURSOR-DENSITY WEIGHTS"
          sub="Documented, tunable, and explicitly uncalibrated"
          tone="medium"
        />
        <div className="divide-y divide-line-faint">
          {Object.entries(weights).map(([key, value]) => (
            <Row key={key} label={key.replace(/_/g, ' ')} value={String(value)} mono />
          ))}
        </div>
        <div className="border-t border-line px-4 py-3">
          <div className="flex items-center gap-2">
            <Chip tone="medium">UNCALIBRATED</Chip>
            <p className="text-xs text-ink-3">{ontology?.density_metric?.note}</p>
          </div>
        </div>
      </ScanPanel>

      <ScanPanel>
        <PanelHead title="TAXONOMY" sub={`Ontology version ${ontology?.version ?? '—'}`} tone="info" />
        <div className="divide-y divide-line-faint">
          <Row label="Life-Saving Rules" value={String(Object.keys(ontology?.life_saving_rules ?? {}).length)} />
          <Row label="Energy types" value={String(Object.keys(ontology?.energy_types ?? {}).length)} />
          <Row label="Barrier types" value={String(Object.keys(ontology?.barrier_types ?? {}).length)} />
          <Row label="Activities" value={String((ontology?.activities ?? []).length)} />
          <Row label="Sites" value={String((ontology?.sites ?? []).length)} />
        </div>
      </ScanPanel>

      <ScanPanel>
        <PanelHead title="DEMO ACCOUNTS" sub="Hardcoded for the prototype — not a user-management system" tone="medium" />
        <div className="divide-y divide-line-faint">
          <Row label="hse_demo / demo123" value="hse_reviewer" mono />
          <Row label="manager_demo / demo123" value="hse_manager" mono />
          <Row label="auditor_demo / demo123" value="auditor" mono />
        </div>
      </ScanPanel>
    </div>
  );
}

function Row({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-4 px-4 py-2.5">
      <span className="text-xs text-ink-3">{label}</span>
      <span className={mono ? 'font-mono text-xs text-ink' : 'text-xs text-ink'}>{value}</span>
    </div>
  );
}
