"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ChangeEvent, FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import {
  ArrowLeft, Bot, Check, ChevronRight, CircleAlert, Clock3, File, FileImage, FileText,
  FileVideo2, GitFork, LoaderCircle, Maximize2, MessageSquareText, Network, Pause, Play,
  PanelRightClose, PanelRightOpen, Pencil, RefreshCw, ScanSearch, ShieldCheck,
  SlidersHorizontal, Sparkles, Upload, X,
} from "lucide-react";
import { Mark } from "@/components/mark";
import { api, getToken, setToken } from "@/lib/api";
import type { Citation, Evidence, EvidenceGraph, Investigation, ObjectMatch, Timeline, TimelineEvent } from "@/lib/types";

type Tab = "reconstruct" | "timeline" | "objects" | "ask" | "graph";
type AiCitation = { event_id?: string; global_timestamp_seconds?: number; evidence?: Citation[]; evidence_id?: string; source?: string; type?: string; frame_url?: string; local_timestamp_seconds?: number; confidence?: number };
type AiResult = { answer?: string; summary?: string; confidence: number; citations: AiCitation[]; warning: string };

function seconds(value: number) {
  const safe = Math.max(0, value || 0); const mins = Math.floor(safe / 60); const secs = safe % 60;
  return `${String(mins).padStart(2, "0")}:${secs.toFixed(2).padStart(5, "0")}`;
}

function Confidence({ value }: { value?: number | null }) {
  const percent = Math.round((value ?? 0) * 100);
  return <span className={`confidence ${percent < 55 ? "confidence-low" : percent < 80 ? "confidence-mid" : ""}`}><i style={{ width: `${percent}%` }} />{percent}%</span>;
}

function EvidenceIcon({ type }: { type: string }) {
  if (type.includes("video")) return <FileVideo2 size={18} />;
  if (type.includes("image")) return <FileImage size={18} />;
  if (type.includes("pdf") || type.includes("text")) return <FileText size={18} />;
  return <File size={18} />;
}

async function openProtectedCitation(citation: Citation) {
  const target = window.open("", "_blank");
  try {
    const path = citation.frame_url ?? "";
    const url = await api.blob(path);
    if (target) target.location.href = url;
    else window.location.href = url;
    window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
  } catch {
    target?.close();
  }
}

function ProtectedMedia({ investigationId, evidence, globalTime, playing, playbackRate, onReady }: {
  investigationId: string; evidence: Evidence; globalTime: number; playing: boolean; playbackRate: number; onReady?: (duration: number) => void;
}) {
  const [url, setUrl] = useState(""); const video = useRef<HTMLVideoElement>(null);
  useEffect(() => {
    let alive = true; let objectUrl = "";
    api.blob(`/investigations/${investigationId}/evidence/${evidence.evidence_id}/content`).then(value => {
      objectUrl = value; if (alive) setUrl(value); else URL.revokeObjectURL(value);
    }).catch(() => undefined);
    return () => { alive = false; if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [evidence.evidence_id, investigationId]);
  useEffect(() => {
    if (!video.current) return;
    const local = Math.max(0, globalTime - (evidence.effective_offset || 0));
    if (Math.abs(video.current.currentTime - local) > .18) video.current.currentTime = local;
    video.current.playbackRate = playbackRate;
    if (playing) video.current.play().catch(() => undefined); else video.current.pause();
  }, [globalTime, playing, playbackRate, evidence.effective_offset]);
  if (!url) return <div className="media-loading"><LoaderCircle className="spin" size={20} /> Loading protected source</div>;
  if (evidence.media_type.includes("video")) return <video ref={video} src={url} muted playsInline onLoadedMetadata={e => onReady?.(e.currentTarget.duration)} />;
  // Protected blob URLs cannot be optimized by the Next image pipeline.
  // eslint-disable-next-line @next/next/no-img-element
  if (evidence.media_type.includes("image")) return <img src={url} alt={evidence.original_filename} />;
  return <div className="document-source"><FileText size={28} /><span>{evidence.original_filename}</span><a href={url} download={evidence.original_filename}>Open original</a></div>;
}

function Reconstructor({ id, investigation, timeline, jumpTime, onRefresh, onAddEvidence }: { id: string; investigation: Investigation; timeline: Timeline | null; jumpTime: number; onRefresh: () => Promise<void>; onAddEvidence: () => void }) {
  const evidence = investigation.evidence ?? []; const visual = evidence.filter(item => item.media_type.includes("video") || item.media_type.includes("image"));
  const [time, setTime] = useState(jumpTime); const [playing, setPlaying] = useState(false); const [max, setMax] = useState(60);
  const [speed, setSpeed] = useState(1); const [isolated, setIsolated] = useState<string | null>(null);
  const [syncOpen, setSyncOpen] = useState(false); const [syncValues, setSyncValues] = useState<Record<string, number>>({}); const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  useEffect(() => {
    if (timer.current) clearInterval(timer.current);
    if (playing) timer.current = setInterval(() => setTime(value => value >= max ? 0 : value + .1 * speed), 100);
    return () => { if (timer.current) clearInterval(timer.current); };
  }, [playing, max, speed]);
  async function saveOffsets() {
    await Promise.all(evidence.map(item => api.adjustSync(id, item.evidence_id, syncValues[item.evidence_id] ?? item.effective_offset ?? 0, "Manual alignment from synchronized review")));
    setSyncOpen(false); await onRefresh();
  }
  if (!evidence.length) return <div className="stage-empty evidence-empty">
    <div className="empty-source-map" aria-hidden="true"><span>CAM 01</span><span>CAM 02</span><i><GitFork size={22}/></i><span>AUDIO</span></div>
    <span className="section-index">RECONSTRUCTION / READY FOR INPUT</span>
    <h2>Build the case from source evidence.</h2>
    <p>Add independent views of the same incident. EchoTrace preserves each original, extracts time signals, and aligns them on one reviewable clock.</p>
    <button type="button" className="button button-primary empty-action" onClick={onAddEvidence}><Upload size={17}/> Add source files</button>
    <div className="empty-steps"><span><b>01</b> Add sources</span><span><b>02</b> Process evidence</span><span><b>03</b> Align the clocks</span></div>
  </div>;
  return <section className="reconstructor">
    <div className="source-grid" style={{ gridTemplateColumns: `repeat(${isolated ? 1 : Math.min(Math.max(visual.length, 1), 3)}, minmax(0, 1fr))` }}>
      {visual.slice(0, 3).filter(item => !isolated || isolated === item.evidence_id).map((item, index) => <article className="source-view" key={item.evidence_id}>
        <div className="source-label"><span>CAM {String(index + 1).padStart(2, "0")}</span><span className="source-tools"><span>{seconds(time - item.effective_offset)}</span><button title={isolated ? "Show all feeds" : "Isolate feed"} onClick={() => setIsolated(isolated ? null : item.evidence_id)}><Maximize2 size={12}/></button></span></div>
        <ProtectedMedia investigationId={id} evidence={item} globalTime={time} playing={playing} playbackRate={speed} onReady={duration => setMax(value => Math.max(value, duration + item.effective_offset))} />
        <div className="source-foot"><span>{item.original_filename}</span><Confidence value={item.sync_confidence} /></div>
      </article>)}
      {!visual.length && <div className="stage-empty"><FileText size={29}/><h2>Document-only evidence set</h2><p>Open the timeline or Ask EchoTrace to inspect extracted context.</p></div>}
    </div>
    <div className="transport">
      <button className="play-control" onClick={() => setPlaying(!playing)}>{playing ? <Pause size={18} fill="currentColor" /> : <Play size={18} fill="currentColor" />}</button>
      <span className="timecode">{seconds(time)}</span>
      <input aria-label="Global investigation time" type="range" min="0" max={max} step=".05" value={Math.min(time, max)} onChange={event => { setTime(Number(event.target.value)); setPlaying(false); }} />
      <span className="timecode timecode-muted">{seconds(max)}</span>
      <select aria-label="Playback speed" value={speed} onChange={event => setSpeed(Number(event.target.value))}><option value=".5">0.5×</option><option value="1">1×</option><option value="1.5">1.5×</option><option value="2">2×</option></select>
      <button className="icon-button labeled" onClick={() => { setSyncValues(Object.fromEntries(evidence.map(item => [item.evidence_id, item.effective_offset]))); setSyncOpen(true); }}><SlidersHorizontal size={16} /> Align</button>
    </div>
    <div className="sync-rail">
      <div className="rail-header"><span>GLOBAL CLOCK</span><span>{timeline?.event_count ?? 0} detected events</span></div>
      <div className="rail-line">{timeline?.events.map(event => <button key={event.event_id} style={{ left: `${Math.min(100, event.global_timestamp_seconds / max * 100)}%` }} title={event.description} onClick={() => { setTime(event.global_timestamp_seconds); setPlaying(false); }}><i /><span>{event.event_type.replaceAll("_", " ")}</span></button>)}</div>
    </div>
    {syncOpen && <div className="modal-backdrop"><section className="modal sync-modal"><button type="button" aria-label="Close alignment dialog" className="modal-close" onClick={() => setSyncOpen(false)}><X size={18}/></button><span className="section-index">MANUAL ALIGNMENT</span><h2>Refine the global clock</h2><p>Set each source&apos;s start position relative to the investigation clock. Original estimates remain in the audit history.</p>
      <div className="offset-list">{evidence.map(item => <label key={item.evidence_id}><span>{item.original_filename}</span><div><input type="number" step=".01" value={syncValues[item.evidence_id] ?? item.effective_offset} onChange={event => setSyncValues({...syncValues, [item.evidence_id]: Number(event.target.value)})} /><small>sec</small></div></label>)}</div>
      <button className="button button-primary button-wide" onClick={saveOffsets}>Save alignment <Check size={17} /></button>
    </section></div>}
  </section>;
}

function TimelineView({ id, timeline, onJump, onRefresh }: { id: string; timeline: Timeline | null; onJump: (time: number) => void; onRefresh: () => Promise<void> }) {
  const [selected, setSelected] = useState<TimelineEvent | null>(null); const [description, setDescription] = useState(""); const [stamp, setStamp] = useState(0); const [confidence, setConfidence] = useState(0);
  function select(event: TimelineEvent) { setSelected(event); setDescription(event.description); setStamp(event.global_timestamp_seconds); setConfidence(event.confidence); }
  async function save() { if (!selected) return; await api.correctEvent(id, selected.event_id, { description, timestamp_seconds: stamp, confidence, note: "Human review in evidence workspace" }); setSelected(null); await onRefresh(); }
  return <section className="timeline-view">
    <header className="panel-heading"><div><span className="section-index">UNIFIED SEQUENCE</span><h2>What happened, in order</h2></div><div className="panel-stat"><strong>{timeline?.event_count ?? 0}</strong><span>events</span></div></header>
    {!timeline?.events.length ? <div className="stage-empty"><Clock3 size={29}/><h2>No events detected yet.</h2><p>Process your evidence to generate the first reconstruction.</p></div> : <div className="event-list">{timeline.events.map((event, index) => <article className="event-row" key={event.event_id}>
      <button className="event-jump" title="Jump all cameras to this event" onClick={() => onJump(event.global_timestamp_seconds)}><span className="event-index">{String(index + 1).padStart(2, "0")}</span><span className="event-time">T+ {seconds(event.global_timestamp_seconds)}</span><span className="event-body"><small>{event.event_type.replaceAll("_", " ")} · {event.review_status}</small><strong>{event.description}</strong><em>{event.evidence_count} source{event.evidence_count === 1 ? "" : "s"} corroborate this event</em></span><Confidence value={event.confidence} /><Play size={16}/></button>
      <button className="event-edit" title="Review or correct event" onClick={() => select(event)}><Pencil size={14}/></button>
    </article>)}</div>}
    {selected && <div className="modal-backdrop"><section className="modal"><button type="button" aria-label="Close event review" className="modal-close" onClick={() => setSelected(null)}><X size={18}/></button><span className="section-index">HUMAN CORRECTION / AUDITED</span><h2>Review event</h2><div className="form-stack"><label>Description<textarea value={description} onChange={e => setDescription(e.target.value)} /></label><div className="form-grid"><label>Global timestamp (seconds)<input type="number" min="0" step=".01" value={stamp} onChange={e => setStamp(Number(e.target.value))} /></label><label>Confidence designation<input type="number" min="0" max="1" step=".01" value={confidence} onChange={e => setConfidence(Number(e.target.value))} /></label></div><div className="citation-strip">{selected.evidence.map(item => <button onClick={() => openProtectedCitation(item)} key={`${item.evidence_id}-${item.local_timestamp_seconds}`}>{item.source} · {seconds(item.local_timestamp_seconds)}</button>)}</div><button className="button button-primary button-wide" onClick={save}>Save correction <Check size={17}/></button></div></section></div>}
  </section>;
}

function ObjectReview({ id, objects, matches, onRefresh }: { id: string; objects: Array<Record<string, unknown>>; matches: ObjectMatch[]; onRefresh: () => Promise<void> }) {
  const tracks = useMemo(() => {
    const unique = new Map<string, Record<string, unknown>>(); objects.forEach(item => unique.set(`${item.evidence_id}-${item.track_id}`, item)); return [...unique.values()];
  }, [objects]);
  const [editing, setEditing] = useState<Record<string, unknown> | null>(null); const [identity, setIdentity] = useState("");
  async function review(matchId: string, decision: "confirmed" | "rejected") { await api.reviewMatch(id, matchId, decision); await onRefresh(); }
  async function saveIdentity() { if (!editing) return; await api.correctObject(id, String(editing.evidence_id), Number(editing.track_id), identity, "Human identity label"); setEditing(null); await onRefresh(); }
  return <section className="review-grid">
    <div className="review-column"><header className="panel-heading"><div><span className="section-index">TRACK REGISTER</span><h2>Observed objects</h2></div><div className="panel-stat"><strong>{tracks.length}</strong><span>tracks</span></div></header>
      <div className="object-list">{tracks.map(track => <button className="object-row" key={`${track.evidence_id}-${track.track_id}`} onClick={() => { setEditing(track); setIdentity(String(track.canonical_identity ?? `${track.class_name} ${track.track_id}`)); }}><span className="object-glyph">{String(track.class_name).slice(0,1).toUpperCase()}</span><span><strong>{String(track.canonical_identity ?? `${track.class_name} ${track.track_id}`)}</strong><small>Track {String(track.track_id)} · {String(track.evidence_id).slice(0,8)}</small></span><ChevronRight size={17}/></button>)}</div>
    </div>
    <div className="review-column"><header className="panel-heading"><div><span className="section-index">CROSS-VIEW MATCHING</span><h2>Candidate identities</h2></div><div className="panel-stat"><strong>{matches.length}</strong><span>pairs</span></div></header>
      {!matches.length ? <div className="stage-empty compact"><ScanSearch size={26}/><p>No cross-view match candidates available.</p></div> : <div className="match-list">{matches.map(match => <article className="match-card" key={match.match_id}><div className="match-head"><GitFork size={18}/><Confidence value={match.probability}/></div><div className="match-pair"><span>{match.first.class_name} #{match.first.track_id}<small>{match.first.source}</small></span><i/><span>{match.second.class_name} #{match.second.track_id}<small>{match.second.source}</small></span></div><div className="match-review"><span className={`status status-${match.review_status}`}>{match.review_status}</span><button onClick={() => review(match.match_id, "rejected")}><X size={15}/> Reject</button><button onClick={() => review(match.match_id, "confirmed")}><Check size={15}/> Confirm</button></div></article>)}</div>}
    </div>
    {editing && <div className="modal-backdrop"><section className="modal"><button type="button" aria-label="Close object label dialog" className="modal-close" onClick={() => setEditing(null)}><X size={18}/></button><span className="section-index">CANONICAL IDENTITY</span><h2>Label tracked object</h2><div className="form-stack"><label>Identity label<input value={identity} onChange={e => setIdentity(e.target.value)} placeholder="Blue sedan A" /></label><p className="modal-note">This label changes the review layer only. The original detection record remains immutable.</p><button className="button button-primary button-wide" onClick={saveIdentity}>Save label <Check size={17}/></button></div></section></div>}
  </section>;
}

function AskView({ id }: { id: string }) {
  const [question, setQuestion] = useState(""); const [result, setResult] = useState<AiResult | null>(null); const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  async function run(prompt?: string) { const query = prompt ?? question; if (!query.trim()) return; setQuestion(query); setBusy(true); setError(""); try { setResult(await api.ask(id, query) as AiResult); } catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to answer"); } finally { setBusy(false); } }
  async function summarize() { setBusy(true); setError(""); try { setResult(await api.summary(id) as AiResult); } catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to summarize"); } finally { setBusy(false); } }
  const prompts = ["What happened immediately before the first potential impact?", "Which sources corroborate the highest-confidence event?", "Where does the evidence remain uncertain?"];
  const citedEvidence = result?.citations.flatMap(citation => citation.evidence ?? (citation.evidence_id ? [{ evidence_id: citation.evidence_id, source: citation.source ?? "Document evidence", local_timestamp_seconds: citation.local_timestamp_seconds ?? 0, global_timestamp_seconds: citation.global_timestamp_seconds ?? 0, confidence: citation.confidence ?? result.confidence, frame_url: citation.frame_url }] : [])) ?? [];
  return <section className="ask-layout"><div className="ask-intro"><span className="bot-mark"><Bot size={25}/></span><span className="section-index">EVIDENCE-GROUNDED ASSISTANT</span><h2>Ask the record.</h2><p>Answers are limited to processed evidence and cite their supporting source. EchoTrace does not determine fault or liability.</p><button className="button button-quiet" onClick={summarize}><Sparkles size={16}/> Generate incident summary</button></div>
    <div className="ask-console"><form onSubmit={(event: FormEvent) => { event.preventDefault(); run(); }}><MessageSquareText size={18}/><input value={question} onChange={e => setQuestion(e.target.value)} placeholder="Ask a question about this incident…"/><button disabled={busy}>{busy ? <LoaderCircle className="spin" size={17}/> : <ArrowLeft className="send-arrow" size={17}/>}</button></form>
      {!result && !busy && <div className="prompt-list"><span>Suggested questions</span>{prompts.map(prompt => <button onClick={() => run(prompt)} key={prompt}>{prompt}<ChevronRight size={16}/></button>)}</div>}
      {result && <article className="answer"><div className="answer-meta"><span>ECHOTRACE RESPONSE</span><Confidence value={result.confidence}/></div><p>{result.answer ?? result.summary}</p>{citedEvidence.length > 0 && <div className="sources"><span>SOURCES</span>{citedEvidence.map((citation, index) => <button onClick={() => citation.frame_url && openProtectedCitation(citation)} key={`${citation.evidence_id}-${index}`}><strong>{citation.source}</strong><small>T+ {seconds(citation.global_timestamp_seconds)} · {Math.round(citation.confidence * 100)}% confidence</small></button>)}</div>}<div className="ai-warning"><CircleAlert size={15}/>{result.warning}</div></article>}
      {error && <p className="form-error">{error}</p>}
    </div></section>;
}

function GraphView({ graph }: { graph: EvidenceGraph | null }) {
  const nodes = useMemo(() => graph?.nodes ?? [], [graph]); const edges = graph?.edges ?? []; const width = 900, height = 500;
  const [selected, setSelected] = useState<Record<string, string | number> | null>(null);
  const positions = useMemo(() => Object.fromEntries(nodes.map((node, index) => { const angle = index / Math.max(nodes.length,1) * Math.PI * 2 - Math.PI/2; const radius = index === 0 ? 0 : 175 + (index % 3) * 30; return [String(node.id), { x: width/2 + Math.cos(angle)*radius, y: height/2 + Math.sin(angle)*radius }]; })), [nodes]);
  return <section className="graph-view"><header className="panel-heading"><div><span className="section-index">EVIDENCE RELATIONSHIPS</span><h2>Reconstruction graph</h2></div><p>Sources, events, and tracked objects connected by traceable claims.</p></header>
    {!nodes.length ? <div className="stage-empty"><Network size={29}/><h2>No graph available.</h2><p>Process evidence to construct relationships.</p></div> : <div className="graph-canvas"><svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Evidence relationship graph">{edges.map((edge,index) => { const a=positions[edge.source], b=positions[edge.target]; return a&&b ? <line key={index} x1={a.x} y1={a.y} x2={b.x} y2={b.y} opacity={Math.max(.15,edge.confidence)}/> : null; })}{nodes.map(node => { const p=positions[String(node.id)]; const label=String(node.label ?? node.name ?? node.id); const kind=String(node.type ?? "evidence"); return p ? <g role="button" tabIndex={0} onClick={() => setSelected(node)} key={String(node.id)} transform={`translate(${p.x} ${p.y})`}><circle r={kind.includes("event") ? 23 : 18} className={`node-${kind}`}/><text y="36" textAnchor="middle">{label.length>22 ? `${label.slice(0,22)}…` : label}</text></g> : null; })}</svg><div className="graph-legend"><span><i className="legend-source"/> Evidence</span><span><i className="legend-event"/> Event</span><span><i className="legend-object"/> Object</span></div>{selected && <aside className="node-inspector"><button onClick={() => setSelected(null)}><X size={14}/></button><span>{String(selected.type)}</span><strong>{String(selected.label)}</strong>{selected.confidence !== undefined && <Confidence value={Number(selected.confidence)}/>}</aside>}</div>}
  </section>;
}

export function InvestigationWorkspace() {
  const id = String(useParams().id); const router = useRouter(); const fileInput = useRef<HTMLInputElement>(null);
  const reduceMotion = useReducedMotion();
  const [investigation, setInvestigation] = useState<Investigation | null>(null); const [timeline, setTimeline] = useState<Timeline | null>(null); const [objects, setObjects] = useState<Array<Record<string, unknown>>>([]); const [matches, setMatches] = useState<ObjectMatch[]>([]); const [graph, setGraph] = useState<EvidenceGraph | null>(null);
  const [tab, setTab] = useState<Tab>("reconstruct"); const [busy, setBusy] = useState(""); const [error, setError] = useState(""); const [dragging, setDragging] = useState(false); const [evidenceOpen, setEvidenceOpen] = useState(false);
  const [jumpTime, setJumpTime] = useState(0);
  async function load() { const [caseData, timeData, objectData, matchData, graphData] = await Promise.all([api.investigation(id), api.timeline(id), api.objects(id), api.matches(id), api.graph(id)]); setInvestigation(caseData); setTimeline(timeData); setObjects(objectData); setMatches(matchData); setGraph(graphData); }
  useEffect(() => {
    if (!getToken()) { router.replace("/app"); return; }
    let active = true;
    Promise.all([api.investigation(id), api.timeline(id), api.objects(id), api.matches(id), api.graph(id)]).then(([caseData, timeData, objectData, matchData, graphData]) => {
      if (active) { setInvestigation(caseData); setTimeline(timeData); setObjects(objectData); setMatches(matchData); setGraph(graphData); }
    }).catch(caught => {
      if (!active) return;
      if (caught instanceof Error && caught.message.includes("Authentication")) { setToken(null); router.replace("/app"); }
      else setError(caught instanceof Error ? caught.message : "Unable to load investigation");
    });
    return () => { active = false; };
  }, [id, router]);
  useEffect(() => {
    function closeDrawer(event: KeyboardEvent) { if (event.key === "Escape") setEvidenceOpen(false); }
    window.addEventListener("keydown", closeDrawer);
    return () => window.removeEventListener("keydown", closeDrawer);
  }, []);
  async function uploadFiles(files: FileList | File[]) { setBusy("upload"); setError(""); try { for (const file of Array.from(files)) await api.upload(id, file); await load(); setEvidenceOpen(false); } catch(caught) { setError(caught instanceof Error ? caught.message : "Upload failed"); } finally { setBusy(""); } }
  async function process() { setBusy("process"); setError(""); try { await api.process(id); await load(); } catch(caught) { setError(caught instanceof Error ? caught.message : "Processing failed"); } finally { setBusy(""); } }
  async function synchronize() { setBusy("sync"); setError(""); try { await api.synchronize(id); await load(); } catch(caught) { setError(caught instanceof Error ? caught.message : "Synchronization failed"); } finally { setBusy(""); } }
  if (!investigation) return <main className="loading-screen"><Mark/><LoaderCircle className="spin" size={24}/><p>{error || "Opening evidence room…"}</p></main>;
  const nav: Array<[Tab, string, React.ReactNode]> = [["reconstruct","Reconstruct",<Maximize2 key="r"/>],["timeline","Timeline",<Clock3 key="t"/>],["objects","Objects",<ScanSearch key="o"/>],["ask","Ask",<Bot key="a"/>],["graph","Graph",<Network key="g"/>]];
  return <main className="workspace-shell">
    <header className="workspace-header"><Link href="/app" aria-label="Back to investigations" className="back-link"><ArrowLeft size={17}/></Link><Mark/><div className="case-identity"><span>{investigation.incident_type}</span><strong>{investigation.title}</strong></div><div className="workspace-status"><span className={`status status-${investigation.status}`}>{investigation.status.replaceAll("_"," ")}</span><span className="case-date">{investigation.incident_date}</span></div></header>
    <aside className="workspace-sidebar"><nav aria-label="Investigation views">{nav.map(([value,label,icon]) => <button type="button" aria-current={tab===value?"page":undefined} className={tab===value?"active":""} onClick={()=>setTab(value)} key={value}>{icon}{label}</button>)}</nav><div className="sidebar-rule"><ShieldCheck size={16}/><span>Evidence integrity<br/><strong>verified</strong></span></div></aside>
    <section className="workspace-main">
      <header className="workbar"><div className="workbar-context"><span className="section-index">CASE / {id.slice(0,8).toUpperCase()}</span><p>{investigation.location}</p><span className="case-stats">{investigation.evidence?.length ?? 0} sources / {timeline?.event_count ?? 0} events</span></div><div className="work-actions"><button type="button" className="button button-quiet evidence-toggle" aria-expanded={evidenceOpen} onClick={()=>setEvidenceOpen(true)}><PanelRightOpen size={16}/> Sources <span>{investigation.evidence?.length ?? 0}</span></button><button type="button" className="button button-quiet" disabled={!!busy || !(investigation.evidence?.length)} onClick={process}>{busy==="process"?<LoaderCircle className="spin" size={16}/>:<RefreshCw size={16}/>} Process evidence</button><button type="button" className="button button-primary" disabled={!!busy || (investigation.evidence?.filter(e=>e.media_type.includes("video")).length??0)<2} onClick={synchronize}>{busy==="sync"?<LoaderCircle className="spin" size={16}/>:<GitFork size={16}/>} Auto-synchronize</button></div></header>
      {error && <div className="workspace-error"><CircleAlert size={17}/>{error}<button onClick={()=>setError("")}><X size={15}/></button></div>}
      <div className="workspace-content">
        <AnimatePresence mode="wait" initial={false}><motion.div key={tab} className="workspace-stage" initial={reduceMotion?false:{opacity:0,y:8}} animate={{opacity:1,y:0}} exit={reduceMotion?undefined:{opacity:0,y:-5}} transition={{duration:reduceMotion?0:0.2,ease:"easeOut"}}>
          {tab==="reconstruct"&&<Reconstructor id={id} investigation={investigation} timeline={timeline} jumpTime={jumpTime} onRefresh={load} onAddEvidence={()=>setEvidenceOpen(true)}/>} {tab==="timeline"&&<TimelineView id={id} timeline={timeline} onJump={time => { setJumpTime(time); setTab("reconstruct"); }} onRefresh={load}/>} {tab==="objects"&&<ObjectReview id={id} objects={objects} matches={matches} onRefresh={load}/>} {tab==="ask"&&<AskView id={id}/>} {tab==="graph"&&<GraphView graph={graph}/>}
        </motion.div></AnimatePresence>
      </div>
    </section>
    {evidenceOpen&&<button type="button" aria-label="Close source register" className="drawer-scrim" onClick={()=>setEvidenceOpen(false)}/>}<aside className={`evidence-drawer ${evidenceOpen?"open":""}`} aria-label="Source register"><header><div><span className="section-index">SOURCE REGISTER</span><h2>Evidence</h2></div><div className="drawer-heading-actions"><span className="evidence-count">{investigation.evidence?.length??0}</span><button type="button" aria-label="Close source register" className="drawer-close" onClick={()=>setEvidenceOpen(false)}><PanelRightClose size={17}/></button></div></header><input ref={fileInput} hidden multiple type="file" accept=".mp4,.mov,.jpg,.jpeg,.png,.txt,.pdf" onChange={(e:ChangeEvent<HTMLInputElement>)=>e.target.files&&uploadFiles(e.target.files)}/><button type="button" className={`drop-zone ${dragging?"dragging":""}`} onClick={()=>fileInput.current?.click()} onDragOver={e=>{e.preventDefault();setDragging(true)}} onDragLeave={()=>setDragging(false)} onDrop={e=>{e.preventDefault();setDragging(false);uploadFiles(e.dataTransfer.files)}}>{busy==="upload"?<LoaderCircle className="spin" size={21}/>:<Upload size={21}/>}<span>{busy==="upload"?"Securing upload…":"Add source files"}</span><small>MP4 · MOV · JPG · PNG · TXT · PDF</small></button><div className="evidence-list">{investigation.evidence?.map((item,index)=><article key={item.evidence_id}><span className="file-icon"><EvidenceIcon type={item.media_type}/></span><div><strong>{item.original_filename}</strong><small>{item.processing_status} · SHA {item.sha256.slice(0,7)}</small></div><span className="source-num">{String(index+1).padStart(2,"0")}</span></article>)}</div><footer><ShieldCheck size={15}/><span>Original files are immutable.<br/>Corrections are stored separately.</span></footer></aside>
  </main>;
}
