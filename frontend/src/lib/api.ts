export interface Campaign {
  public_id: string;
  title: string;
  organizer_name: string;
  organization_name: string | null;
  purpose: string;
  cause: string | null;
  location: string;
  status: "verified";
  urgency: string;
  verification_score: number | null;
  created_at: string;
}

export interface CampaignDetail extends Campaign {
  description: string;
  beneficiaries: string | null;
  target_amount: number;
  payment_method: string | null;
  payment_details: string | null;
  updated_at: string;
  findings: {
    criterion: string;
    points_awarded: number;
    points_possible: number;
  }[];
}

export interface CampaignPage {
  items: Campaign[];
  total: number;
  skip: number;
  limit: number;
}

export interface Submission {
  public_id: string;
  status: "pending";
  documents_received: number;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, options);
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = body?.detail;
    throw new Error(
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((issue: { msg: string }) => issue.msg).join("; ")
          : `Request failed (${response.status}). Please try again.`,
    );
  }
  return response.json() as Promise<T>;
}

export function listCampaigns(params: URLSearchParams, signal?: AbortSignal) {
  return request<CampaignPage>(`/campaigns?${params}`, { signal });
}

export function getCampaign(id: string, signal?: AbortSignal) {
  return request<CampaignDetail>(`/campaigns/${encodeURIComponent(id)}`, {
    signal,
  });
}

export function submitCampaign(fields: Record<string, string>, files: File[]) {
  const form = new FormData();
  const values = Object.fromEntries(
    Object.entries(fields).map(([key, value]) => [key, value || null]),
  );
  form.append(
    "campaign",
    JSON.stringify({ ...values, target_amount: Number(fields.target_amount) }),
  );
  files.forEach((file) => form.append("documents", file));
  return request<Submission>("/submissions", { method: "POST", body: form });
}
