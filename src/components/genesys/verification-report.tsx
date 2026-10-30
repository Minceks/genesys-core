export type VerificationReportData = {
  passed: string[]; failed: string[]; incomplete: string[];
  manualReview: string[]; deferred: string[]; limitations: string[];
};

export function readVerificationReport(value: unknown): VerificationReportData | undefined {
  if (!value || typeof value !== 'object') return undefined;
  const data = value as Record<string, unknown>;
  const list = (key: string) => Array.isArray(data[key]) ? data[key].filter((item): item is string => typeof item === 'string').slice(0, 30) : [];
  return { passed: list('passed'), failed: list('failed'), incomplete: list('incomplete'),
    manualReview: list('manualReview'), deferred: list('deferred'),
    limitations: list('limitations').length ? list('limitations') : list('unverified') };
}

export function VerificationReport({ report }: { report: VerificationReportData }) {
  const sections = [
    { title: 'Failed checks', items: report.failed, color: 'text-red-300', open: true },
    { title: 'Checks incomplete', items: report.incomplete, color: 'text-amber-300', open: true },
    { title: 'Passed checks', items: report.passed, color: 'text-emerald-300', open: false },
    { title: 'Needs manual review', items: report.manualReview, color: 'text-sky-300', open: false },
    { title: 'Deferred integrations', items: report.deferred, color: 'text-zinc-300', open: false },
    { title: 'Scope of these checks', items: report.limitations, color: 'text-zinc-400', open: false },
  ];
  return <section aria-label="Verification results" className="mt-3 rounded-2xl border border-white/10 bg-zinc-950 p-4 text-xs leading-relaxed">
    <p className="mb-2 font-semibold text-zinc-100">Verification results</p>
    {!report.failed.length && !report.incomplete.length && report.passed.length > 0 &&
      <p className="mb-3 text-emerald-300">All listed checks passed. Manual review and deferred integrations are separate.</p>}
    <div className="space-y-3">{sections.filter(section => section.items.length).map(section =>
      <details key={section.title} open={section.open}>
        <summary className={`cursor-pointer font-medium ${section.color}`}>{section.title} ({section.items.length})</summary>
        <ul className="mt-2 list-disc space-y-2 pl-5 text-zinc-300">{section.items.map((item, index) => <li key={index}>{item}</li>)}</ul>
      </details>)}</div>
  </section>;
}
