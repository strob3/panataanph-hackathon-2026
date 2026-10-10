import {
  ArrowRight,
  FileCheck,
  FileSpreadsheet,
  LockKeyhole,
  Scale,
  ShieldAlert,
} from "lucide-react";

export function TermsPage({ go }: { go: (path: string) => void }) {
  return (
    <main className="min-h-screen bg-canvas">
      <section className="border-b border-line bg-white">
        <div className="container py-12 sm:py-16">
          <span className="badge badge-red">PanataanPH Terms</span>
          <h1 className="mt-5 max-w-3xl text-3xl font-extrabold tracking-tight sm:text-5xl">
            Terms of Service
          </h1>
          <p className="mt-5 max-w-2xl text-base leading-7 text-muted">
            These Terms govern your access to and use of PanataanPH. By accessing the directory,
            registering an account, or submitting a fundraiser, you agree to these terms.
          </p>
        </div>
      </section>

      <div className="container py-10 sm:py-14">
        <div className="grid gap-5 md:grid-cols-2">
          {[
            {
              icon: FileSpreadsheet,
              title: "Directory Only",
              text: "PanataanPH is a non-commercial verification directory and transparency platform. PanataanPH does not collect, hold, process, escrow, or distribute funds. All donations occur directly between donors and campaign organizers through organizer-provided payment accounts.",
            },
            {
              icon: FileCheck,
              title: "Verification & Scoring Disclaimer",
              text: "The 0–100 evidence completeness score is computed deterministically from submitted documents. It measures document presence against a structured rubric—not a fraud guarantee, endorsement, or insurance of campaign legitimacy. Human administrator review assists in evaluating records, but does not guarantee organizer conduct.",
            },
            {
              icon: Scale,
              title: "Organizer Responsibilities",
              text: "Campaign organizers represent that all submitted evidence, identification, permits, and campaign narratives are authentic, accurate, and unaltered. Organizers agree to apply funds strictly to stated relief purposes and submit truthful financial updates. Submitting falsified documents or fraudulent drives violates Philippine law and results in immediate delisting.",
            },
            {
              icon: LockKeyhole,
              title: "Evidence Privacy & RA 10173",
              text: "Supporting documents (such as government IDs and permits) are stored securely in private storage and accessible only to authorized reviewers. In compliance with the Data Privacy Act of 2012 (RA 10173), uploaded evidence is never forwarded to external third-party AI APIs or published publicly.",
            },
          ].map(({ icon: Icon, title, text }) => (
            <section key={title} className="feature-card">
              <div className="feature-icon">
                <Icon size={22} />
              </div>
              <h2 className="mt-5 text-xl font-extrabold">{title}</h2>
              <p className="mt-3 text-sm leading-7 text-muted">{text}</p>
            </section>
          ))}
        </div>

        <section className="report-card mt-8">
          <div className="flex items-center gap-3">
            <ShieldAlert className="text-brand" size={24} />
            <h2 className="text-2xl font-extrabold">Limitation of Liability & Donor Discretion</h2>
          </div>
          <div className="mt-5 space-y-4 text-sm leading-7 text-muted">
            <p>
              PanataanPH and its maintainers provide this platform on an &ldquo;as is&rdquo; and
              &ldquo;as available&rdquo; basis. While we enforce verification rubrics and human
              review, donors give at their own independent discretion and risk.
            </p>
            <p>
              To the fullest extent permitted by Philippine law, PanataanPH and its contributors are
              not liable for direct, indirect, incidental, or consequential damages resulting from
              donation transactions, organizer misrepresentations, or third-party service
              disruptions.
            </p>
          </div>
        </section>

        <section className="report-card mt-8">
          <h2 className="text-xl font-extrabold">Prohibited Conduct & Removal</h2>
          <p className="mt-3 text-sm leading-7 text-muted">
            Users agree not to: (1) forge permits or misrepresent identities; (2) divert relief
            funds for personal enrichment; (3) interfere with platform security or offline OCR/LLM
            operations; or (4) scrape private evidence. PanataanPH reserves the right to reject,
            unpublish, or permanently ban any campaign or account found in breach of these terms.
          </p>
        </section>

        <div className="mt-8 flex flex-wrap gap-3">
          <button className="button button-primary" onClick={() => go("/campaigns")}>
            Browse Campaigns <ArrowRight size={17} />
          </button>
          <button className="button button-secondary" onClick={() => go("/verify")}>
            Submit a Fundraiser
          </button>
        </div>
      </div>
    </main>
  );
}
