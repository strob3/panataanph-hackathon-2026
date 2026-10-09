import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { ArrowRight, BadgeCheck, HeartHandshake } from "lucide-react";
import { request } from "../lib/api";
import type { User } from "../lib/accountApi";

interface OwnCampaign {
  public_id: string;
  title: string;
  location: string;
  status: string;
  verification_score: number | null;
  target_amount: number;
  admin_notes: string | null;
}

interface FundUpdate {
  public_id: string;
  kind: "received" | "spent";
  amount_centavos: number;
  description: string;
  occurred_on: string;
  status: "pending" | "approved" | "rejected";
  review_reason: string | null;
}

const money = (centavos: number) =>
  new Intl.NumberFormat("en-PH", { style: "currency", currency: "PHP" }).format(centavos / 100);
const reason = (error: unknown) => error instanceof Error ? error.message : "Unable to load your campaigns.";
const statusLabel = (status: string) => status.replace(/_/g, " ");

export function ProfilePage({ user, go }: { user: User; go: (path: string) => void }) {
  const [campaigns, setCampaigns] = useState<OwnCampaign[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [updates, setUpdates] = useState<FundUpdate[]>([]);
  const [loading, setLoading] = useState(true);
  const [fundsLoading, setFundsLoading] = useState(false);
  const [error, setError] = useState("");
  const [fundsError, setFundsError] = useState("");
  const [success, setSuccess] = useState("");
  const [busy, setBusy] = useState(false);
  const [retry, setRetry] = useState(0);
  const [evidenceFiles, setEvidenceFiles] = useState<File[]>([]);
  const selected = campaigns.find((campaign) => campaign.public_id === selectedId);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    request<OwnCampaign[]>("/my/campaigns", { signal: controller.signal })
      .then((result) => {
        if (!controller.signal.aborted) setCampaigns(result);
      })
      .catch((failure) => {
        if (!controller.signal.aborted) setError(reason(failure));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [user.id, retry]);

  useEffect(() => {
    setUpdates([]);
    setFundsError("");
    if (!selectedId) return;
    const controller = new AbortController();
    setFundsLoading(true);
    request<FundUpdate[]>(`/my/campaigns/${encodeURIComponent(selectedId)}/funds`, { signal: controller.signal })
      .then((result) => {
        if (!controller.signal.aborted) setUpdates(result);
      })
      .catch((failure) => {
        if (!controller.signal.aborted) setFundsError(reason(failure));
      })
      .finally(() => {
        if (!controller.signal.aborted) setFundsLoading(false);
      });
    return () => controller.abort();
  }, [selectedId, retry]);

  const submitFunds = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selected || selected.status !== "verified" || busy) return;
    const form = event.currentTarget;
    const fields = new FormData(form);
    setBusy(true);
    setFundsError("");
    setSuccess("");
    try {
      const update = await request<FundUpdate>(`/my/campaigns/${encodeURIComponent(selected.public_id)}/funds`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          kind: fields.get("kind"),
          amount: String(fields.get("amount") || "").trim(),
          description: String(fields.get("description") || "").trim(),
          occurred_on: fields.get("occurred_on"),
        }),
      });
      setUpdates((current) => [update, ...current]);
      setSuccess("Fund report submitted. It will appear publicly after administrator approval.");
      form.reset();
    } catch (failure) {
      setFundsError(reason(failure));
    } finally {
      setBusy(false);
    }
  };

  const submitEvidence = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selected || selected.status !== "needs_information" || busy) return;
    if (!evidenceFiles.length) {
      setFundsError("Choose at least one additional supporting document.");
      return;
    }
    setBusy(true);
    setFundsError("");
    setSuccess("");
    const form = new FormData();
    evidenceFiles.forEach((file) => form.append("documents", file));
    try {
      const result = await request<{ documents_received: number }>(
        `/my/campaigns/${encodeURIComponent(selected.public_id)}/documents`,
        { method: "POST", body: form },
      );
      setEvidenceFiles([]);
      setSuccess(`${result.documents_received} additional documents submitted privately. Campaign is under review again.`);
      setRetry((value) => value + 1);
    } catch (failure) {
      setFundsError(reason(failure));
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="container py-10 sm:py-14">
      <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-start">
        <div className="min-w-0">
          <p className="eyebrow">Organizer account</p>
          <h1 className="mt-3 text-3xl font-extrabold sm:text-4xl">My Campaigns</h1>
          <p className="mt-3 break-words text-muted">{user.name} · {user.email}</p>
          <span className={`badge mt-4 ${user.verified ? "badge-green" : "badge-amber"}`}>
            {user.verified && <BadgeCheck size={15} />}
            {user.verified ? "Account reviewed" : "Account awaiting review"}
          </span>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-muted">
            Account verification and campaign approval are separate. Each fundraiser needs evidence
            review and the required score, or a documented administrator exception, before publication.
          </p>
        </div>
        <button className="button button-primary shrink-0" onClick={() => go("/verify")}>
          New Campaign <ArrowRight size={17} />
        </button>
      </div>
      <section className="mt-8" aria-label="Your submitted campaigns">
        {loading ? <p role="status" className="report-card text-sm text-muted">Loading your campaigns…</p> : error ? (
          <div className="report-card">
            <p role="alert" className="text-sm text-brand">{error}</p>
            <button className="button button-secondary mt-4" onClick={() => setRetry((value) => value + 1)}>Try Again</button>
          </div>
        ) : !campaigns.length ? (
          <div className="report-card">
            <HeartHandshake className="text-brand" size={30} />
            <h2 className="mt-4 text-xl font-extrabold">No campaigns submitted yet</h2>
            <p className="mt-2 text-sm leading-6 text-muted">Submit your first fundraiser with supporting documents for private review.</p>
          </div>
        ) : (
          <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
            {campaigns.map((campaign) => (
              <article key={campaign.public_id} className="campaign-card flex flex-col">
                <span className={`badge capitalize ${campaign.status === "verified" ? "badge-green" : "badge-amber"}`}>
                  {statusLabel(campaign.status)}
                </span>
                <h2 className="mt-4 break-words text-xl font-extrabold">{campaign.title}</h2>
                <p className="mt-2 text-sm text-muted">{campaign.location}</p>
                <p className="mt-4 text-sm font-semibold">Evidence score: {campaign.verification_score ?? "Not scored"}{campaign.verification_score !== null && " / 100"}</p>
                {campaign.admin_notes && <p className="mt-3 whitespace-pre-wrap break-words rounded-xl bg-canvas p-3 text-sm leading-6"><span className="font-bold">Reviewer feedback: </span>{campaign.admin_notes}</p>}
                <button
                  className="button button-secondary mt-5 w-full"
                  aria-pressed={selectedId === campaign.public_id}
                  disabled={busy}
                  onClick={() => {
                    setSelectedId(campaign.public_id);
                    setEvidenceFiles([]);
                    setSuccess("");
                  }}
                >{campaign.status === "verified" ? "Report Funds" : "View Review Details"}</button>
                {campaign.status === "verified" && user.verified && <button className="button button-ghost mt-2" onClick={() => go(`/campaigns/${campaign.public_id}`)}>View Public Campaign</button>}
              </article>
            ))}
          </div>
        )}
      </section>
      {selected && (
        <section className="report-card mt-8" aria-labelledby="fund-report-heading">
          <h2 id="fund-report-heading" className="break-words text-xl font-extrabold">{selected.status === "needs_information" ? "Review details" : "Fund reports"}: {selected.title}</h2>
          {selected.status === "needs_information" && (
            <form onSubmit={submitEvidence} className="mt-5">
              <fieldset disabled={busy} className="min-w-0">
                <h3 className="text-lg font-extrabold">Additional evidence requested</h3>
                <p className="mt-2 whitespace-pre-wrap break-words text-sm leading-6 text-muted">
                  {selected.admin_notes || "An administrator requested more supporting evidence."}
                </p>
                <label className="mt-5 block text-sm font-semibold">
                  Additional supporting documents (up to 4 PDFs, JPGs, or PNGs; 10 MB each)
                  <input
                    type="file"
                    multiple
                    accept=".pdf,.jpg,.jpeg,.png"
                    aria-label="Additional supporting documents"
                    className="mt-3 block w-full text-sm"
                    onChange={(event) => {
                      const files = [...(event.target.files || [])];
                      event.target.value = "";
                      if (
                        files.length > 4 || files.some((file) =>
                          !["application/pdf", "image/jpeg", "image/png"].includes(file.type) ||
                          !/\.(pdf|jpe?g|png)$/i.test(file.name) ||
                          !file.size || file.size > 10 * 1024 * 1024,
                        )
                      ) {
                        setFundsError("Choose up to 4 nonempty PDFs, JPGs, or PNGs, at most 10 MB each.");
                        return;
                      }
                      setEvidenceFiles(files);
                      setFundsError("");
                      setSuccess("");
                    }}
                  />
                </label>
                {evidenceFiles.length > 0 && <ul className="mt-3 space-y-1 text-sm text-muted">{evidenceFiles.map((file, index) => <li key={index} className="break-all">{file.name}</li>)}</ul>}
                <p className="mt-3 text-sm leading-6 text-muted">Documents stay private. Sending evidence returns your campaign to human review.</p>
                <button type="submit" className="button button-primary mt-5">{busy ? "Sending evidence…" : "Send Additional Evidence"}</button>
              </fieldset>
            </form>
          )}
          <p className="mt-2 text-sm leading-6 text-muted">
            Record funds received or spent. Each report needs administrator approval before it
            updates public totals. Do not include donor names, account numbers, or other private data.
          </p>
          {selected.status === "verified" ? <form key={selected.public_id} onSubmit={submitFunds} className="mt-5">
            <fieldset disabled={busy || fundsLoading} className="grid min-w-0 gap-5 md:grid-cols-2">
              <label className="block text-sm font-semibold">Report type
                <select name="kind" className="mt-2 w-full rounded-xl border border-line bg-white p-3 text-sm">
                  <option value="received">Funds received</option><option value="spent">Funds spent</option>
                </select>
              </label>
              <label className="block text-sm font-semibold">Amount (PHP) *
                <input name="amount" type="number" min="0.01" step="0.01" required className="mt-2 w-full rounded-xl border border-line p-3 text-sm" />
              </label>
              <label className="block text-sm font-semibold">Transaction date *
                <input name="occurred_on" type="date" required className="mt-2 w-full rounded-xl border border-line p-3 text-sm" />
              </label>
              <label className="block text-sm font-semibold">Public description *
                <textarea name="description" required maxLength={1000} rows={3} className="mt-2 w-full rounded-xl border border-line p-3 text-sm" />
              </label>
              <button className="button button-primary md:col-span-2 md:justify-self-start" type="submit">{busy ? "Saving report…" : "Submit Fund Report"}</button>
            </fieldset>
          </form> : <p className="mt-5 rounded-xl bg-canvas p-4 text-sm text-muted">Fund reporting becomes available after campaign approval.</p>}
          {fundsError && <p role="alert" className="mt-5 rounded-xl bg-soft-red p-4 text-sm text-brand">{fundsError}</p>}
          {success && <p role="status" className="mt-5 rounded-xl bg-green-50 p-4 text-sm text-success">{success}</p>}
          <h3 className="mt-8 text-lg font-extrabold">Report History</h3>
          {fundsLoading ? <p role="status" className="mt-4 text-sm text-muted">Loading fund reports…</p> : updates.length ? (
            <ul className="mt-4 divide-y divide-line">
              {updates.map((update) => (
                <li key={update.public_id} className="flex flex-col justify-between gap-3 py-4 sm:flex-row">
                  <div className="min-w-0">
                    <p className="whitespace-pre-wrap break-words text-sm font-semibold">{update.description}</p>
                    <p className="mt-1 text-xs text-muted">{update.occurred_on} · {update.kind === "received" ? "Received" : "Spent"} {money(update.amount_centavos)}</p>
                    {update.review_reason && <p className="mt-2 break-words text-sm text-muted">Reviewer feedback: {update.review_reason}</p>}
                  </div>
                  <span className={`badge shrink-0 self-start capitalize ${update.status === "approved" ? "badge-green" : "badge-amber"}`}>{update.status}</span>
                </li>
              ))}
            </ul>
          ) : !fundsError && <p className="mt-4 text-sm text-muted">No fund reports submitted yet.</p>}
        </section>
      )}
    </main>
  );
}
