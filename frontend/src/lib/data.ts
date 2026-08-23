import {
  attentionFixture,
  jobsFixture,
  overviewFixture,
  qualityFixture,
} from "./fixtures";
import type {
  AttentionView,
  JobDetailView,
  OverviewView,
  QualityView,
} from "./types";

export async function getOverview(): Promise<OverviewView> {
  return overviewFixture;
}

export async function getAttention(): Promise<AttentionView[]> {
  return attentionFixture;
}

export async function getQuality(): Promise<QualityView> {
  return qualityFixture;
}

export async function getJob(jobId: string): Promise<JobDetailView | null> {
  return jobsFixture[jobId] ?? null;
}
