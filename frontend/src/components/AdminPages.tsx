import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { BadgeCheck, Download, LockKeyhole, ShieldCheck } from "lucide-react";
import {
  getAdminDocument,
  getPublicConfig,
  listAdminAccounts,
  listAdminCampaigns,
  loginAccount,
  recordFundTransaction,
  registerAccount,
  reviewCampaign,
  verifyAccount,
} from "../lib/api";
import type { Account, AdminAccount, AdminCampaign } from "../lib/api";

type Navigate = (path: string) => void;
type AuthMode = "login" | "register";
const errorMessage = (error: unknown) =>
  error instanceof Error ? error.message : "Unable to connect to the API. Please try again.";
const currency = (amount: number) =>
  new Intl.NumberFormat("en-PH", { style: "currency", currency: "PHP" }).format(amount);

export function AuthPage({
  go,
  onAuthenticated,
  initialMode,
}: {
  go: Navigate;
  onAuthenticated: (account: Account) => void;
  initialMode: AuthMode;
}) {
  const [mode, setMode] = useState<AuthMode>(initialMode);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => setMode(initialMode), [initialMode]);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (busy) return;
    const fields = Object.fromEntries(new FormData(event.currentTarget).entries());
    setBusy(true);
    setError("");
    try {
      const account =
        mode === "login"
          ? await loginAccount(String(fields.email), String(fields.password))
          : await registerAccount({
              display_name: String(fields.display_name),
              email: String(fields.email),
              password: String(fields.password),
              organization_name: String(fields.organization_name || ""),
              organization_registration_number: String(fields.organization_registration_number || ""),
              phone: String(fields.phone || ""),
            });
      onAuthenticated(account);
      const requested = new URLSearchParams(window.location.search).get("next");
      const next = requested?.startsWith("/") && !requested.startsWith("//")
        ? requested
        : account.role === "admin" || account.role === "lgu"
          ? "/admin"
          : "/";
      go(next);
    } catch (failure) {
      setError(errorMessage(failure));
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="min-h-[calc(100vh-5rem)] bg-canvas px-4 py-10 sm:py-16">
      <section className="report-card mx-auto max-w-xl p-5 sm:p-8">
        <div className="grid size-12 place-items-center rounded-2xl bg-soft-red text-brand">
          {mode === "login" ? <LockKeyhole size={22} /> : <ShieldCheck size={22} />}
        </div>
        <p className="eyebrow mt-6">PanataanPH account</p>
        <h1 className="mt-2 text-3xl font-extrabold tracking-tight">
          {mode === "login" ? "Welcome back" : "Create an organizer account"}
        </h1>
        <p className="mt-3 text-sm leading-6 text-muted">
          {mode === "login"
            ? "Sign in to submit and manage fundraiser campaigns. LGU and administrator accounts are provisioned by the platform administrator."
            : "Use an account to submit a fundraiser. Account details can be reviewed by an authorized LGU or administrator."}
        </p>
        <form className="mt-7 space-y-4" onSubmit={submit}>
          {mode === "register" && (
            <>
              <label className="block text-sm font-semibold">
                Full name *
                <input
                  name="display_name"
                  autoComplete="name"
                  required
                  maxLength={255}
                  className="mt-2 w-full rounded-xl border border-line bg-white p-3 outline-none focus:border-brand"
                />
              </label>
              <label className="block text-sm font-semibold">
                Organization name (optional)
                <input
                  name="organization_name"
                  maxLength={255}
                  className="mt-2 w-full rounded-xl border border-line bg-white p-3 outline-none focus:border-brand"
                />
              </label>
              <div className="grid gap-4 sm:grid-cols-2">
                <label className="block text-sm font-semibold">
                  Registration number (optional)
                  <input
                    name="organization_registration_number"
                    maxLength={100}
                    className="mt-2 w-full min-w-0 rounded-xl border border-line bg-white p-3 outline-none focus:border-brand"
                  />
                </label>
                <label className="block text-sm font-semibold">
                  Phone (optional)
                  <input
                    name="phone"
                    type="tel"
                    maxLength={50}
                    autoComplete="tel"
                    className="mt-2 w-full min-w-0 rounded-xl border border-line bg-white p-3 outline-none focus:border-brand"
                  />
                </label>
              </div>
            </>
          )}
          <label className="block text-sm font-semibold">
            Email
            <input
              name="email"
              type="email"
              autoComplete="email"
              required
              maxLength={255}
              className="mt-2 w-full rounded-xl border border-line bg-white p-3 outline-none focus:border-brand"
            />
          </label>
          <label className="block text-sm font-semibold">
            Password {mode === "register" && "(at least 10 characters)"}
            <input
              name="password"
              type="password"
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              required
              minLength={mode === "register" ? 10 : 1}
              maxLength={128}
              className="mt-2 w-full rounded-xl border border-line bg-white p-3 outline-none focus:border-brand"
            />
          </label>
          {error && (
            <p role="alert" className="rounded-xl bg-red-50 p-4 text-sm text-brand">
              {error}
            </p>
          )}
          <button type="submit" disabled={busy} className="button button-primary w-full">
            {busy ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}
          </button>
        </form>
        <p className="mt-6 text-center text-sm text-muted">
          {mode === "login" ? "New to PanataanPH?" : "Already have an account?"}{" "}
          <button
            className="font-bold text-brand hover:underline"
            onClick={() => {
              setError("");
              setMode(mode === "login" ? "register" : "login");
            }}
          >
            {mode === "login" ? "Create an account" : "Sign in"}
          </button>
        </p>
        {mode === "register" && (
          <p className="mt-5 text-center text-xs leading-5 text-muted">
            New accounts are organizers by default. Admin and LGU access is granted separately and
            cannot be selected during sign-up.
          </p>
        )}
      </section>
    </main>
  );
}

function breakdown(campaign: AdminCampaign) {
  if (!campaign.score_breakdown) return [];
  try {
    return JSON.parse(campaign.score_breakdown) as {
      criterion: string;
      points_awarded: number;
      points_possible: number;
      details: string;
    }[];
  } catch {
    return [];
  }
}

export function AdminDashboard({
  account,
  go,
}: {
  account: Account | null;
  go: Navigate;
}) {
  const [view, setView] = useState<"campaigns" | "accounts">("campaigns");
  const [campaignStatus, setCampaignStatus] = useState("pending");
  const [accountStatus, setAccountStatus] = useState("pending");
  const [campaigns, setCampaigns] = useState<AdminCampaign[]>([]);
  const [accounts, setAccounts] = useState<AdminAccount[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [selectedAccountId, setSelectedAccountId] = useState<number | null>(null);
  const [minimumScore, setMinimumScore] = useState(70);
  const [reason, setReason] = useState("");
  const [ledgerKind, setLedgerKind] = useState<"received" | "spent">("received");
  const [ledgerError, setLedgerError] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [reload, setReload] = useState(0);
  const campaign = campaigns.find((item) => item.public_id === selectedId) ?? null;
  const organizer = accounts.find((item) => item.id === selectedAccountId) ?? null;

  useEffect(() => {
    getPublicConfig().then((config) => setMinimumScore(config.minimum_verification_score)).catch(() => {});
  }, []);

  useEffect(() => {
    let active = true;
    setError("");
    listAdminCampaigns(campaignStatus)
      .then((items) => {
        if (active) setCampaigns(items);
      })
      .catch((failure) => {
        if (active) setError(errorMessage(failure));
      });
    return () => {
      active = false;
    };
  }, [campaignStatus, reload]);

  useEffect(() => {
    let active = true;
    setError("");
    listAdminAccounts(accountStatus)
      .then((items) => {
        if (active) setAccounts(items);
      })
      .catch((failure) => {
        if (active) setError(errorMessage(failure));
      });
    return () => {
      active = false;
    };
  }, [accountStatus, reload]);

  useEffect(() => {
    if (!campaigns.some((item) => item.public_id === selectedId)) {
      setSelectedId(campaigns[0]?.public_id ?? "");
      setReason("");
    }
  }, [campaigns, selectedId]);

  useEffect(() => {
    if (!accounts.some((item) => item.id === selectedAccountId)) {
      setSelectedAccountId(accounts[0]?.id ?? null);
      setReason("");
    }
  }, [accounts, selectedAccountId]);

  if (!account || !["admin", "lgu"].includes(account.role)) {
    return (
      <main className="container py-14">
        <section className="report-card mx-auto max-w-2xl text-center">
          <div className="mx-auto grid size-12 place-items-center rounded-2xl bg-soft-red text-brand">
            <LockKeyhole size={22} />
          </div>
          <h1 className="mt-5 text-3xl font-extrabold">Reviewer access only</h1>
          <p className="mt-3 text-muted">
            The review workspace is restricted to provisioned LGU and administrator accounts.
          </p>
          <button className="button button-primary mt-6" onClick={() => go("/login?next=%2Fadmin")}>
            Sign in as a reviewer
          </button>
        </section>
      </main>
    );
  }

  const decideCampaign = async (
    decision: "verified" | "rejected" | "needs_information" | "under_review",
  ) => {
    if (!campaign || busy) return;
    if (["rejected", "needs_information"].includes(decision) && !reason.trim()) {
      setError("Add a reason before rejecting a campaign or requesting information.");
      return;
    }
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await reviewCampaign(campaign.public_id, decision, reason.trim());
      setNotice(`Campaign marked ${decision.replace(/_/g, " ")}.`);
      setReason("");
      setReload((value) => value + 1);
    } catch (failure) {
      setError(errorMessage(failure));
    } finally {
      setBusy(false);
    }
  };

  const decideAccount = async (status: "verified" | "needs_information" | "rejected") => {
    if (!organizer || busy) return;
    if (["needs_information", "rejected"].includes(status) && !reason.trim()) {
      setError("Add a reason before requesting information or rejecting an account.");
      return;
    }
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await verifyAccount(organizer.id, status, reason.trim());
      setNotice(`Organizer account marked ${status.replace(/_/g, " ")}.`);
      setReason("");
      setReload((value) => value + 1);
    } catch (failure) {
      setError(errorMessage(failure));
    } finally {
      setBusy(false);
    }
  };

  const download = async (doc: AdminCampaign["documents"][number]) => {
    if (!campaign) return;
    try {
      const blob = await getAdminDocument(campaign.public_id, doc.public_id);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = doc.original_filename;
      link.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (failure) {
      setError(errorMessage(failure));
    }
  };

  const recordLedger = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!campaign || busy) return;
    const form = event.currentTarget;
    const fields = Object.fromEntries(new FormData(form).entries());
    setBusy(true);
    setLedgerError("");
    try {
      await recordFundTransaction(campaign.public_id, {
        kind: ledgerKind,
        amount: Number(fields.amount),
        description: String(fields.description),
        reference: String(fields.reference || "") || undefined,
      });
      form.reset();
      setNotice("Fund ledger entry recorded and will appear on the public campaign page.");
    } catch (failure) {
      setLedgerError(errorMessage(failure));
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="min-h-screen bg-canvas">
      <header className="border-b border-line bg-white">
        <div className="container py-8 sm:py-10">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <span className="badge badge-red">
                <ShieldCheck size={14} /> Restricted workspace
              </span>
              <h1 className="mt-4 text-3xl font-extrabold sm:text-4xl">Admin review</h1>
              <p className="mt-2 text-sm text-muted">
                Signed in as {account.display_name} · {account.role.toUpperCase()}
              </p>
            </div>
            <button className="button button-secondary self-start" onClick={() => go("/")}>
              Back to directory
            </button>
          </div>
          <div className="mt-6 flex flex-wrap gap-2" role="tablist" aria-label="Review sections">
            {[
              ["campaigns", "Campaign reviews"],
              ["accounts", "Organizer accounts"],
            ].map(([value, label]) => (
              <button
                key={value}
                role="tab"
                aria-selected={view === value}
                className={`button ${view === value ? "button-primary" : "button-secondary"}`}
                onClick={() => {
                  setView(value as "campaigns" | "accounts");
                  setError("");
                }}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      </header>

      <div className="container py-7 sm:py-10">
        {error && <p role="alert" className="mb-5 rounded-xl bg-red-50 p-4 text-sm text-brand">{error}</p>}
        {notice && <p role="status" className="mb-5 rounded-xl bg-green-50 p-4 text-sm text-green-800">{notice}</p>}
        {view === "campaigns" ? (
          <>
            <div className="mb-5 flex flex-wrap gap-2" aria-label="Campaign review status">
              {[
                ["pending", "Pending"],
                ["under_review", "Under review"],
                ["needs_information", "Needs information"],
                ["verified", "Verified"],
                ["rejected", "Rejected"],
              ].map(([value, label]) => (
                <button
                  key={value}
                  className={`filter-button ${campaignStatus === value ? "border-brand text-brand" : ""}`}
                  onClick={() => setCampaignStatus(value)}
                >
                  {label}
                </button>
              ))}
            </div>
            <div className="grid min-w-0 gap-5 xl:grid-cols-[minmax(17rem,.72fr)_minmax(0,1.28fr)]">
              <section className="report-card min-w-0 p-4 sm:p-5">
                <h2 className="text-lg font-extrabold">Campaign queue</h2>
                {campaigns.length ? (
                  <ul className="mt-4 space-y-2">
                    {campaigns.map((item) => (
                      <li key={item.public_id}>
                        <button
                          className={`w-full rounded-xl border p-3 text-left ${selectedId === item.public_id ? "border-brand bg-soft-red" : "border-line hover:bg-canvas"}`}
                          onClick={() => {
                            setSelectedId(item.public_id);
                            setReason("");
                          }}
                        >
                          <span className="block break-words font-bold">{item.title}</span>
                          <span className="mt-1 block break-words text-xs text-muted">
                            {item.organizer_name} · {item.verification_score ?? "Not scored"} points
                          </span>
                        </button>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-4 rounded-xl bg-canvas p-4 text-sm text-muted">
                    No campaigns in this status.
                  </p>
                )}
              </section>
              <section className="min-w-0 space-y-5">
                {campaign ? (
                  <>
                    <article className="report-card min-w-0">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="min-w-0">
                          <span className="badge badge-amber">{campaign.status.replace(/_/g, " ")}</span>
                          <h2 className="mt-3 break-words text-2xl font-extrabold">{campaign.title}</h2>
                          <p className="mt-2 break-words text-sm text-muted">
                            {campaign.organization_name || campaign.organizer_name} · {campaign.location}
                          </p>
                        </div>
                        <div className="rounded-xl bg-canvas p-3 text-center">
                          <p className="text-xs font-semibold text-muted">Evidence score</p>
                          <p className="mt-1 text-2xl font-extrabold">
                            {campaign.verification_score ?? "—"}
                            <span className="text-sm font-semibold text-muted"> / 100</span>
                          </p>
                          <p className="mt-1 text-xs text-muted">Minimum {minimumScore}</p>
                        </div>
                      </div>
                      <div className="mt-5 grid gap-4 sm:grid-cols-2">
                        <div className="rounded-xl bg-canvas p-4">
                          <h3 className="font-bold">Organizer contact</h3>
                          <p className="mt-2 break-words text-sm text-muted">{campaign.organizer_name}</p>
                          <p className="break-all text-sm text-muted">{campaign.organizer_email || "No email"}</p>
                          <p className="text-sm text-muted">{campaign.organizer_phone || "No phone"}</p>
                          {campaign.organization_registration_number && (
                            <p className="mt-2 break-all text-xs text-muted">
                              Registration: {campaign.organization_registration_number}
                            </p>
                          )}
                        </div>
                        <div className="rounded-xl bg-canvas p-4">
                          <h3 className="font-bold">Campaign summary</h3>
                          <p className="mt-2 text-sm text-muted">Purpose: {campaign.purpose}</p>
                          <p className="mt-1 text-sm text-muted">Target: {currency(campaign.target_amount)}</p>
                          <p className="mt-1 text-sm text-muted">Beneficiaries: {campaign.beneficiaries || "Not provided"}</p>
                        </div>
                      </div>
                      <p className="mt-4 whitespace-pre-wrap break-words text-sm leading-6 text-muted">
                        {campaign.description}
                      </p>
                      <h3 className="mt-6 font-bold">Evidence and score details</h3>
                      {breakdown(campaign).length ? (
                        <ul className="mt-3 space-y-3">
                          {breakdown(campaign).map((item) => (
                            <li key={item.criterion} className="rounded-xl border border-line p-3">
                              <div className="flex flex-wrap justify-between gap-2 text-sm">
                                <span className="font-semibold">{item.criterion.replace(/_/g, " ")}</span>
                                <span>{item.points_awarded} / {item.points_possible}</span>
                              </div>
                              <p className="mt-1 text-xs leading-5 text-muted">{item.details}</p>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p className="mt-2 text-sm text-muted">No score breakdown is available.</p>
                      )}
                      <h3 className="mt-6 font-bold">Private supporting documents</h3>
                      {campaign.documents.length ? (
                        <ul className="mt-3 grid gap-2 sm:grid-cols-2">
                          {campaign.documents.map((doc) => (
                            <li key={doc.public_id} className="flex min-w-0 items-center gap-2 rounded-xl bg-canvas p-3">
                              <span className="min-w-0 flex-1 truncate text-sm">{doc.original_filename}</span>
                              <button
                                className="icon-button"
                                aria-label={`Download ${doc.original_filename}`}
                                title={`Download ${doc.original_filename}`}
                                onClick={() => download(doc)}
                              >
                                <Download size={17} />
                              </button>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p className="mt-2 text-sm text-muted">No private documents are attached.</p>
                      )}
                      <label className="mt-6 block text-sm font-semibold">
                        Review notes {campaign.status === "pending" && <span className="font-normal text-muted">(required to reject or request information)</span>}
                        <textarea
                          value={reason}
                          onChange={(event) => setReason(event.target.value)}
                          rows={3}
                          maxLength={5000}
                          className="mt-2 w-full rounded-xl border border-line p-3 text-sm outline-none focus:border-brand"
                        />
                      </label>
                      <div className="mt-4 flex flex-wrap gap-2">
                        <button
                          disabled={busy || (campaign.verification_score ?? -1) < minimumScore}
                          className="button button-primary"
                          onClick={() => decideCampaign("verified")}
                          title={`Campaign needs at least ${minimumScore} points to be published`}
                        >
                          <BadgeCheck size={16} /> Verify and publish
                        </button>
                        <button disabled={busy} className="button button-secondary" onClick={() => decideCampaign("under_review")}>
                          Keep under review
                        </button>
                        <button disabled={busy} className="button button-secondary" onClick={() => decideCampaign("needs_information")}>
                          Request information
                        </button>
                        <button disabled={busy} className="button button-secondary" onClick={() => decideCampaign("rejected")}>
                          Reject
                        </button>
                      </div>
                      {(campaign.verification_score ?? -1) < minimumScore && (
                        <p className="mt-3 text-sm text-amber-800">
                          This campaign cannot be published until its evidence completeness score reaches {minimumScore}.
                        </p>
                      )}
                    </article>
                    {campaign.status === "verified" && campaign.verification_score !== null && campaign.verification_score >= minimumScore && (
                      <section className="report-card">
                        <h2 className="text-lg font-extrabold">Record a public fund transaction</h2>
                        <p className="mt-2 text-sm leading-6 text-muted">
                          Record confirmed funds received or campaign spending. This entry will be visible in the campaign transparency ledger.
                        </p>
                        <form className="mt-4 grid gap-4 sm:grid-cols-2" onSubmit={recordLedger}>
                          <label className="text-sm font-semibold">
                            Transaction type
                            <select
                              value={ledgerKind}
                              onChange={(event) => setLedgerKind(event.target.value as "received" | "spent")}
                              className="mt-2 w-full rounded-xl border border-line bg-white p-3"
                            >
                              <option value="received">Funds received</option>
                              <option value="spent">Funds spent</option>
                            </select>
                          </label>
                          <label className="text-sm font-semibold">
                            Amount (PHP)
                            <input name="amount" type="number" min="0.01" step="0.01" required className="mt-2 w-full rounded-xl border border-line p-3" />
                          </label>
                          <label className="text-sm font-semibold sm:col-span-2">
                            Description
                            <input name="description" required maxLength={2000} className="mt-2 w-full rounded-xl border border-line p-3" />
                          </label>
                          <label className="text-sm font-semibold sm:col-span-2">
                            Reference (optional)
                            <input name="reference" maxLength={255} className="mt-2 w-full rounded-xl border border-line p-3" />
                          </label>
                          {ledgerError && <p role="alert" className="text-sm text-brand sm:col-span-2">{ledgerError}</p>}
                          <button type="submit" disabled={busy} className="button button-primary sm:col-span-2">
                            Record transaction
                          </button>
                        </form>
                      </section>
                    )}
                  </>
                ) : (
                  <div className="report-card"><p className="text-sm text-muted">Select a campaign to review.</p></div>
                )}
              </section>
            </div>
          </>
        ) : (
          <>
            <div className="mb-5 flex flex-wrap gap-2" aria-label="Account review status">
              {[
                ["pending", "Pending"],
                ["verified", "Verified"],
                ["needs_information", "Needs information"],
                ["rejected", "Rejected"],
              ].map(([value, label]) => (
                <button
                  key={value}
                  className={`filter-button ${accountStatus === value ? "border-brand text-brand" : ""}`}
                  onClick={() => setAccountStatus(value)}
                >
                  {label}
                </button>
              ))}
            </div>
            <div className="grid min-w-0 gap-5 lg:grid-cols-[minmax(17rem,.72fr)_minmax(0,1.28fr)]">
              <section className="report-card min-w-0 p-4 sm:p-5">
                <h2 className="text-lg font-extrabold">Organizer accounts</h2>
                {accounts.length ? (
                  <ul className="mt-4 space-y-2">
                    {accounts.map((item) => (
                      <li key={item.id}>
                        <button
                          className={`w-full rounded-xl border p-3 text-left ${selectedAccountId === item.id ? "border-brand bg-soft-red" : "border-line hover:bg-canvas"}`}
                          onClick={() => {
                            setSelectedAccountId(item.id);
                            setReason("");
                          }}
                        >
                          <span className="block font-bold">{item.display_name}</span>
                          <span className="mt-1 block break-all text-xs text-muted">{item.email}</span>
                        </button>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-4 rounded-xl bg-canvas p-4 text-sm text-muted">No organizer accounts in this status.</p>
                )}
              </section>
              {organizer ? (
                <section className="report-card min-w-0">
                  <span className="badge badge-amber">{organizer.verification_status.replace(/_/g, " ")}</span>
                  <h2 className="mt-4 break-words text-2xl font-extrabold">{organizer.display_name}</h2>
                  <dl className="mt-5 divide-y divide-line">
                    {[
                      ["Email", organizer.email],
                      ["Organization", organizer.organization_name || "Not provided"],
                      ["Registration number", organizer.organization_registration_number || "Not provided"],
                      ["Phone", organizer.phone || "Not provided"],
                      ["Registered", new Date(organizer.created_at).toLocaleDateString("en-PH")],
                    ].map(([label, value]) => (
                      <div key={label} className="grid gap-1 py-3 sm:grid-cols-[12rem_1fr]">
                        <dt className="text-sm text-muted">{label}</dt>
                        <dd className="break-words text-sm font-semibold">{value}</dd>
                      </div>
                    ))}
                  </dl>
                  <label className="mt-5 block text-sm font-semibold">
                    Account review notes
                    <textarea value={reason} onChange={(event) => setReason(event.target.value)} rows={3} maxLength={5000} className="mt-2 w-full rounded-xl border border-line p-3 text-sm outline-none focus:border-brand" />
                  </label>
                  <div className="mt-4 flex flex-wrap gap-2">
                    <button disabled={busy} className="button button-primary" onClick={() => decideAccount("verified")}>
                      <BadgeCheck size={16} /> Verify account
                    </button>
                    <button disabled={busy} className="button button-secondary" onClick={() => decideAccount("needs_information")}>
                      Request information
                    </button>
                    <button disabled={busy} className="button button-secondary" onClick={() => decideAccount("rejected")}>
                      Reject account
                    </button>
                  </div>
                  <p className="mt-4 text-xs leading-5 text-muted">
                    Account verification records an administrator or LGU reviewer decision. It does not automatically verify individual fundraiser claims.
                  </p>
                </section>
              ) : (
                <section className="report-card"><p className="text-sm text-muted">Select an organizer account to review.</p></section>
              )}
            </div>
          </>
        )}
      </div>
    </main>
  );
}
