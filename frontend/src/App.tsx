import {
  ArrowRight,
  CheckCircle2,
  CircleAlert,
  FileCheck2,
  Menu,
  Search,
  ShieldCheck,
  Sparkles,
  WifiOff,
  X,
} from "lucide-react";

import { type ReactNode, useEffect, useState } from "react";

import {
  CampaignDirectory,
  CampaignReport,
  SubmissionPage,
  SubmissionReport,
} from "./components/IntegratedPages";

import type { Submission } from "./lib/api";

type Route = string;

type Tone = "red" | "green" | "amber" | "neutral";

const routeFromPath = (): Route => {
  const path = window.location.pathname;

  return path.startsWith("/campaigns/") ||
    ["/", "/verify", "/verify/processing", "/verify/report", "/campaigns"].includes(path)
    ? (path as Route)
    : "/";
};

function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex items-center gap-2.5">
      <div className="grid size-9 place-items-center rounded-xl bg-brand text-white shadow-brand">
        <ShieldCheck size={20} strokeWidth={2.4} />
      </div>
      {!compact && (
        <span className="text-lg font-extrabold tracking-tight text-ink">
          Panataan<span className="text-brand">PH</span>
        </span>
      )}
    </div>
  );
}

function Badge({
  children,

  tone = "neutral",
}: {
  children: ReactNode;

  tone?: Tone;
}) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}

function Button({
  children,

  variant = "primary",

  className = "",

  disabled,

  onClick,

  type = "button",
}: {
  children: ReactNode;

  variant?: "primary" | "secondary" | "ghost" | "outline";

  className?: string;

  disabled?: boolean;

  onClick?: () => void;

  type?: "button" | "submit";
}) {
  return (
    <button
      type={type}
      disabled={disabled}
      onClick={onClick}
      className={`button button-${variant} ${className}`}
    >
      {children}
    </button>
  );
}

function IconButton({
  label,

  children,

  onClick,
}: {
  label: string;

  children: ReactNode;

  onClick?: () => void;
}) {
  return (
    <button className="icon-button" aria-label={label} title={label} onClick={onClick}>
      {children}
    </button>
  );
}

function Navbar({ route, go }: { route: Route; go: (route: Route) => void }) {
  const [open, setOpen] = useState(false);
  const navigate = (path: Route) => {
    setOpen(false);
    go(path);
  };

  const items: [string, Route][] = [
    ["Home", "/"],

    ["Submit a Fundraiser", "/verify"],

    ["Campaigns", "/campaigns"],
  ];

  return (
    <header className="sticky top-0 z-40 border-b border-line/80 bg-white/90 backdrop-blur-xl">
      <div className="container flex h-18 items-center justify-between">
        <button onClick={() => go("/")} aria-label="PanataanPH home">
          <Brand />
        </button>
        <nav className="hidden items-center gap-1 lg:flex" aria-label="Primary navigation">
          {items.map(([label, path]) => (
            <button
              key={path}
              onClick={() => go(path)}
              className={`nav-link ${route === path ? "nav-link-active" : ""}`}
            >
              {label}
            </button>
          ))}
          <button onClick={() => go("/#how")} className="nav-link">
            How It Works
          </button>
          <button onClick={() => go("/#about")} className="nav-link">
            About
          </button>
        </nav>
        <div className="hidden lg:block">
          <Button variant="outline" onClick={() => go("/verify")}>
            Submit a Fundraiser <ArrowRight size={16} />
          </Button>
        </div>
        <div className="lg:hidden">
          <IconButton label="Open menu" onClick={() => setOpen(!open)}>
            {open ? <X size={22} /> : <Menu size={22} />}
          </IconButton>
        </div>
      </div>
      {open && (
        <nav className="border-t border-line bg-white px-5 py-4 lg:hidden">
          <div className="mx-auto flex max-w-lg flex-col gap-1">
            {items.map(([label, path]) => (
              <button
                key={path}
                className="mobile-nav-link"
                onClick={() => {
                  go(path);

                  setOpen(false);
                }}
              >
                {label}
              </button>
            ))}
            <button className="mobile-nav-link" onClick={() => navigate("/#how")}>
              How It Works
            </button>
            <button className="mobile-nav-link" onClick={() => navigate("/#about")}>
              About
            </button>
            <Button className="mt-2 w-full" onClick={() => navigate("/verify")}>
              Submit a Fundraiser
            </Button>
          </div>
        </nav>
      )}
    </header>
  );
}

function Footer({ go }: { go: (route: Route) => void }) {
  return (
    <footer className="border-t border-line bg-white">
      <div className="container grid gap-9 py-12 md:grid-cols-[1.4fr_1fr] md:items-end">
        <div>
          <Brand />
          <p className="mt-4 max-w-sm text-sm leading-6 text-muted">
            Helping Filipinos verify before they give. Private evidence storage and human-led
            review.
          </p>
        </div>
        <div className="flex flex-wrap gap-x-7 gap-y-3 text-sm font-medium text-muted md:justify-end">
          <button className="footer-link" onClick={() => go("/#privacy")}>
            Privacy
          </button>
          <button className="footer-link" onClick={() => go("/#how")}>
            How It Works
          </button>
          <button className="footer-link" onClick={() => go("/#about")}>
            About
          </button>
          <button className="footer-link" onClick={() => go("/verify")}>
            Submit a Fundraiser
          </button>
        </div>
      </div>
    </footer>
  );
}

function FeatureCard({
  icon,

  title,

  copy,
}: {
  icon: ReactNode;

  title: string;

  copy: string;
}) {
  return (
    <article className="feature-card">
      <div className="feature-icon">{icon}</div>
      <h3 className="mt-5 text-lg font-bold text-ink">{title}</h3>
      <p className="mt-2 text-sm leading-6 text-muted">{copy}</p>
    </article>
  );
}

function HeroMockup() {
  const rows = [
    ["Fundraiser post", "Organization detected", "check"],

    ["DSWD permit", "Permit number detected", "check"],

    ["Payment account", "Recipient needs verification", "warn"],
  ];

  return (
    <div className="relative mx-auto max-w-lg">
      <div className="absolute -left-12 -top-10 size-44 rounded-full bg-brand/8 blur-2xl" />
      <div className="absolute -bottom-10 -right-8 size-52 rounded-full bg-amber-200/30 blur-3xl" />
      <div className="relative overflow-hidden rounded-[1.75rem] border border-line bg-white p-3 shadow-2xl shadow-zinc-900/10">
        <div className="rounded-3xl bg-canvas p-5 sm:p-7">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.16em] text-brand">
                Illustrative example
              </p>
              <h3 className="mt-1 text-lg font-bold text-ink">Typhoon Relief Drive</h3>
            </div>
            <Badge tone="green">
              <span className="status-dot" /> Local
            </Badge>
          </div>
          <div className="mt-6 space-y-3">
            {rows.map(([label, copy, status]) => (
              <div
                key={label}
                className="flex items-center gap-3 rounded-2xl border border-line bg-white p-3.5"
              >
                <div
                  className={`grid size-10 shrink-0 place-items-center rounded-xl ${
                    status === "check" ? "bg-green-50 text-success" : "bg-amber-50 text-warning"
                  }`}
                >
                  {status === "check" ? <FileCheck2 size={19} /> : <CircleAlert size={19} />}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-bold text-ink">{label}</p>
                  <p className="truncate text-xs text-muted">{copy}</p>
                </div>
                {status === "check" ? (
                  <CheckCircle2 className="text-success" size={18} />
                ) : (
                  <CircleAlert className="text-warning" size={18} />
                )}
              </div>
            ))}
          </div>
          <div className="mt-5 rounded-2xl bg-ink p-4 text-white">
            <div className="flex items-center justify-between text-sm">
              <span className="font-semibold">Evidence checks</span>
              <span className="font-bold">4 of 6 passed</span>
            </div>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-white/15">
              <div className="h-full w-2/3 rounded-full bg-brand" />
            </div>
          </div>
        </div>
      </div>
      <div className="absolute -right-4 top-1/3 hidden rounded-2xl border border-line bg-white p-3 shadow-lg sm:flex">
        <ShieldCheck className="text-brand" size={22} />
      </div>
    </div>
  );
}

function HomePage({ go }: { go: (route: Route) => void }) {
  const steps = [
    [
      "Upload Evidence",
      "Fundraiser posts, permits, payment screenshots, and supporting documents.",
    ],

    ["Private Storage", "Documents are saved privately on the project backend for review."],

    ["Human Review", "Administrators assess the campaign details and supporting evidence."],

    [
      "Verified Directory",
      "Approved campaigns appear publicly with their available evidence scores.",
    ],
  ];

  return (
    <>
      <main>
        <section className="overflow-hidden bg-white py-16 sm:py-20 lg:py-24">
          <div className="container grid items-center gap-14 lg:grid-cols-[1.02fr_.98fr]">
            <div>
              <Badge tone="red">
                <span className="status-dot bg-brand" /> Private evidence ? Human review
              </Badge>
              <h1 className="mt-7 max-w-xl text-5xl font-extrabold leading-[1.02] tracking-[-0.045em] text-ink sm:text-6xl lg:text-7xl">
                Verify before <span className="text-brand">you give.</span>
              </h1>
              <p className="mt-6 max-w-xl text-lg leading-8 text-muted">
                Browse verified relief campaigns and submit fundraiser posts, permits, and
                supporting documents for human review.
              </p>
              <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                <Button onClick={() => go("/verify")}>
                  Submit a Fundraiser <ArrowRight size={17} />
                </Button>
                <Button variant="secondary" onClick={() => go("/campaigns")}>
                  Browse Campaigns
                </Button>
              </div>
              <p className="mt-6 flex items-center gap-2 text-sm font-medium text-muted">
                <ShieldCheck size={17} className="text-success" /> Supporting documents are stored
                privately on the project backend.
              </p>
            </div>
            <HeroMockup />
          </div>
        </section>

        <section id="about" className="section bg-canvas">
          <div className="container">
            <div className="section-heading">
              <p className="eyebrow">Confidence through clarity</p>
              <h2>Built for moments when verification matters most</h2>
              <p>
                Practical checks that protect privacy and keep the final decision in your hands.
              </p>
            </div>
            <div className="mt-11 grid gap-5 md:grid-cols-3">
              <FeatureCard
                icon={<WifiOff size={22} />}
                title="Local Processing"
                copy="Evidence is kept on the project backend and never sent to external AI services."
              />
              <FeatureCard
                icon={<ShieldCheck size={22} />}
                title="Private by Design"
                copy="Sensitive documents do not need to be sent to a cloud AI provider."
              />
              <FeatureCard
                icon={<Search size={22} />}
                title="Evidence, Not Accusations"
                copy="Missing evidence calls for human review and does not imply fraud."
              />
            </div>
          </div>
        </section>

        <section id="how" className="section bg-white">
          <div className="container">
            <div className="section-heading">
              <p className="eyebrow">Simple by design</p>
              <h2>From documents to a clearer decision</h2>
              <p>Four focused steps help you understand the evidence before you donate.</p>
            </div>
            <div className="relative mt-14 grid gap-5 md:grid-cols-4">
              <div className="absolute left-[12.5%] right-[12.5%] top-6 hidden h-px bg-line md:block">
                <div className="progress-line h-full w-3/4 bg-brand" />
              </div>
              {steps.map(([title, copy], index) => (
                <article
                  key={title}
                  className="relative rounded-2xl border border-line bg-white p-5 md:border-0 md:p-3"
                >
                  <div className="relative z-10 grid size-12 place-items-center rounded-2xl border-4 border-white bg-soft-red text-sm font-extrabold text-brand">
                    {String(index + 1).padStart(2, "0")}
                  </div>
                  <h3 className="mt-5 font-bold text-ink">{title}</h3>
                  <p className="mt-2 text-sm leading-6 text-muted">{copy}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="section bg-canvas">
          <div className="container">
            <div className="overflow-hidden rounded-[2rem] border border-line bg-white shadow-xl shadow-zinc-900/5">
              <div className="grid lg:grid-cols-[.72fr_1.28fr]">
                <div className="bg-brand p-8 text-white sm:p-11">
                  <div className="grid size-11 place-items-center rounded-2xl bg-white/15">
                    <Sparkles size={22} />
                  </div>
                  <p className="mt-8 text-sm font-bold uppercase tracking-[0.14em] text-white/70">
                    PanataanPH
                  </p>
                  <h2 className="mt-2 text-3xl font-extrabold tracking-tight">
                    Submit a Fundraiser
                  </h2>
                  <p className="mt-4 leading-7 text-white/80">
                    Submit your campaign and evidence to the project backend for private review.
                  </p>
                  <div className="mt-8 flex items-center gap-2 text-sm font-semibold">
                    <ShieldCheck size={18} /> Private by design
                  </div>
                </div>
                <div className="p-6 sm:p-9">
                  <p className="text-lg font-bold">Campaign details and supporting evidence</p>
                  <p className="mt-3 leading-7 text-muted">
                    Prepare your fundraiser screenshot, permits, registration, and donation details.
                    The form accepts up to four PDF, JPG, or PNG documents.
                  </p>
                  <Button className="mt-5 w-full" onClick={() => go("/verify")}>
                    Open Submission Form <ArrowRight size={17} />
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </section>
        <section id="privacy" className="container pb-12">
          <div className="report-card">
            <h2 className="text-xl font-extrabold">Evidence privacy</h2>
            <p className="mt-3 text-sm leading-7 text-muted">
              Supporting documents and organizer contact details are saved privately on the project
              backend for human review. Uploaded evidence is never sent to external AI services or
              published in the directory.
            </p>
            <p className="mt-3 text-sm leading-7 text-muted">
              Campaign descriptions, organizer names, and donation details become public after
              approval. Automatic extraction and the administrator review interface are still being
              developed.
            </p>
          </div>
        </section>
      </main>
      <Footer go={go} />
    </>
  );
}

export default function App() {
  const [route, setRoute] = useState<Route>(routeFromPath);

  const [submission, setSubmission] = useState<Submission | null>(null);

  const go = (next: Route | string) => {
    if (next.includes("#")) {
      const [path, hash] = next.split("#");

      if (window.location.pathname !== path) window.history.pushState({}, "", next);

      setRoute(path as Route);

      window.setTimeout(
        () => document.getElementById(hash)?.scrollIntoView({ behavior: "smooth" }),
        30,
      );

      return;
    }

    window.history.pushState({}, "", next);

    setRoute(next as Route);

    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  useEffect(() => {
    const onPop = () => setRoute(routeFromPath());

    window.addEventListener("popstate", onPop);

    return () => window.removeEventListener("popstate", onPop);
  }, []);

  return (
    <div className="min-h-screen bg-canvas text-ink">
      <Navbar route={route} go={go} />
      {route === "/" && <HomePage go={go} />}
      {route === "/verify" && <SubmissionPage go={go} onSubmitted={setSubmission} />}
      {route === "/verify/processing" && <SubmissionReport submission={submission} go={go} />}
      {route === "/verify/report" && <SubmissionReport submission={submission} go={go} />}
      {route === "/campaigns" && <CampaignDirectory go={go} />}
      {route.startsWith("/campaigns/") && (
        <CampaignReport id={route.slice("/campaigns/".length)} go={go} />
      )}
    </div>
  );
}
