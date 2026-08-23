import { ControlTowerHeader } from "@/components/control-tower-header";
import { FactorySnapshot } from "@/components/factory-snapshot";
import { NeedsAttention } from "@/components/needs-attention";
import { QualitySummary } from "@/components/quality-summary";
import { getAttention, getOverview, getQuality } from "@/lib/data";

export default async function Home() {
  const [overview, attention, quality] = await Promise.all([
    getOverview(),
    getAttention(),
    getQuality(),
  ]);

  return (
    <div className="min-h-screen bg-paper">
      <ControlTowerHeader factoryAsOf={overview.asOf} />
      <main className="mx-auto max-w-7xl space-y-12 px-5 py-9 sm:px-8 sm:py-12 lg:px-10">
        <FactorySnapshot overview={overview} />
        <NeedsAttention items={attention} />
        <QualitySummary quality={quality} />
      </main>
    </div>
  );
}
