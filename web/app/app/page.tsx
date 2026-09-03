"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { ArrowRight, CalendarDays, FileVideo2, LogOut, MapPin, Plus, ShieldCheck } from "lucide-react";
import { Mark } from "@/components/mark";
import { api, getToken, setToken } from "@/lib/api";
import type { Investigation, User } from "@/lib/types";

const initialCase = {
  title: "", incident_type: "Traffic collision", incident_date: new Date().toISOString().slice(0, 10),
  approximate_time: "", location: "", description: "",
};

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [cases, setCases] = useState<Investigation[]>([]);
  const [mode, setMode] = useState<"login" | "register">("login");
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [caseForm, setCaseForm] = useState(initialCase);
  const [showCreate, setShowCreate] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!getToken()) return;
    let active = true;
    Promise.all([api.me(), api.investigations()]).then(([me, investigations]) => {
      if (active) { setUser(me); setCases(investigations); }
    }).catch(() => setToken(null));
    return () => { active = false; };
  }, []);

  async function authenticate(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError("");
    try {
      const result = mode === "login"
        ? await api.login({ email: form.email, password: form.password })
        : await api.register(form);
      setToken(result.access_token); setUser(result.user); setCases(await api.investigations());
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Authentication failed"); }
    finally { setBusy(false); }
  }

  async function createCase(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError("");
    try {
      const body = Object.fromEntries(Object.entries(caseForm).filter(([, value]) => value));
      const created = await api.createInvestigation(body); router.push(`/app/investigations/${created.investigation_id}`);
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Could not create investigation"); }
    finally { setBusy(false); }
  }

  if (!user) return (
    <main className="auth-shell">
      <Link href="/" className="auth-brand"><Mark /></Link>
      <section className="auth-story">
        <span className="section-index">SECURE EVIDENCE WORKSPACE</span>
        <h1>Bring the incident<br />into <em>focus.</em></h1>
        <p>Separate sources become one reviewable sequence. Every inference stays tied to the evidence.</p>
        <div className="auth-rule"><ShieldCheck size={20} /><span>Original uploads are preserved and fingerprinted with SHA-256.</span></div>
      </section>
      <section className="auth-panel">
        <div className="auth-tabs">
          <button className={mode === "login" ? "active" : ""} onClick={() => setMode("login")}>Sign in</button>
          <button className={mode === "register" ? "active" : ""} onClick={() => setMode("register")}>Create account</button>
        </div>
        <form onSubmit={authenticate} className="form-stack">
          <div><span className="section-index">{mode === "login" ? "WELCOME BACK" : "GET STARTED"}</span><h2>{mode === "login" ? "Continue your investigation." : "Create your secure workspace."}</h2></div>
          {mode === "register" && <label>Your name<input required value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="Jordan Lee" /></label>}
          <label>Email address<input required type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} placeholder="jordan@example.com" /></label>
          <label>Password<input required minLength={10} type="password" value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} placeholder="10+ characters" /></label>
          {error && <p className="form-error">{error}</p>}
          <button className="button button-primary button-wide" disabled={busy}>{busy ? "Securing workspace…" : mode === "login" ? "Sign in" : "Create account"}<ArrowRight size={17} /></button>
        </form>
      </section>
    </main>
  );

  return (
    <main className="app-shell">
      <header className="app-header"><Mark /><div className="header-meta"><span>{user.name}</span><button title="Sign out" onClick={() => { setToken(null); setUser(null); }}><LogOut size={17} /></button></div></header>
      <section className="dashboard">
        <div className="dashboard-title"><div><span className="section-index">INVESTIGATION INDEX</span><h1>Case workspace</h1><p>{cases.length} active record{cases.length === 1 ? "" : "s"}</p></div><button className="button button-primary" onClick={() => setShowCreate(true)}><Plus size={17} /> New investigation</button></div>
        {cases.length ? <div className="case-list">{cases.map((item, index) => (
          <Link href={`/app/investigations/${item.investigation_id}`} className="case-row" key={item.investigation_id}>
            <span className="case-number">{String(index + 1).padStart(2, "0")}</span>
            <div className="case-main"><span className={`status status-${item.status}`}>{item.status.replaceAll("_", " ")}</span><h2>{item.title}</h2><p>{item.incident_type}</p></div>
            <div className="case-meta"><span><CalendarDays size={15} />{item.incident_date}</span><span><MapPin size={15} />{item.location}</span></div>
            <ArrowRight className="case-arrow" size={20} />
          </Link>
        ))}</div> : <div className="empty-state"><FileVideo2 size={30} /><h2>No evidence rooms yet.</h2><p>Open your first investigation and begin adding source material.</p><button className="text-link" onClick={() => setShowCreate(true)}>Create an investigation <ArrowRight size={15} /></button></div>}
      </section>
      {showCreate && <div className="modal-backdrop" onMouseDown={() => setShowCreate(false)}><section className="modal" onMouseDown={e => e.stopPropagation()}>
        <button className="modal-close" onClick={() => setShowCreate(false)}>×</button><span className="section-index">NEW RECORD</span><h2>Open an investigation</h2>
        <form className="form-stack" onSubmit={createCase}>
          <label>Case title<input required value={caseForm.title} onChange={e => setCaseForm({...caseForm, title:e.target.value})} placeholder="Oak & 7th collision" /></label>
          <div className="form-grid"><label>Incident type<input required value={caseForm.incident_type} onChange={e => setCaseForm({...caseForm, incident_type:e.target.value})} /></label><label>Date<input required type="date" value={caseForm.incident_date} onChange={e => setCaseForm({...caseForm, incident_date:e.target.value})} /></label></div>
          <div className="form-grid"><label>Approx. time<input type="time" value={caseForm.approximate_time} onChange={e => setCaseForm({...caseForm, approximate_time:e.target.value})} /></label><label>Location<input required value={caseForm.location} onChange={e => setCaseForm({...caseForm, location:e.target.value})} placeholder="Austin, TX" /></label></div>
          <label>Known context<textarea value={caseForm.description} onChange={e => setCaseForm({...caseForm, description:e.target.value})} placeholder="Describe only what is known before review." /></label>
          {error && <p className="form-error">{error}</p>}<button className="button button-primary button-wide" disabled={busy}>Create evidence room <ArrowRight size={17} /></button>
        </form>
      </section></div>}
    </main>
  );
}
