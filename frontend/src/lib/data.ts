import {
  attentionFixture,
  jobsFixture,
  overviewFixture,
} from "./fixtures";
import type {
  BlockedAttentionView,
  JobDetailView,
  OverviewView,
} from "./types";

export async function getOverview(): Promise<OverviewView> {
  return overviewFixture;
}

export async function getAttentionPreview(): Promise<
  BlockedAttentionView[]
> {
  return attentionFixture;
}

export async function getJob(jobId: string): Promise<JobDetailView | null> {
  return jobsFixture[jobId] ?? null;
}
