import { ArrowRight, FileCheck, HeartHandshake, LockKeyhole, ShieldCheck } from "lucide-react";

export function AboutPage({ go }: { go: (path: string) => void }) {
  return (
    <main className="min-h-screen bg-canvas">
      <section className="border-b border-line bg-white">
        <div className="container py-12 sm:py-16">
          <span className="badge badge-red">About PanataanPH</span>
          <h1 className="mt-5 max-w-3xl text-3xl font-extrabold tracking-tight sm:text-5xl">Clear evidence. Human review. Informed giving.</h1>
          <p className="mt-5 max-w-2xl text-base leading-7 text-muted">
            PanataanPH brings Philippine relief drives and fundraisers into one directory, with
            campaign details, review status, donation methods, and reported use of funds.
          </p>
        </div>
      </section>
      <div className="container py-10 sm:py-14">
        <div className="grid gap-5 md:grid-cols-2">
          {[
            { icon: FileCheck, title: "Evidence, explained", text: "Fixed application rules calculate evidence completeness from 0 to 100. The score is not a fraud probability or a guarantee of legitimacy. Missing information triggers further review." },
            { icon: ShieldCheck, title: "People make the decision", text: "Authorized administrators and LGU reviewers inspect campaign evidence. Publication requires human approval and the score threshold, or an administrator's documented exception. Account review and campaign approval are separate." },
            { icon: LockKeyhole, title: "Private documents", text: "Supporting permits, IDs, and other evidence stay in private storage, available only to authorized reviewers. Uploaded documents are never sent to external AI services." },
            { icon: HeartHandshake, title: "Transparent fund reports", text: "Organizers report received and spent funds. Administrators review those reports before public totals update. Reports describe organizer-provided information; PanataanPH does not collect donations or confirm bank balances." },
          ].map(({ icon: Icon, title, text }) => (
            <section key={title} className="feature-card">
              <div className="feature-icon"><Icon size={22} /></div>
              <h2 className="mt-5 text-xl font-extrabold">{title}</h2>
              <p className="mt-3 text-sm leading-7 text-muted">{text}</p>
            </section>
          ))}
        </div>
        <section className="report-card mt-8">
          <p className="eyebrow">How publication works</p>
          <h2 className="mt-3 text-2xl font-extrabold">From submission to public campaign</h2>
          <ol className="mt-6 grid gap-6 md:grid-cols-3">
            {[
              ["Sign in and submit", "Create an organizer account, describe your fundraiser, and upload supporting evidence. Donation QR images are provided separately for publication after approval."],
              ["Administrator review", "Authorized reviewers assess your account, evidence, and campaign details. They approve, reject with a reason, or request more information."],
              ["Publish and report", "Approved campaigns meeting the score threshold, or a documented administrator exception, appear in the directory. Organizers can submit fund reports for review and publication."],
            ].map(([title, text], index) => (
              <li key={title} className="min-w-0">
                <span className="grid size-9 place-items-center rounded-xl bg-soft-red text-sm font-extrabold text-brand">{index + 1}</span>
                <h3 className="mt-4 font-extrabold">{title}</h3>
                <p className="mt-2 text-sm leading-6 text-muted">{text}</p>
              </li>
            ))}
          </ol>
        </section>
        <div className="mt-8 flex flex-wrap gap-3">
          <button className="button button-primary" onClick={() => go("/campaigns")}>Browse Campaigns <ArrowRight size={17} /></button>
          <button className="button button-secondary" onClick={() => go("/verify")}>Submit a Fundraiser</button>
        </div>
      </div>
    </main>
  );
}
