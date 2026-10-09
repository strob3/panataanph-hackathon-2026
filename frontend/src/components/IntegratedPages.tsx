import { useEffect, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import {
  ArrowRight,
  BadgeCheck,
  Download,
  HeartHandshake,
  MapPin,
  Search,
  ShieldCheck,
  Upload,
  X,
} from "lucide-react";
import { getCampaign, listCampaigns, submitCampaign } from "../lib/api";
import type { Campaign, CampaignDetail, CampaignPage, Submission } from "../lib/api";

type Navigate = (path: string) => void;
const message = (error: unknown) =>
  error instanceof Error ? error.message : "Unable to connect to the API. Please try again.";
const date = (value: string) =>
  new Date(/^\d{4}-\d{2}-\d{2}$/.test(value) ? `${value}T00:00:00` : value.endsWith("Z") ? value : `${value}Z`).toLocaleDateString("en-PH");
const money = (value: number) =>
  new Intl.NumberFormat("en-PH", { style: "currency", currency: "PHP" }).format(value);

function Notice({ children, error = false }: { children: ReactNode; error?: boolean }) {
  return (
    <p
      role={error ? "alert" : "status"}
      className={`rounded-xl p-4 text-sm ${
        error ? "bg-red-50 text-brand" : "bg-zinc-100 text-muted"
      }`}
    >
      {children}
    </p>
  );
}

function Field({
  name,
  label,
  required = false,
  type = "text",
  maxLength,
}: {
  name: string;
  label: string;
  required?: boolean;
  type?: string;
  maxLength?: number;
}) {
  const classes =
    "mt-2 w-full rounded-xl border border-line bg-white p-3 text-sm outline-none focus:border-brand";
  return (
    <label className="block text-sm font-semibold text-ink">
      {label}
      {required && " *"}
      {type === "textarea" ? (
        <textarea
          name={name}
          required={required}
          maxLength={maxLength}
          rows={4}
          className={classes}
        />
      ) : (
        <input
          name={name}
          required={required}
          type={type}
          maxLength={maxLength}
          min={type === "number" ? "0.01" : undefined}
          step={type === "number" ? "0.01" : undefined}
          className={classes}
        />
      )}
    </label>
  );
}

const uploadZones = [
  ["fundraiser", "Fundraiser Screenshot", "The original fundraiser post"],
  ["permit", "Permit / Registration", "DSWD permit or registration record"],
  ["payment", "Payment Screenshot", "Bank, e-wallet, or QR payment details"],
  ["other", "Other Supporting Document", "Receipts, IDs, or organizer evidence"],
];

export function SubmissionPage({
  go,
  onSubmitted,
}: {
  go: Navigate;
  onSubmitted: (submission: Submission) => void;
}) {
  const [files, setFiles] = useState<Record<string, File>>({});
  const [donationQR, setDonationQR] = useState<File>();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const addFile = (key: string, file?: File) => {
    if (!file) return;
    if (
      !["image/jpeg", "image/png", "application/pdf"].includes(file.type) ||
      !/\.(pdf|jpe?g|png)$/i.test(file.name)
    ) {
      setError("Please choose a PDF, JPG, or PNG document.");
      return;
    }
    if (file.size === 0 || file.size > 10 * 1024 * 1024) {
      setError("Each document must be nonempty and at most 10 MB.");
      return;
    }
    setError("");
    setFiles((current) => ({ ...current, [key]: file }));
  };
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (busy) return;
    if (!Object.keys(files).length) {
      setError("Add at least one supporting document.");
      return;
    }
    const fields = Object.fromEntries(
      [...new FormData(event.currentTarget).entries()].filter(([, value]) => typeof value === "string"),
    ) as Record<string, string>;
    Object.keys(fields).forEach((key) => {
      fields[key] = fields[key].trim();
    });
    if (
      ["organizer_name", "title", "description", "purpose", "location"].some((key) => !fields[key])
    ) {
      setError("Complete all required campaign fields.");
      return;
    }
    if (donationQR && !fields.qr_label) {
      setError("Add a donation QR label, including its payment provider and account name.");
      return;
    }
    setError("");
    setBusy(true);
    try {
      const result = await submitCampaign(fields, Object.values(files), donationQR);
      onSubmitted(result);
      go("/verify/report");
    } catch (failure) {
      setError(message(failure));
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="min-h-screen bg-canvas">
      <div className="container py-10 sm:py-14">
        <div className="mx-auto max-w-3xl text-center">
          <span className="badge badge-amber">
            <ShieldCheck size={15} /> Human review required
          </span>
          <h1 className="mt-5 text-4xl font-extrabold tracking-tight sm:text-5xl">
            Submit a Fundraiser
          </h1>
          <p className="mt-3 text-base leading-7 text-muted">
            Share campaign details and supporting evidence with PanataanPH reviewers.
          </p>
        </div>
        <form
          onSubmit={submit}
          className="mx-auto mt-10 max-w-5xl rounded-[1.75rem] border border-line bg-white p-5 shadow-xl shadow-zinc-900/5 sm:p-8"
        >
          <fieldset disabled={busy} className="min-w-0">
            <h2 className="text-xl font-extrabold">Campaign details</h2>
            <p className="mt-2 text-sm text-muted">
              Fields marked * are required. Contact information and uploaded documents are private.
            </p>
            <div className="mt-6 grid gap-5 md:grid-cols-2">
              <Field name="organizer_name" label="Organizer name" required maxLength={255} />
              <Field name="organization_name" label="Organization name" maxLength={255} />
              <Field name="organization_registration_number" label="Organizer / organization registration number" maxLength={100} />
              <Field name="organizer_email" label="Email (private)" type="email" maxLength={255} />
              <Field name="organizer_phone" label="Phone (private)" type="tel" maxLength={50} />
              <Field name="title" label="Campaign title" required maxLength={500} />
              <Field name="location" label="Location" required maxLength={255} />
              <Field name="purpose" label="Purpose" required maxLength={255} />
              <Field name="target_amount" label="Target amount (PHP)" type="number" required />
              <label className="text-sm font-semibold">
                Campaign type
                <select
                  name="cause"
                  className="mt-2 w-full rounded-xl border border-line p-3 text-sm"
                >
                  <option value="disaster_relief">Disaster relief</option>
                  <option value="medical">Medical</option>
                  <option value="education">Education</option>
                  <option value="other">Other</option>
                </select>
              </label>
              <label className="text-sm font-semibold">
                Urgency
                <select
                  name="urgency"
                  className="mt-2 w-full rounded-xl border border-line p-3 text-sm"
                >
                  <option value="normal">Normal</option>
                  <option value="low">Low</option>
                  <option value="high">High</option>
                  <option value="critical">Critical</option>
                </select>
              </label>
              <Field name="description" label="Description" type="textarea" required />
              <Field name="beneficiaries" label="Beneficiaries" type="textarea" />
              <Field
                name="payment_method"
                label="Payment method (public after approval)"
                maxLength={100}
              />
              <Field
                name="payment_details"
                label="Donation payment details (public after approval)"
                type="textarea"
              />
            </div>
            <h2 className="mt-10 text-xl font-extrabold">Donation QR (optional)</h2>
            <p className="mt-2 text-sm leading-6 text-muted">
              Upload your payment provider's real QR image. This donation image and its label become
              public only after campaign approval. Supporting evidence stays private.
            </p>
            <div className="mt-5 grid items-start gap-5 md:grid-cols-2">
              <Field
                name="qr_label"
                label="QR label / provider and account name"
                required={Boolean(donationQR)}
                maxLength={100}
              />
              <label className="block min-w-0 text-sm font-semibold">
                Donation QR image (PNG or JPG, up to 10 MB)
                <input
                  type="file"
                  aria-label="Donation QR image"
                  accept=".jpg,.jpeg,.png"
                  className="mt-3 block w-full text-sm"
                  onChange={(event) => {
                    const file = event.target.files?.[0];
                    if (!file) return;
                    if (
                      !["image/jpeg", "image/png"].includes(file.type) ||
                      !/\.(jpe?g|png)$/i.test(file.name) ||
                      !file.size || file.size > 10 * 1024 * 1024
                    ) {
                      setError("Choose a nonempty PNG or JPG donation QR image up to 10 MB.");
                      event.target.value = "";
                      return;
                    }
                    setDonationQR(file);
                    setError("");
                    event.target.value = "";
                  }}
                />
              </label>
            </div>
            {donationQR && (
              <div className="mt-4 flex min-w-0 items-center gap-3 rounded-xl bg-canvas p-3">
                <p className="min-w-0 flex-1 break-all text-sm">{donationQR.name}</p>
                <button
                  type="button"
                  className="icon-button"
                  aria-label="Remove donation QR"
                  onClick={() => setDonationQR(undefined)}
                >
                  <X size={18} />
                </button>
              </div>
            )}
            <h2 className="mt-10 text-xl font-extrabold">Add your evidence</h2>
            <p className="mt-2 text-sm text-muted">
              Add at least one document. PDF, JPG, PNG · up to 10 MB each · up to 4 files.
            </p>
            <div className="mt-5 grid gap-4 md:grid-cols-2">
              {uploadZones.map(([key, title, subtitle]) => (
                <div
                  key={key}
                  className={files[key] ? "uploaded-card" : "upload-zone"}
                  onDragOver={(event) => event.preventDefault()}
                  onDrop={(event) => {
                    event.preventDefault();
                    if (!busy) addFile(key, event.dataTransfer.files[0]);
                  }}
                >
                  {files[key] ? (
                    <>
                      <div className="file-thumb">
                        <Upload size={23} />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-bold">{files[key].name}</p>
                        <p className="mt-1 text-xs text-muted">
                          {title} · {(files[key].size / 1024 / 1024).toFixed(1)} MB
                        </p>
                        <p className="mt-2 text-xs text-success">Ready to submit</p>
                      </div>
                      <button
                        type="button"
                        className="icon-button"
                        aria-label={`Remove ${title}`}
                        onClick={() =>
                          setFiles((current) => {
                            const next = { ...current };
                            delete next[key];
                            return next;
                          })
                        }
                      >
                        <X size={18} />
                      </button>
                    </>
                  ) : (
                    <label className="flex min-h-60 cursor-pointer flex-col items-center justify-center p-7 text-center">
                      <div className="upload-icon">
                        <Upload size={22} />
                      </div>
                      <span className="mt-4 text-sm font-bold">{title}</span>
                      <span className="mt-2 text-xs text-muted">{subtitle}</span>
                      <span className="mt-3 text-xs font-semibold text-brand">
                        Browse files or drag and drop
                      </span>
                      <input
                        type="file"
                        aria-label={title}
                        accept=".pdf,.jpg,.jpeg,.png"
                        className="mt-4 max-w-full text-xs"
                        onChange={(event) => {
                          addFile(key, event.target.files?.[0]);
                          event.target.value = "";
                        }}
                      />
                    </label>
                  )}
                </div>
              ))}
            </div>
            <p className="mt-6 text-sm leading-6 text-muted">
              Supporting evidence is stored privately and reviewed by authorized administrators.
              Evidence completeness is scored using fixed rules. Documents are never sent to
              external AI services.
            </p>
            <label className="mt-5 flex items-start gap-3 text-sm leading-6">
              <input type="checkbox" required className="mt-1.5" />I agree to submit these documents
              for private review and publish the campaign and donation details if approved.
            </label>
            <div className="mt-6">{error && <Notice error>{error}</Notice>}</div>
            <div className="mt-6 flex flex-col items-center justify-between gap-4 border-t border-line pt-6 sm:flex-row">
              <p className="text-sm text-muted">
                {Object.keys(files).length} of 4 documents selected
              </p>
              <button type="submit" disabled={busy} className="button button-primary">
                {busy ? "Saving submission…" : "Submit for Review"}
                <ArrowRight size={17} />
              </button>
            </div>
          </fieldset>
        </form>
      </div>
    </main>
  );
}

export function SubmissionReport({
  submission,
  go,
}: {
  submission: Submission | null;
  go: Navigate;
}) {
  return (
    <main className="container py-12">
      <section className="report-card mx-auto max-w-2xl">
        <span className="badge badge-amber">
          {submission ? "Pending human review" : "No submission in this session"}
        </span>
        <h1 className="mt-5 text-3xl font-extrabold">
          {submission ? "Submission received" : "Submit evidence for review"}
        </h1>
        {submission ? (
          <>
            <p className="mt-4 leading-7 text-muted">
              Your {submission.documents_received} supporting documents were saved privately. Your
              campaign will appear in the public directory after human approval and the required
              evidence score, or an administrator's documented score exception.
            </p>
            <p className="mt-5 text-sm font-semibold">Submission reference</p>
            <p className="mt-2 break-all rounded-xl bg-canvas p-4 font-mono text-sm">
              {submission.public_id}
            </p>
            <p className="mt-4 text-sm text-muted">
              Keep this reference. Check My Campaigns for review status and administrator feedback.
            </p>
          </>
        ) : (
          <p className="mt-4 text-muted">
            Complete the submission form to receive a reference number.
          </p>
        )}
        <div className="mt-7 flex flex-wrap gap-3">
          <button className="button button-primary" onClick={() => go("/my-campaigns")}>
            My Campaigns
          </button>
          <button className="button button-secondary" onClick={() => go("/verify")}>
            Submit a Fundraiser
          </button>
          <button className="button button-secondary" onClick={() => go("/campaigns")}>
            Browse Campaigns
          </button>
        </div>
      </section>
    </main>
  );
}

function CampaignCard({ campaign, go }: { campaign: Campaign; go: Navigate }) {
  return (
    <article className="campaign-card">
      <div className="flex items-start justify-between gap-3">
        <div className="grid size-11 place-items-center rounded-2xl bg-soft-red text-brand">
          <HeartHandshake size={22} />
        </div>
        <span className="badge badge-green">
          <BadgeCheck size={15} /> Verified
        </span>
      </div>
      <p className="mt-5 text-xs font-bold uppercase tracking-[0.1em] text-muted">
        {campaign.organization_name || campaign.organizer_name}
      </p>
      <h2 className="mt-2 text-xl font-extrabold">{campaign.title}</h2>
      <p className="mt-2 flex items-start gap-1.5 text-sm text-muted">
        <MapPin size={15} className="mt-0.5 shrink-0" />
        {campaign.location}
      </p>
      <div className="mt-5 rounded-2xl bg-canvas p-4">
        <div className="flex justify-between text-xs">
          <span className="font-semibold text-muted">Evidence score</span>
          <span className="font-extrabold">
            {campaign.verification_score === null
              ? "Not scored"
              : `${campaign.verification_score} / 100`}
          </span>
        </div>
        {campaign.verification_score !== null && (
          <div className="mt-2 h-2 overflow-hidden rounded-full bg-zinc-100">
            <div
              className="h-full rounded-full bg-brand"
              style={{
                width: `${Math.max(0, Math.min(100, campaign.verification_score))}%`,
              }}
            />
          </div>
        )}
        <p className="mt-4 text-xs text-muted">Submitted {date(campaign.created_at)}</p>
      </div>
      <button
        className="button button-secondary mt-5 w-full"
        onClick={() => go(`/campaigns/${campaign.public_id}`)}
      >
        View Campaign <ArrowRight size={16} />
      </button>
    </article>
  );
}

export function CampaignDirectory({ go }: { go: Navigate }) {
  const [search, setSearch] = useState("");
  const [location, setLocation] = useState("");
  const [cause, setCause] = useState("");
  const [urgency, setUrgency] = useState("");
  const [skip, setSkip] = useState(0);
  const [page, setPage] = useState<CampaignPage | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    const timer = window.setTimeout(() => {
      const params = new URLSearchParams({ skip: String(skip), limit: "12" });
      if (search.trim()) params.set("search", search.trim());
      if (location.trim()) params.set("location", location.trim());
      if (cause) params.set("cause", cause);
      if (urgency) params.set("urgency", urgency);
      listCampaigns(params, controller.signal)
        .then((result) => {
          if (!controller.signal.aborted) setPage(result);
        })
        .catch((failure) => {
          if (!controller.signal.aborted) setError(message(failure));
        })
        .finally(() => {
          if (!controller.signal.aborted) setLoading(false);
        });
    }, 250);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [search, location, cause, urgency, skip, retry]);
  return (
    <main className="min-h-screen bg-canvas">
      <section className="border-b border-line bg-white">
        <div className="container py-12 sm:py-16">
          <span className="badge badge-red">Public directory</span>
          <h1 className="mt-5 text-4xl font-extrabold tracking-tight sm:text-5xl">
            Relief Campaign Directory
          </h1>
          <p className="mt-3 max-w-2xl text-lg leading-7 text-muted">
            Browse campaigns verified by human reviewers. Evidence scores describe completeness and
            do not guarantee legitimacy.
          </p>
          <label className="mt-8 flex max-w-2xl items-center gap-3 rounded-2xl border border-line px-4">
            <Search size={20} className="text-muted" />
            <input
              aria-label="Search campaigns"
              value={search}
              onChange={(event) => {
                setSearch(event.target.value);
                setSkip(0);
              }}
              className="h-13 min-w-0 flex-1 bg-transparent text-sm outline-none"
              placeholder="Search organizations or campaigns…"
            />
          </label>
        </div>
      </section>
      <div className="container py-8 sm:py-10">
        <div className="flex flex-wrap items-end gap-3">
          <label className="text-xs font-semibold text-muted">
            Location
            <input
              className="filter-button mt-2 block"
              placeholder="All locations"
              value={location}
              onChange={(event) => {
                setLocation(event.target.value);
                setSkip(0);
              }}
            />
          </label>
          <label className="text-xs font-semibold text-muted">
            Campaign type
            <select
              className="filter-button mt-2 block"
              value={cause}
              onChange={(event) => {
                setCause(event.target.value);
                setSkip(0);
              }}
            >
              <option value="">All types</option>
              <option value="disaster_relief">Disaster relief</option>
              <option value="medical">Medical</option>
              <option value="education">Education</option>
              <option value="other">Other</option>
            </select>
          </label>
          <label className="text-xs font-semibold text-muted">
            Urgency
            <select
              className="filter-button mt-2 block"
              value={urgency}
              onChange={(event) => {
                setUrgency(event.target.value);
                setSkip(0);
              }}
            >
              <option value="">All levels</option>
              <option value="low">Low</option>
              <option value="normal">Normal</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
          </label>
        </div>
        <div className="mt-7">
          {loading ? (
            <Notice>Loading verified campaigns…</Notice>
          ) : error ? (
            <>
              <Notice error>{error}</Notice>
              <button
                className="button button-secondary mt-4"
                onClick={() => setRetry((value) => value + 1)}
              >
                Try Again
              </button>
            </>
          ) : (
            page && (
              <>
                <p className="text-sm text-muted">
                  {page.total} verified campaign{page.total === 1 ? "" : "s"}
                </p>
                {page.items.length ? (
                  <div className="mt-5 grid gap-5 md:grid-cols-2 xl:grid-cols-3">
                    {page.items.map((campaign) => (
                      <CampaignCard key={campaign.public_id} campaign={campaign} go={go} />
                    ))}
                  </div>
                ) : (
                  <div className="mt-5">
                    <Notice>No verified campaigns match these filters.</Notice>
                  </div>
                )}
                <div className="mt-7 flex justify-between gap-3">
                  <button
                    className="button button-secondary"
                    disabled={skip === 0}
                    onClick={() => setSkip(Math.max(0, skip - 12))}
                  >
                    Previous
                  </button>
                  <button
                    className="button button-secondary"
                    disabled={skip + page.limit >= page.total}
                    onClick={() => setSkip(skip + 12)}
                  >
                    Next
                  </button>
                </div>
              </>
            )
          )}
        </div>
      </div>
    </main>
  );
}

export function CampaignReport({ id, go }: { id: string; go: Navigate }) {
  const [campaign, setCampaign] = useState<CampaignDetail | null>(null);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setCampaign(null);
    setError("");
    getCampaign(id, controller.signal)
      .then((result) => {
        if (!controller.signal.aborted) setCampaign(result);
      })
      .catch((failure) => {
        if (!controller.signal.aborted) setError(message(failure));
      });
    return () => controller.abort();
  }, [id, retry]);
  const download = () => {
    if (!campaign) return;
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(campaign, null, 2)], {
        type: "application/json",
      }),
    );
    const link = document.createElement("a");
    link.href = url;
    link.download = `panataanph-${campaign.public_id}.json`;
    link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  return (
    <main className="container py-10 sm:py-14">
      <button className="button button-ghost mb-5" onClick={() => go("/campaigns")}>
        ← Back to Directory
      </button>
      {error ? (
        <>
          <Notice error>{error}</Notice>
          <button
            className="button button-secondary mt-4"
            onClick={() => setRetry((value) => value + 1)}
          >
            Try Again
          </button>
        </>
      ) : !campaign ? (
        <Notice>Loading campaign…</Notice>
      ) : (
        <>
          <span className="badge badge-green">
            <BadgeCheck size={15} /> Verified by human review
          </span>
          <h1 className="mt-5 text-3xl font-extrabold sm:text-4xl">{campaign.title}</h1>
          <p className="mt-3 text-muted">
            {campaign.organization_name || campaign.organizer_name} · {campaign.location} · Updated{" "}
            {date(campaign.updated_at)}
          </p>
          <div className="mt-8 grid gap-5 lg:grid-cols-[.72fr_1.28fr]">
            <section className="report-card flex flex-col items-center text-center">
              <div
                className="score-ring"
                style={{
                  background: `conic-gradient(var(--color-brand) 0 ${campaign.verification_score ?? 0}%, #f4f4f5 ${campaign.verification_score ?? 0}% 100%)`,
                }}
              >
                <div className="score-inner">
                  <strong>{campaign.verification_score ?? "—"}</strong>
                  <span>{campaign.verification_score === null ? "Not scored" : "/ 100"}</span>
                </div>
              </div>
              <h2 className="mt-5 text-xl font-extrabold">Evidence Score</h2>
              <p className="mt-2 text-sm leading-6 text-muted">
                Evidence completeness, calculated using fixed rules. Standard publication threshold:
                {" "}{campaign.minimum_score}/100, with human approval. Score does not guarantee legitimacy.
              </p>
              {campaign.threshold_overridden && (
                <p className="mt-4 rounded-xl bg-amber-50 p-3 text-sm font-semibold text-amber-800">
                  Approved with a documented administrator score exception.
                </p>
              )}
            </section>
            <section className="report-card">
              <h2 className="text-xl font-extrabold">Score Breakdown</h2>
              {campaign.findings.length ? (
                <div className="mt-6 space-y-5">
                  {campaign.findings.map((finding) => (
                    <div key={finding.criterion}>
                      <div className="mb-2 flex justify-between gap-3 text-sm">
                        <span className="font-semibold capitalize">{finding.criterion}</span>
                        <span className="shrink-0">
                          {finding.points_awarded} / {finding.points_possible}
                        </span>
                      </div>
                      <div className="h-2 overflow-hidden rounded-full bg-zinc-100">
                        <div
                          className="h-full bg-brand"
                          style={{
                            width: `${
                              finding.points_possible > 0
                                ? Math.max(
                                    0,
                                    Math.min(
                                      100,
                                      (finding.points_awarded / finding.points_possible) * 100,
                                    ),
                                  )
                                : 0
                            }%`,
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="mt-4 text-sm text-muted">No criterion breakdown is available.</p>
              )}
            </section>
          </div>
          <section className="report-card mt-5">
            <h2 className="text-xl font-extrabold">Campaign Information</h2>
            <p className="mt-4 whitespace-pre-wrap leading-7 text-muted">{campaign.description}</p>
            <dl className="mt-5 divide-y divide-line">
              {[
                ["Purpose", campaign.purpose],
                ["Beneficiaries", campaign.beneficiaries || "Not provided"],
                ["Target", money(campaign.target_amount)],
              ].map(([label, value]) => (
                <div key={label} className="grid gap-2 py-4 sm:grid-cols-[12rem_1fr]">
                  <dt className="text-sm text-muted">{label}</dt>
                  <dd className="whitespace-pre-wrap break-words text-sm font-semibold">{value}</dd>
                </div>
              ))}
            </dl>
          </section>
          <section className="report-card mt-5" aria-labelledby="donation-heading">
            <h2 id="donation-heading" className="text-xl font-extrabold">Donation Methods</h2>
            <p className="mt-2 text-sm leading-6 text-muted">
              Organizer-provided payment details reviewed with this campaign. Confirm the account
              name and recipient in your payment app before sending funds.
            </p>
            {campaign.payment_method || campaign.payment_details ? (
              <dl className="mt-5 space-y-4">
                {campaign.payment_method && <div><dt className="text-sm text-muted">Payment method</dt><dd className="mt-1 whitespace-pre-wrap break-words font-semibold">{campaign.payment_method}</dd></div>}
                {campaign.payment_details && <div><dt className="text-sm text-muted">Account details</dt><dd className="mt-1 whitespace-pre-wrap break-words font-semibold">{campaign.payment_details}</dd></div>}
              </dl>
            ) : !campaign.qr_codes.length && (
              <p className="mt-5 rounded-xl bg-canvas p-4 text-sm text-muted">
                No donation methods have been published for this campaign.
              </p>
            )}
            {campaign.qr_codes.length ? (
              <div className="mt-6 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
                {campaign.qr_codes.map((qr) => (
                  <figure key={qr.public_id} className="min-w-0 rounded-2xl border border-line p-4">
                    <img
                      src={qr.image_url}
                      alt={`Donation QR for ${qr.label}`}
                      className="mx-auto aspect-square w-full max-w-64 object-contain"
                      loading="lazy"
                    />
                    <figcaption className="mt-3 break-words text-center text-sm font-bold">{qr.label}</figcaption>
                  </figure>
                ))}
              </div>
            ) : (
              <p className="mt-4 text-sm text-muted">No donation QR image has been provided.</p>
            )}
          </section>
          <section className="report-card mt-5" aria-labelledby="transparency-heading">
            <h2 id="transparency-heading" className="text-xl font-extrabold">Fund Transparency</h2>
            <p className="mt-2 text-sm leading-6 text-muted">
              Organizer-reported funds, reviewed by administrators before publication. PanataanPH
              does not collect payments or independently confirm bank balances.
            </p>
            <dl className="mt-6 grid gap-4 sm:grid-cols-3">
              {[
                ["Reported received", campaign.transparency.received_centavos],
                ["Reported spent", campaign.transparency.spent_centavos],
                ["Reported balance", campaign.transparency.balance_centavos],
              ].map(([label, cents]) => (
                <div key={label} className="min-w-0 rounded-2xl bg-canvas p-4">
                  <dt className="text-sm text-muted">{label}</dt>
                  <dd className="mt-2 break-words text-xl font-extrabold">{money(Number(cents) / 100)}</dd>
                </div>
              ))}
            </dl>
            <div className="mt-5">
              <p className="text-sm font-semibold">
                {money(campaign.transparency.received_centavos / 100)} reported of {money(campaign.target_amount)} target
              </p>
              <progress
                value={campaign.transparency.received_centavos / 100}
                max={campaign.target_amount || 1}
                aria-label="Reported funds received toward target"
                className="mt-3 h-2 w-full accent-brand"
              />
            </div>
            {campaign.transparency.entries.length ? (
              <ul className="mt-6 divide-y divide-line">
                {campaign.transparency.entries.map((entry) => (
                  <li key={entry.public_id} className="flex flex-col justify-between gap-3 py-4 sm:flex-row">
                    <div className="min-w-0">
                      <p className="whitespace-pre-wrap break-words text-sm font-semibold">{entry.description}</p>
                      <p className="mt-1 text-xs text-muted">{date(entry.occurred_on)} · Admin-reviewed report</p>
                    </div>
                    <p className={`shrink-0 text-sm font-bold ${entry.kind === "received" ? "text-success" : "text-ink"}`}>
                      {entry.kind === "received" ? "Received" : "Spent"} {money(entry.amount_centavos / 100)}
                    </p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-5 rounded-xl bg-canvas p-4 text-sm leading-6 text-muted">
                No approved fund reports yet. Zero totals mean no published reports; they do not
                confirm the campaign's actual receipts or balance.
              </p>
            )}
          </section>
          <p className="mt-5 text-sm text-muted">
            Original supporting documents and private reviewer notes are confidential.
          </p>
          <button className="button button-secondary mt-6" onClick={download}>
            <Download size={17} />
            Download Public Report
          </button>
        </>
      )}
    </main>
  );
}
