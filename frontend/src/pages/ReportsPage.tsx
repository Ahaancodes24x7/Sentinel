import { useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Filter, Search } from 'lucide-react';
import { Chip, Counter, PanelHead, PulseDot, ScanPanel, type Tone } from '../components/kinetic';
import { EmptyPanel, NoDataYet, PanelLoading, QueryError } from '../components/common/QueryState';
import { useOntology, useReports } from '../api/hooks';
import { BUCKET_META, type Bucket } from '../api/types';
import { cn } from '../lib/cn';

const BUCKET_TONE: Record<Bucket, Tone> = {
  HIGH_CONF_SIF: 'critical',
  LOW_CONF_REVIEW: 'high',
  NEEDS_MORE_INFO: 'medium',
  HIGH_CONF_NON_SIF: 'low',
};

const PAGE_SIZE = 40;

export function ReportsPage() {
  const [site, setSite] = useState<string>('');
  const [bucket, setBucket] = useState<string>('');
  const [lsr, setLsr] = useState<string>('');
  const [page, setPage] = useState(0);
  const [search, setSearch] = useState('');

  const { data: ontology } = useOntology();
  const { data, isLoading, error, isFetching } = useReports({
    site: site || undefined,
    bucket: bucket || undefined,
    lsr_tag: lsr || undefined,
    limit: PAGE_SIZE,
    offset: page * PAGE_SIZE,
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;

  // Client-side text filter over the current page only. Deliberately not
  // presented as a corpus-wide search — the API has no full-text endpoint, and
  // a box that silently searches 40 of 25,000 rows would be misleading.
  const visible = search
    ? items.filter(
        (r) =>
          r.report_id.toLowerCase().includes(search.toLowerCase()) ||
          r.site.toLowerCase().includes(search.toLowerCase()) ||
          r.lsr_tag.toLowerCase().includes(search.toLowerCase()),
      )
    : items;

  const sites = ontology?.sites?.map((s) => s.name) ?? [];
  const rules = Object.keys(ontology?.life_saving_rules ?? {});

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <PulseDot tone="info" size={6} />
            <span className="font-mono text-2xs tracked text-ink-4">CORPUS BROWSER</span>
          </div>
          <h1 className="mt-1.5 font-display text-4xl text-ink">All Reports</h1>
        </div>
        <div className="text-right">
          <div className="font-display text-3xl text-hivis">
            <Counter value={total} />
          </div>
          <div className="font-mono text-2xs tracked text-ink-4">MATCHING RECORDS</div>
        </div>
      </div>

      {/* Filters */}
      <ScanPanel>
        <div className="flex flex-wrap items-center gap-2 p-3">
          <div className="flex items-center gap-1.5 text-ink-4">
            <Filter className="h-3.5 w-3.5" strokeWidth={2} />
            <span className="font-mono text-2xs tracked">FILTER</span>
          </div>

          <div className="relative">
            <Search className="pointer-events-none absolute left-2 top-1/2 h-3 w-3 -translate-y-1/2 text-ink-4" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Filter this page…"
              className="w-48 rounded-md border border-line bg-surface-2 py-1.5 pl-7 pr-2 text-xs text-ink placeholder:text-ink-4 focus:border-hivis-edge focus:outline-none"
            />
          </div>

          <FilterSelect value={site} onChange={setSite} label="All sites" options={sites} />
          <FilterSelect
            value={bucket}
            onChange={setBucket}
            label="All buckets"
            options={Object.keys(BUCKET_META)}
            render={(v) => BUCKET_META[v as Bucket]?.short ?? v}
          />
          <FilterSelect value={lsr} onChange={setLsr} label="All rules" options={rules} />

          {(site || bucket || lsr || search) && (
            <button
              type="button"
              onClick={() => {
                setSite('');
                setBucket('');
                setLsr('');
                setSearch('');
                setPage(0);
              }}
              className="font-mono text-2xs tracked text-ink-3 underline hover:text-hivis"
            >
              CLEAR
            </button>
          )}

          {isFetching && (
            <span className="ml-auto flex items-center gap-1.5">
              <PulseDot tone="hivis" size={5} />
              <span className="font-mono text-2xs tracked text-ink-4">SYNCING</span>
            </span>
          )}
        </div>
      </ScanPanel>

      {/* Table */}
      <ScanPanel>
        <PanelHead
          title="REPORTS"
          right={
            <span className="font-mono text-2xs tabular text-ink-4">
              {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, total)} of {total}
            </span>
          }
        />

        {isLoading ? (
          <PanelLoading rows={10} />
        ) : error ? (
          <QueryError error={error} />
        ) : total === 0 ? (
          <NoDataYet />
        ) : visible.length === 0 ? (
          <EmptyPanel title="No matches on this page" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[46rem] text-left">
              <thead>
                <tr className="border-b border-line bg-surface-2">
                  {['REPORT', 'SITE', 'DATE', 'ROUTING', 'LIFE-SAVING RULE', 'VERDICT'].map((h) => (
                    <th
                      key={h}
                      className="px-4 py-2 font-mono text-[9px] tracked font-medium text-ink-4"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-line-faint">
                {visible.map((r, i) => (
                  <motion.tr
                    key={r.report_id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: Math.min(i * 0.012, 0.3) }}
                    className="group transition-colors hover:bg-surface-2"
                  >
                    <td className="px-4 py-2.5">
                      <Link
                        to={`/reports/${r.report_id}`}
                        className="font-mono text-xs text-ink group-hover:text-hivis"
                      >
                        {r.report_id}
                      </Link>
                    </td>
                    <td className="px-4 py-2.5 text-xs text-ink-2">{r.site}</td>
                    <td className="px-4 py-2.5 font-mono text-2xs tabular text-ink-3">
                      {r.timestamp?.slice(0, 10)}
                    </td>
                    <td className="px-4 py-2.5">
                      <Chip tone={BUCKET_TONE[r.bucket]} dot>
                        {BUCKET_META[r.bucket]?.short ?? r.bucket}
                      </Chip>
                    </td>
                    <td className="px-4 py-2.5 text-xs text-ink-2">
                      {r.lsr_tag && r.lsr_tag !== 'N/A' ? r.lsr_tag : <span className="text-ink-4">—</span>}
                    </td>
                    <td className="px-4 py-2.5">
                      <span
                        className={cn(
                          'font-mono text-2xs tracked',
                          r.sif_potential ? 'text-critical' : 'text-low',
                        )}
                      >
                        {r.sif_potential ? 'PRECURSOR' : 'CLEARED'}
                      </span>
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {total > PAGE_SIZE && (
          <div className="flex items-center justify-between border-t border-line px-4 py-2">
            <button
              type="button"
              disabled={page === 0}
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              className="font-mono text-2xs tracked text-ink-2 disabled:opacity-30 hover:text-hivis"
            >
              ← PREV
            </button>
            <span className="font-mono text-2xs tabular text-ink-4">
              PAGE {page + 1} / {Math.max(1, Math.ceil(total / PAGE_SIZE))}
            </span>
            <button
              type="button"
              disabled={(page + 1) * PAGE_SIZE >= total}
              onClick={() => setPage((p) => p + 1)}
              className="font-mono text-2xs tracked text-ink-2 disabled:opacity-30 hover:text-hivis"
            >
              NEXT →
            </button>
          </div>
        )}
      </ScanPanel>
    </div>
  );
}

function FilterSelect({
  value,
  onChange,
  label,
  options,
  render,
}: {
  value: string;
  onChange: (v: string) => void;
  label: string;
  options: string[];
  render?: (v: string) => string;
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="rounded-md border border-line bg-surface-2 px-2 py-1.5 text-xs text-ink focus:border-hivis-edge focus:outline-none"
    >
      <option value="">{label}</option>
      {options.map((o) => (
        <option key={o} value={o}>
          {render ? render(o) : o}
        </option>
      ))}
    </select>
  );
}
