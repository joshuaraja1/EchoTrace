import Link from "next/link";
import { ArrowUpRight, CheckCircle2, GitMerge, Play, ShieldCheck } from "lucide-react";
import { Mark } from "@/components/mark";

export default function Home() {
  return (
    <main className="landing">
      <nav className="landing-nav">
        <Mark />
        <Link className="button button-quiet" href="/app">Open workspace <ArrowUpRight size={16} /></Link>
      </nav>
      <section className="hero">
        <div className="eyebrow"><span className="live-dot" /> Evidence reconstruction system / 01</div>
        <h1>One timeline.<br /><em>Every perspective.</em></h1>
        <p className="hero-copy">EchoTrace aligns scattered video evidence into a traceable incident reconstruction—with a source behind every conclusion.</p>
        <div className="hero-actions">
          <Link className="button button-primary" href="/app">Start a reconstruction <ArrowUpRight size={17} /></Link>
          <a className="text-link" href="#method"><Play size={15} fill="currentColor" /> See how it works</a>
        </div>
        <div className="hero-proof">
          <span><ShieldCheck size={17} /> Evidence remains immutable</span>
          <span><CheckCircle2 size={17} /> Human review built in</span>
          <span><GitMerge size={17} /> Multi-source synchronization</span>
        </div>
      </section>
      <section className="method" id="method">
        <div className="method-heading">
          <span className="section-index">METHOD / 03 STEPS</span>
          <h2>From isolated footage to a defensible sequence.</h2>
        </div>
        <div className="method-grid">
          {[
            ["01", "Ingest", "Upload videos, images, PDFs, and witness notes. Every original is fingerprinted on arrival."],
            ["02", "Synchronize", "Audio, visual, and metadata signals estimate one shared clock—with uncertainty preserved."],
            ["03", "Investigate", "Review events, compare perspectives, correct the record, and ask evidence-grounded questions."],
          ].map(([n, title, copy]) => (
            <article className="method-card" key={n}>
              <span>{n}</span><h3>{title}</h3><p>{copy}</p>
            </article>
          ))}
        </div>
      </section>
      <footer className="landing-footer">
        <Mark /><p>Reconstructs what the evidence shows. Never assigns fault.</p>
      </footer>
    </main>
  );
}
