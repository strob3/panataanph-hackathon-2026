import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { FileText, ShieldCheck, Users } from "lucide-react";
import {
  extractDocument,
  getAdminCampaign,
  listAdminAccounts,
  listAdminCampaigns,
  reviewCampaign,
  reviewFundUpdate,
  verifyAccount,
} from "../lib/accountApi";
import type {
  AdminCampaignDetail,
  AdminCampaignSummary,
  CampaignStatus,
  ReviewInput,
  User,
} from "../lib/accountApi";

const label = (value: string) => value.split("_").join(" ");
const message = (error: unknown) =>
  error instanceof Error ? error.message : "Unable to connect. Please try again.";
const money = (amount: number) =>
  new Intl.NumberFormat("en-PH", { style: "currency", currency: "PHP" }).format(amount);
const reviewedDate = (value: string) =>
  new Date(/[Z+-]\d*:?\d*$/.test(value) ? value : `${value}Z`).toLocaleString("en-PH");
const criteria = [
  ["permits", "Applicable permits or authorizations reviewed", 30],
  ["identity", "Organizer identity and registration reviewed", 20],
  ["consistency", "Organizer and payment details match", 20],
  ["history", "Previous reviewed campaign history confirmed", 10],
] as const;

function FundReview({
  update,
  onReviewed,
}: {
  update: AdminCampaignDetail["fund_updates"][number];
  onReviewed: () => Promise<void>;
}) {
  const [reason, setReason] = useState("");
  const [decision, setDecision] = useState<"approved" | "rejected">("approved");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (busy || !reason.trim()) return;
    setBusy(true);
    setError("");
    try {
      await reviewFundUpdate(update.public_id, decision, reason.trim());
      await onReviewed();
    } catch (failure) {
      setError(message(failure));
    } finally {
      setBusy(false);
    }
  };
  return (
    <article className="rounded-xl border border-line p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="font-bold">
          {label(update.kind)} · {money(update.amount_centavos / 100)}
        </p>
        <span className="badge badge-neutral">{label(update.status)}</span>
      </div>
      <p className="mt-2 break-words text-sm leading-6">{update.description}</p>
      <p className="mt-1 text-xs text-muted">Transaction date: {update.occurred_on}</p>
      {update.review_reason && (
        <p className="mt-2 break-words text-sm text-muted">Review: {update.review_reason}</p>
      )}
      {update.status === "pending" && (
        <form onSubmit={submit} className="mt-4 space-y-3">
          {error && (
            <p role="alert" className="text-sm text-brand">
              {error}
            </p>
          )}
          <label className="block text-sm font-semibold">
            Fund update decision
            <select
              aria-label="Fund update decision"
              value={decision}
              onChange={(event) => setDecision(event.target.value as "approved" | "rejected")}
              disabled={busy}
              className="mt-2 w-full rounded-xl border border-line bg-white p-3"
            >
              <option value="approved">Approve for transparency ledger</option>
              <option value="rejected">Reject update</option>
            </select>
          </label>
          <label className="block text-sm font-semibold">
            Fund update review reason
            <textarea
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              required
              maxLength={1000}
              rows={2}
              disabled={busy}
              className="mt-2 w-full rounded-xl border border-line p-3"
            />
          </label>
          <button
            type="submit"
            className="button button-secondary w-full sm:w-auto"
            disabled={busy || !reason.trim()}
          >
            {busy ? "Saving…" : "Save fund review"}
          </button>
        </form>
      )}
    </article>
  );
}

function CampaignReview({ id, revision, onReviewed }: { id: string; revision: number; onReviewed: () => void }) {
  const [campaign, setCampaign] = useState<AdminCampaignDetail | null>(null);
  const [extracting, setExtracting] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [reason, setReason] = useState("");
  const [decision, setDecision] = useState<ReviewInput["decision"]>("under_review");
  const [warningsResolved, setWarningsResolved] = useState(false);
  const [overrideThreshold, setOverrideThreshold] = useState(false);
  const [overrideReason, setOverrideReason] = useState("");
  const [checks, setChecks] = useState({
    permits: false,
    identity: false,
    consistency: false,
    history: false,
  });
  useEffect(() => {
    const controller = new AbortController();
    getAdminCampaign(id, controller.signal)
      .then((result) => {
        setCampaign(result);
        setDecision(result.status === "under_review" ? "needs_information" : "under_review");
        setChecks({ permits: false, identity: false, consistency: false, history: false });
        setWarningsResolved(false);
        setOverrideThreshold(false);
        setOverrideReason("");
      })
      .catch((failure) => {
        if (!controller.signal.aborted) setError(message(failure));
      });
    return () => controller.abort();
  }, [id, revision]);
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (busy || !reason.trim()) return;
    setError("");
    setNotice("");
    setBusy(true);
    try {
      const updated = await reviewCampaign(id, {
        ...checks,
        decision,
        reason: reason.trim(),
        override_threshold: decision === "verified" && overrideThreshold,
        override_reason:
          decision === "verified" && overrideThreshold ? overrideReason.trim() : null,
        warnings_resolved: decision === "verified" && warningsResolved,
      });
      setCampaign(updated);
      setDecision(updated.status === "under_review" ? "needs_information" : "under_review");
      setReason("");
      setWarningsResolved(false);
      setOverrideThreshold(false);
      setOverrideReason("");
      setNotice(`Review saved. Campaign is ${label(updated.status)}.`);
      onReviewed();
    } catch (failure) {
      setError(message(failure));
    } finally {
      setBusy(false);
    }
  };
  const extract = async (documentId: number) => {
    if (extracting !== null) return;
    setExtracting(documentId);
    setError("");
    try {
      await extractDocument(documentId);
      setCampaign(await getAdminCampaign(id));
    } catch (failure) {
      setError(message(failure));
    } finally {
      setExtracting(null);
    }
  };
  if (!campaign)
    return (
      <p role={error ? "alert" : "status"} className="report-card text-sm text-muted">
        {error || "Loading campaign evidence…"}
      </p>
    );

  const details = [
    ["Organizer", campaign.organizer_name],
    ["Organization", campaign.organization_name],
    ["Location", campaign.location],
    ["Purpose", campaign.purpose],
    ["Beneficiaries", campaign.beneficiaries],
    ["Target", money(campaign.target_amount)],
    ["Payment method", campaign.payment_method],
    ["Payment details", campaign.payment_details],
    ["Private contact email", campaign.organizer_email],
    ["Private contact phone", campaign.organizer_phone],
  ];
  return (
    <div className="min-w-0 space-y-5">
      <section className="report-card">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="min-w-0 break-words text-xl font-extrabold">{campaign.title}</h2>
          <span className="badge badge-neutral capitalize">{label(campaign.status)}</span>
        </div>
        <p className="mt-3 break-words text-sm leading-7 text-muted">{campaign.description}</p>
        <dl className="mt-5 grid gap-4 text-sm sm:grid-cols-2">
          {details.map(([name, value]) => (
            <div key={name}>
              <dt className="font-bold">{name}</dt>
              <dd className="mt-1 whitespace-pre-wrap break-words text-muted">
                {value || "Not provided"}
              </dd>
            </div>
          ))}
        </dl>
        <div
          className={`mt-5 rounded-xl p-4 text-sm ${campaign.owner?.verified ? "bg-green-50 text-green-800" : "bg-amber-50 text-amber-900"}`}
        >
          {campaign.owner
            ? `Account: ${campaign.owner.name} (${campaign.owner.email}) — ${campaign.owner.verified ? "verified" : "awaiting verification"}.`
            : "No organizer account linked. This campaign cannot be approved until ownership is established."}
        </div>
      </section>

      <section className="report-card">
        <h2 className="text-lg font-extrabold">Private supporting documents</h2>
        <p className="mt-2 text-sm leading-6 text-muted">
          Inspect originals before checking evidence. Extraction assists review; unreadable or
          missing fields require further investigation.
        </p>
        <div className="mt-4 space-y-3">
          {!campaign.documents.length && (
            <p className="text-sm text-muted">No supporting documents attached.</p>
          )}
          {campaign.documents.map((document) => (
            <article key={document.public_id} className="min-w-0 rounded-xl border border-line p-4">
              <a
                href={document.url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex max-w-full items-start gap-2 font-semibold text-brand underline underline-offset-4"
              >
                <FileText size={18} className="mt-0.5 shrink-0" />
                <span className="break-all">{document.original_filename}</span>
                <span className="sr-only"> (opens new tab)</span>
              </a>
              <p className="mt-2 text-xs text-muted">
                {document.file_type} · {label(document.processing_status)}
              </p>
              <button
                type="button"
                className="button button-secondary mt-3"
                disabled={extracting !== null || document.processing_status === "processing"}
                onClick={() => extract(document.id)}
              >
                {extracting === document.id ? "Extracting text…" : document.extraction ? "Extract text again" : "Extract text"}
              </button>
              {document.extraction ? (
                <dl className="mt-3 grid gap-3 text-sm sm:grid-cols-2">
                  {Object.entries(document.extraction).map(([name, value]) => (
                    <div key={name}>
                      <dt className="font-semibold capitalize">{label(name)}</dt>
                      <dd className="mt-1 whitespace-pre-wrap break-words text-muted">
                        {value === null
                          ? "Not extracted"
                          : Array.isArray(value)
                            ? value.join(", ") || "None"
                            : typeof value === "object"
                              ? JSON.stringify(value)
                              : String(value)}
                      </dd>
                    </div>
                  ))}
                </dl>
              ) : (
                <p className="mt-3 text-sm text-muted">
                  No extracted fields available. Review original document.
                </p>
              )}
            </article>
          ))}
        </div>
      </section>

      <section className="report-card">
        <h2 className="text-lg font-extrabold">Donation QR destinations</h2>
        <p className="mt-2 text-sm leading-6 text-muted">
          Compare uploaded QR codes with organizer and payment details before marking consistency.
        </p>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          {campaign.qr_codes?.length ? (
            campaign.qr_codes.map((qr) => (
              <figure key={qr.public_id} className="min-w-0 rounded-xl border border-line p-4">
                <img
                  src={qr.image_url}
                  alt={`Donation QR for ${qr.label}`}
                  loading="lazy"
                  className="mx-auto aspect-square max-h-64 max-w-full object-contain"
                />
                <figcaption className="mt-3 break-words text-center text-sm font-semibold">
                  {qr.label}
                </figcaption>
              </figure>
            ))
          ) : (
            <p className="text-sm text-muted">No donation QR codes attached.</p>
          )}
        </div>
      </section>

      <section className="report-card">
        <h2 className="text-lg font-extrabold">Evidence completeness</h2>
        <p className="mt-2 text-sm leading-6 text-muted">
          Recorded score:{" "}
          <strong className="text-ink">
            {campaign.verification_score ?? "Not scored"}
            {campaign.verification_score !== null && "/100"}
          </strong>
          . Normal publication requires at least {campaign.minimum_score}/100. A reviewer can record
          an exception for a lower score with a reason. A verified organizer account, resolved major
          warnings, and human approval remain required. Missing evidence does not imply fraud.
        </p>
        <dl className="mt-4 space-y-3">
          {campaign.findings.map((finding, index) => (
            <div key={`${finding.criterion}-${index}`} className="rounded-xl bg-canvas p-3 text-sm">
              <div className="flex justify-between gap-4">
                <dt className="min-w-0 break-words capitalize">{label(finding.criterion)}</dt>
                <dd className="shrink-0 font-bold">
                  {finding.points_awarded}/{finding.points_possible}
                </dd>
              </div>
              {finding.details && <p className="mt-1 break-words text-muted">{finding.details}</p>}
            </div>
          ))}
        </dl>
        <form onSubmit={submit} className="mt-6 space-y-5 border-t border-line pt-5">
          {error && (
            <p role="alert" className="rounded-xl bg-red-50 p-3 text-sm text-brand">
              {error}
            </p>
          )}
          {notice && (
            <p role="status" className="rounded-xl bg-green-50 p-3 text-sm text-green-800">
              {notice}
            </p>
          )}
          <fieldset disabled={busy}>
            <legend className="text-sm font-bold">Confirm only evidence you reviewed</legend>
            <div className="mt-3 space-y-3">
              {criteria.map(([name, text, points]) => (
                <label
                  key={name}
                  className="flex cursor-pointer items-start gap-3 rounded-xl border border-line p-3 text-sm"
                >
                  <input
                    type="checkbox"
                    checked={checks[name]}
                    onChange={(event) =>
                      setChecks((previous) => ({ ...previous, [name]: event.target.checked }))
                    }
                    className="mt-0.5 size-4 shrink-0 accent-brand"
                  />
                  <span>
                    {text} <span className="text-muted">({points} points)</span>
                  </span>
                </label>
              ))}
            </div>
            <p className="mt-3 text-xs leading-5 text-muted">
              Remaining 20 points come from required campaign information, calculated by backend.
              Evidence boxes start unchecked for each campaign.
            </p>
            <p className="mt-2 text-xs leading-5 text-muted">
              Standard approval requires reviewed permits, organizer identity, and matching payment
              details. Missing evidence needs further review or a recorded threshold exception.
            </p>
          </fieldset>
          <label className="block text-sm font-semibold">
            Campaign decision
            <select
              aria-label="Campaign decision"
              value={decision}
              onChange={(event) => setDecision(event.target.value as ReviewInput["decision"])}
              disabled={busy}
              className="mt-2 w-full rounded-xl border border-line bg-white p-3"
            >
              {campaign.status === "under_review" ? (
                <>
                  <option value="needs_information">Request more information</option>
                  <option value="verified" disabled={!campaign.owner?.verified}>
                    Verify and publish campaign
                  </option>
                  <option value="rejected">Reject campaign</option>
                </>
              ) : (
                <option value="under_review">
                  {campaign.status === "pending" ? "Start review" : "Reopen review"}
                </option>
              )}
            </select>
          </label>
          <label className="block text-sm font-semibold">
            Review reason
            <textarea
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              required
              maxLength={4000}
              rows={3}
              disabled={busy}
              className="mt-2 w-full rounded-xl border border-line p-3"
              placeholder="Describe evidence checked, missing information, and reasons for this decision."
            />
          </label>
          {decision === "verified" && (
            <fieldset disabled={busy} className="space-y-4">
              <legend className="text-sm font-bold">Publication checks</legend>
              <p className="rounded-xl bg-amber-50 p-3 text-sm leading-6 text-amber-900">
                Approving publishes campaign details and donation destinations. Review applicable
                authorizations, warnings, and major inconsistencies before saving. A threshold
                exception does not bypass organizer verification or unresolved warnings.
              </p>
              <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-line p-3 text-sm">
                <input
                  type="checkbox"
                  checked={warningsResolved}
                  onChange={(event) => setWarningsResolved(event.target.checked)}
                  required
                  className="mt-0.5 size-4 shrink-0 accent-brand"
                />
                <span>Warnings and major inconsistencies reviewed and resolved</span>
              </label>
              <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-line p-3 text-sm">
                <input
                  type="checkbox"
                  checked={overrideThreshold}
                  onChange={(event) => setOverrideThreshold(event.target.checked)}
                  className="mt-0.5 size-4 shrink-0 accent-brand"
                />
                <span>Override evidence score threshold</span>
              </label>
              {overrideThreshold && (
                <label className="block text-sm font-semibold">
                  Threshold override reason
                  <textarea
                    value={overrideReason}
                    onChange={(event) => setOverrideReason(event.target.value)}
                    aria-label="Threshold override reason"
                    aria-describedby="threshold-override-help"
                    required
                    maxLength={4000}
                    rows={3}
                    className="mt-2 w-full rounded-xl border border-line p-3"
                    placeholder="Explain why publication is appropriate despite missing evidence points. This exception is recorded in review history."
                  />
                  <span
                    id="threshold-override-help"
                    className="mt-2 block text-xs font-normal leading-5 text-muted"
                  >
                    An exception applies only when the backend's reviewed score is below{" "}
                    {campaign.minimum_score}/100. It does not add evidence points.
                  </span>
                </label>
              )}
            </fieldset>
          )}
          <button
            type="submit"
            className="button button-primary w-full sm:w-auto"
            disabled={
              busy ||
              !reason.trim() ||
              (decision === "verified" &&
                (!campaign.owner?.verified ||
                  !warningsResolved ||
                  (overrideThreshold
                    ? !overrideReason.trim()
                    : !checks.permits || !checks.identity || !checks.consistency)))
            }
          >
            {busy
              ? "Saving review…"
              : decision === "under_review"
                ? "Start review"
                : decision === "verified"
                  ? "Verify and publish"
                  : "Save campaign review"}
          </button>
        </form>
      </section>

      <section className="report-card">
        <h2 className="text-lg font-extrabold">Funds transparency review</h2>
        <p className="mt-2 text-sm leading-6 text-muted">
          Only approved organizer-reported updates appear in public totals. Review descriptions
          against supporting records.
        </p>
        <div className="mt-4 space-y-3">
          {campaign.fund_updates.length ? (
            campaign.fund_updates.map((update) => (
              <FundReview
                key={update.public_id}
                update={update}
                onReviewed={async () => {
                  setCampaign(await getAdminCampaign(id));
                }}
              />
            ))
          ) : (
            <p className="text-sm text-muted">No fund updates submitted.</p>
          )}
        </div>
      </section>

      <section className="report-card">
        <h2 className="text-lg font-extrabold">Review history</h2>
        <ol className="mt-4 space-y-3">
          {campaign.reviews.map((review, index) => (
            <li
              key={`${review.reviewed_at}-${index}`}
              className="rounded-xl border border-line p-4 text-sm"
            >
              <p className="font-semibold capitalize">
                {label(review.previous_status ?? "unknown")} → {label(review.new_status)}
              </p>
              <p className="mt-1 break-words text-muted">{review.reason}</p>
              {review.threshold_override && (
                <p className="mt-2 rounded-xl bg-amber-50 p-3 text-sm text-amber-900">
                  Evidence score threshold exception: {review.override_reason}
                </p>
              )}
              {review.warnings_resolved && (
                <p className="mt-2 text-xs text-muted">
                  Reviewer confirmed warnings and major inconsistencies resolved.
                </p>
              )}
              <p className="mt-2 break-words text-xs text-muted">
                {review.admin_username} · {reviewedDate(review.reviewed_at)}
              </p>
            </li>
          ))}
        </ol>
        {!campaign.reviews.length && (
          <p className="mt-3 text-sm text-muted">No reviews recorded.</p>
        )}
      </section>
    </div>
  );
}

function AccountVerification() {
  const [accounts, setAccounts] = useState<User[]>([]);
  const [total, setTotal] = useState(0);
  const [skip, setSkip] = useState(0);
  const [selected, setSelected] = useState<User | null>(null);
  const [reason, setReason] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    listAdminAccounts(controller.signal, skip)
      .then((result) => {
        setAccounts(result.items);
        setTotal(result.total);
      })
      .catch((failure) => {
        if (!controller.signal.aborted) setError(message(failure));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [skip]);
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selected || busy || !reason.trim()) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const updated = await verifyAccount(selected.id, !selected.verified, reason.trim());
      setSelected(updated);
      setAccounts((previous) =>
        previous.map((account) => (account.id === updated.id ? updated : account)),
      );
      setReason("");
      setNotice(
        updated.verified
          ? "Organizer account verified."
          : "Account verification revoked. Its campaigns are excluded from the public directory.",
      );
    } catch (failure) {
      setError(message(failure));
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,.8fr)_minmax(0,1.2fr)]">
      <section className="report-card min-w-0">
        <h2 className="text-lg font-extrabold">Organizer accounts</h2>
        <p className="mt-2 text-sm leading-6 text-muted">
          Inspect campaign evidence under Campaign review before verifying organizer identity.
        </p>
        {loading ? (
          <p role="status" className="mt-4 text-sm text-muted">
            Loading accounts…
          </p>
        ) : (
          <div className="mt-4 space-y-2">
            {accounts.map((account) => (
              <button
                key={account.id}
                disabled={busy}
                onClick={() => {
                  setSelected(account);
                  setReason("");
                  setError("");
                  setNotice("");
                }}
                aria-pressed={selected?.id === account.id}
                className={`w-full rounded-xl border p-3 text-left ${selected?.id === account.id ? "border-brand bg-soft-red" : "border-line bg-white"}`}
              >
                <span className="block break-words text-sm font-bold">{account.name}</span>
                <span className="mt-1 block break-all text-xs text-muted">{account.email}</span>
                <span className="mt-2 block text-xs font-semibold">
                  {account.role} · {account.verified ? "Verified" : "Awaiting verification"}
                </span>
              </button>
            ))}
            {!accounts.length && <p className="text-sm text-muted">No accounts found.</p>}
          </div>
        )}
        <div className="mt-4 flex flex-wrap items-center justify-between gap-2 text-xs text-muted">
          <span>
            {total ? `${skip + 1}–${Math.min(skip + 20, total)} of ${total}` : "0 accounts"}
          </span>
          <div className="flex gap-2">
            <button
              type="button"
              className="button button-secondary"
              disabled={skip === 0 || loading || busy}
              onClick={() => setSkip((previous) => Math.max(0, previous - 20))}
            >
              Previous
            </button>
            <button
              type="button"
              className="button button-secondary"
              disabled={skip + 20 >= total || loading || busy}
              onClick={() => setSkip((previous) => previous + 20)}
            >
              Next
            </button>
          </div>
        </div>
      </section>
      <section className="report-card min-w-0">
        <h2 className="text-lg font-extrabold">Account verification</h2>
        {error && (
          <p role="alert" className="mt-3 rounded-xl bg-red-50 p-3 text-sm text-brand">
            {error}
          </p>
        )}
        {notice && (
          <p role="status" className="mt-3 rounded-xl bg-green-50 p-3 text-sm text-green-800">
            {notice}
          </p>
        )}
        {selected ? (
          <>
            <dl className="mt-4 space-y-3 text-sm">
              <div>
                <dt className="font-bold">Full name</dt>
                <dd className="mt-1 break-words text-muted">{selected.name}</dd>
              </div>
              <div>
                <dt className="font-bold">Email</dt>
                <dd className="mt-1 break-all text-muted">{selected.email}</dd>
              </div>
              <div>
                <dt className="font-bold">Verification</dt>
                <dd className="mt-1 text-muted">
                  {selected.verified ? "Verified" : "Awaiting verification"}
                </dd>
              </div>
            </dl>
            {selected.role === "organizer" ? (
              <form onSubmit={submit} className="mt-5 space-y-4">
                <p className="text-sm leading-6 text-muted">
                  Verify identity using submitted records. Account verification alone does not
                  approve any campaign.
                </p>
                <label className="block text-sm font-semibold">
                  Account verification reason
                  <textarea
                    required
                    rows={3}
                    maxLength={4000}
                    value={reason}
                    onChange={(event) => setReason(event.target.value)}
                    disabled={busy}
                    className="mt-2 w-full rounded-xl border border-line p-3"
                  />
                </label>
                {selected.verified && (
                  <p className="rounded-xl bg-amber-50 p-3 text-sm leading-6 text-amber-900">
                    Revoking verification removes this organizer's campaigns from the public
                    directory until account verification is restored.
                  </p>
                )}
                <button
                  type="submit"
                  disabled={busy || !reason.trim()}
                  className="button button-primary w-full sm:w-auto"
                >
                  {busy
                    ? "Saving…"
                    : selected.verified
                      ? "Revoke account verification"
                      : "Verify organizer account"}
                </button>
              </form>
            ) : (
              <p className="mt-4 text-sm text-muted">
                Reviewer accounts are provisioned by the project administrator.
              </p>
            )}
          </>
        ) : (
          <p className="mt-4 text-sm text-muted">Select an organizer account to review.</p>
        )}
      </section>
    </div>
  );
}

export function AdminPage({ user, go }: { user: User; go: (path: string) => void }) {
  const [section, setSection] = useState<"campaigns" | "accounts">("campaigns");
  const [status, setStatus] = useState<CampaignStatus | "">("pending");
  const [campaigns, setCampaigns] = useState<AdminCampaignSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [skip, setSkip] = useState(0);
  const [selected, setSelected] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  const allowed = user.role === "admin" || user.role === "lgu";
  useEffect(() => {
    if (!allowed || section !== "campaigns") return;
    const controller = new AbortController();
    setLoading(true);
    setError("");
    listAdminCampaigns(status, controller.signal, skip)
      .then((result) => {
        setCampaigns(result.items);
        setTotal(result.total);
      })
      .catch((failure) => {
        if (!controller.signal.aborted) setError(message(failure));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [allowed, section, status, skip, revision]);
  if (!allowed)
    return (
      <main className="container py-12">
        <div className="report-card">
          <h1 className="text-2xl font-extrabold">Administrator access required</h1>
          <p className="mt-3 text-sm text-muted">
            Only assigned administrators and LGU reviewers can review private evidence.
          </p>
          <button className="button button-secondary mt-5" onClick={() => go("/campaigns")}>
            Browse campaigns
          </button>
        </div>
      </main>
    );
  return (
    <main className="container py-8 sm:py-12">
      <span className="badge badge-red">
        <ShieldCheck size={15} /> {user.role === "lgu" ? "LGU reviewer" : "Administrator"}
      </span>
      <h1 className="mt-4 text-3xl font-extrabold tracking-tight sm:text-4xl">Review dashboard</h1>
      <p className="mt-3 max-w-3xl text-sm leading-7 text-muted">
        Review organizer accounts, campaign evidence, and reported fund updates. Decisions are
        recorded with reviewer identity and reason.
      </p>
      <nav className="mt-6 flex flex-wrap gap-3" aria-label="Review sections">
        <button
          className={`button ${section === "campaigns" ? "button-primary" : "button-secondary"}`}
          onClick={() => setSection("campaigns")}
          aria-current={section === "campaigns" ? "page" : undefined}
        >
          <FileText size={17} /> Campaign review
        </button>
        <button
          className={`button ${section === "accounts" ? "button-primary" : "button-secondary"}`}
          onClick={() => setSection("accounts")}
          aria-current={section === "accounts" ? "page" : undefined}
        >
          <Users size={17} /> Account verification
        </button>
      </nav>
      <div className="mt-6">
        {section === "accounts" ? (
          <AccountVerification />
        ) : (
          <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,.7fr)_minmax(0,1.3fr)]">
            <section className="report-card min-w-0">
              <h2 className="text-lg font-extrabold">Campaign queue</h2>
              <label className="mt-4 block text-sm font-semibold">
                Campaign status
                <select
                  aria-label="Campaign status"
                  value={status}
                  onChange={(event) => {
                    setStatus(event.target.value as CampaignStatus | "");
                    setSkip(0);
                  }}
                  className="mt-2 w-full rounded-xl border border-line bg-white p-3"
                >
                  <option value="">All statuses</option>
                  {["pending", "under_review", "needs_information", "verified", "rejected"].map(
                    (value) => (
                      <option key={value} value={value}>
                        {label(value)}
                      </option>
                    ),
                  )}
                </select>
              </label>
              <button
                className="button button-secondary mt-3 w-full"
                disabled={loading}
                onClick={() => setRevision((previous) => previous + 1)}
              >
                Refresh queue
              </button>
              {error && (
                <p role="alert" className="mt-4 text-sm text-brand">
                  {error}
                </p>
              )}
              {loading ? (
                <p role="status" className="mt-4 text-sm text-muted">
                  Loading campaigns…
                </p>
              ) : (
                <div className="mt-4 space-y-3">
                  {campaigns.map((campaign) => (
                    <button
                      key={campaign.public_id}
                      onClick={() => setSelected(campaign.public_id)}
                      aria-pressed={selected === campaign.public_id}
                      className={`w-full rounded-xl border p-4 text-left ${selected === campaign.public_id ? "border-brand bg-soft-red" : "border-line bg-white"}`}
                    >
                      <span className="block break-words text-sm font-bold">{campaign.title}</span>
                      <span className="mt-1 block break-words text-xs text-muted">
                        {campaign.organizer_name} · {campaign.location}
                      </span>
                      <span className="mt-2 block text-xs font-semibold capitalize">
                        {label(campaign.status)} · {campaign.verification_score ?? "Unscored"}
                        {campaign.verification_score !== null ? "/100" : ""}
                      </span>
                    </button>
                  ))}
                  {!campaigns.length && (
                    <p className="text-sm text-muted">No campaigns in this queue.</p>
                  )}
                </div>
              )}
              <div className="mt-4 flex flex-wrap items-center justify-between gap-2 text-xs text-muted">
                <span>
                  {total ? `${skip + 1}–${Math.min(skip + 20, total)} of ${total}` : "0 campaigns"}
                </span>
                <div className="flex gap-2">
                  <button
                    type="button"
                    className="button button-secondary"
                    disabled={skip === 0 || loading}
                    onClick={() => setSkip((previous) => Math.max(0, previous - 20))}
                  >
                    Previous
                  </button>
                  <button
                    type="button"
                    className="button button-secondary"
                    disabled={skip + 20 >= total || loading}
                    onClick={() => setSkip((previous) => previous + 20)}
                  >
                    Next
                  </button>
                </div>
              </div>
            </section>
            {selected ? (
              <CampaignReview
                key={selected}
                id={selected}
                revision={revision}
                onReviewed={() => setRevision((previous) => previous + 1)}
              />
            ) : (
              <p className="report-card text-sm text-muted">
                Select a campaign to inspect its private evidence and review history.
              </p>
            )}
          </div>
        )}
      </div>
    </main>
  );
}
