import { request } from "./api";

export interface User {
  id: number;
  name: string;
  email: string;
  role: "organizer" | "admin" | "lgu";
  verified: boolean;
}

export type CampaignStatus =
  | "pending"
  | "under_review"
  | "needs_information"
  | "verified"
  | "rejected";

export interface AdminCampaignSummary {
  public_id: string;
  title: string;
  organizer_name: string;
  location: string;
  status: CampaignStatus;
  verification_score: number | null;
  target_amount: number;
  created_at: string;
  owner: User | null;
}

export interface AdminCampaignDetail extends AdminCampaignSummary {
  organization_name: string | null;
  description: string;
  purpose: string;
  beneficiaries: string | null;
  payment_method: string | null;
  payment_details: string | null;
  organizer_email: string | null;
  organizer_phone: string | null;
  minimum_score: number;
  qr_codes: { public_id: string; label: string; image_url: string }[];
  documents: {
    id: number;
    public_id: string;
    original_filename: string;
    file_type: string;
    processing_status: string;
    url: string;
    extraction: Record<string, unknown> | null;
  }[];
  findings: {
    criterion: string;
    points_awarded: number;
    points_possible: number;
    details: string | null;
  }[];
  reviews: {
    admin_username: string;
    decision: string;
    reason: string | null;
    previous_status: string | null;
    new_status: string;
    reviewed_at: string;
    threshold_override: boolean;
    override_reason: string | null;
    warnings_resolved: boolean;
  }[];
  fund_updates: {
    public_id: string;
    kind: string;
    amount_centavos: number;
    description: string;
    occurred_on: string;
    status: string;
    review_reason: string | null;
    created_at: string;
  }[];
  reports?: {
    id: number;
    reason: string;
    reporter_name: string | null;
    reporter_email: string | null;
    status: string;
    admin_response: string | null;
    created_at: string;
    resolved_at: string | null;
  }[];
}

export interface ReviewInput {
  decision: Exclude<CampaignStatus, "pending">;
  reason: string;
  permits: boolean;
  identity: boolean;
  consistency: boolean;
  history: boolean;
  override_threshold: boolean;
  override_reason: string | null;
  warnings_resolved: boolean;
}

function json(method: string, value: unknown): RequestInit {
  return {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(value),
  };
}

export const registerAccount = (name: string, email: string, password: string) =>
  request<User>("/auth/register", json("POST", { name, email, password }));

export const login = (email: string, password: string) =>
  request<User>("/auth/login", json("POST", { email, password }));

export const logout = () => request<unknown>("/auth/logout", { method: "POST" });

export const getCurrentUser = (signal?: AbortSignal) => request<User>("/auth/me", { signal });

export const listAdminAccounts = (signal?: AbortSignal, skip = 0) =>
  request<{ items: User[]; total: number; skip: number; limit: number }>(
    `/admin/accounts?skip=${skip}&limit=20`,
    { signal },
  );

export const verifyAccount = (id: number, verified: boolean, reason: string) =>
  request<User>(`/admin/accounts/${id}`, json("PATCH", { verified, reason }));

export const listAdminCampaigns = (status: CampaignStatus | "", signal?: AbortSignal, skip = 0) =>
  request<{ items: AdminCampaignSummary[]; total: number; skip: number; limit: number }>(
    `/admin/campaigns?skip=${skip}&limit=20${status ? `&status=${status}` : ""}`,
    { signal },
  );

export const getAdminCampaign = (id: string, signal?: AbortSignal) =>
  request<AdminCampaignDetail>(`/admin/campaigns/${encodeURIComponent(id)}`, { signal });

export const extractDocument = (id: number) =>
  request<unknown>(`/documents/${id}/extract`, { method: "POST" });

export const reviewCampaign = (id: string, values: ReviewInput) =>
  request<AdminCampaignDetail>(
    `/admin/campaigns/${encodeURIComponent(id)}/review`,
    json("POST", values),
  );

export const reviewFundUpdate = (id: string, status: "approved" | "rejected", reason: string) =>
  request<unknown>(
    `/admin/fund-updates/${encodeURIComponent(id)}`,
    json("PATCH", { status, reason }),
  );

export const resolveCampaignReport = (reportId: number, adminResponse: string, status: "reviewed" | "dismissed" = "reviewed") =>
  request<{ status: string; report_id: number; report_status: string }>(
    `/admin/reports/${reportId}/resolve`,
    json("POST", { admin_response: adminResponse, status }),
  );

