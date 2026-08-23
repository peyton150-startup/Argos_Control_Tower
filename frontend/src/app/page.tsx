import { ControlTowerHeader } from "@/components/control-tower-header";
import { FactorySnapshot } from "@/components/factory-snapshot";
import { NeedsAttention } from "@/components/needs-attention";
import { getAttentionPreview, getOverview } from "@/lib/data";

export default async function Home() {
  const [overview, attention] = await Promise.all([
    getOverview(),
    getAttentionPreview(),
  ]);

  return (
    <div className="min-h-screen bg-paper">
      <ControlTowerHeader factoryAsOf={overview.factoryAsOf} />
      <main className="mx-auto max-w-7xl space-y-12 px-5 py-9 sm:px-8 sm:py-12 lg:px-10">
        <FactorySnapshot snapshot={overview.snapshot} />
        <NeedsAttention
          items={attention}
          totalBlocked={overview.snapshot.blockedJobs}
        />
      </main>
    </div>
  );
}
