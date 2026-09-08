import { LandingHeader } from "@/components/landing/LandingHeader";
import { Hero } from "@/components/landing/Hero";
import { MetricsStrip } from "@/components/landing/MetricsStrip";
import { PipelineStrip } from "@/components/landing/PipelineStrip";
import { CapabilityGrid } from "@/components/landing/CapabilityGrid";
import { TriageLegend } from "@/components/landing/TriageLegend";
import { RoleMatrix } from "@/components/landing/RoleMatrix";
import { CtaBlock } from "@/components/landing/CtaBlock";
import { LandingFooter } from "@/components/landing/LandingFooter";

/**
 * Public landing page. Each block is a self-contained module under
 * `components/landing/` fed from `components/landing/content.ts`, so copy and
 * ordering change in one place.
 */
export default function LandingPage() {
  return (
    <div className="min-h-screen bg-panel">
      <LandingHeader />
      <main>
        <Hero />
        <MetricsStrip />
        <PipelineStrip />
        <CapabilityGrid />
        <TriageLegend />
        <RoleMatrix />
        <CtaBlock />
      </main>
      <LandingFooter />
    </div>
  );
}
