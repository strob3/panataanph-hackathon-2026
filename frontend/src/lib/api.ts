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
  minimum_score: number;
  threshold_overridden: boolean;
  qr_codes: { public_id: string; label: string; image_url: string }[];
  transparency: {
    received_centavos: number;
    spent_centavos: number;
    balance_centavos: number;
    entries: FundEntry[];
  };
}

export interface FundEntry {
  public_id: string;
  kind: "received" | "spent";
  amount_centavos: number;
  description: string;
  occurred_on: string;
  status: "approved";
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

export async function request<T>(path: string, options?: RequestInit): Promise<T> {
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
  if (response.status === 204) return undefined as T;
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

export function submitCampaign(fields: Record<string, string>, files: File[], donationQR?: File) {
  const form = new FormData();
  const values = Object.fromEntries(
    Object.entries(fields).map(([key, value]) => [key, value || null]),
  );
  form.append(
    "campaign",
    JSON.stringify({ ...values, target_amount: Number(fields.target_amount) }),
  );
  files.forEach((file) => form.append("documents", file));
  if (donationQR) {
    form.append("donation_qr", donationQR);
    form.append("qr_label", fields.qr_label || "");
  }
  return request<Submission>("/submissions", { method: "POST", body: form });
}
