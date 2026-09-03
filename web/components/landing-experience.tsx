"use client";

import Link from "next/link";
import NextImage from "next/image";
import {
  ArrowDown,
  ArrowRight,
  AudioLines,
  Check,
  ChevronRight,
  CircleDot,
  Clock3,
  FileCheck2,
  FileText,
  Fingerprint,
  GitMerge,
  Image as ImageIcon,
  MessageSquareText,
  Play,
  ScanLine,
  ShieldCheck,
  Sparkles,
  Video,
} from "lucide-react";
import { motion, useReducedMotion } from "motion/react";
import { Mark } from "@/components/mark";
import styles from "./landing.module.css";

const evidence = [
  { label: "DASHCAM_FRONT.MP4", offset: "+00:00.00", confidence: "97%", icon: Video, tone: "orange", image: "/evidence-preview/dashcam-van.webp", alt: "Dashcam view of an orange delivery van approaching an intersection" },
  { label: "ROAD_CAMERA_04.MP4", offset: "+00:03.42", confidence: "91%", icon: Video, tone: "blue", image: "/evidence-preview/roadside-van.webp", alt: "Roadside camera view of an orange delivery van crossing an intersection" },
  { label: "WITNESS_PHONE.MP4", offset: "−00:01.18", confidence: "84%", icon: Video, tone: "green", image: "/evidence-preview/witness-van.webp", alt: "Witness phone view of an orange delivery van on an industrial road" },
];

const workflow = [
  {
    number: "01",
    title: "Ingest the record",
    copy: "Bring video, audio, images, PDFs, and witness notes into one investigation. Original files are fingerprinted so the source record stays intact.",
    tag: "Source integrity",
    icon: Fingerprint,
  },
  {
    number: "02",
    title: "Extract the signals",
    copy: "EchoTrace detects timestamps, audio landmarks, visual events, and metadata that can connect one perspective to another.",
    tag: "Multimodal analysis",
    icon: ScanLine,
  },
  {
    number: "03",
    title: "Synchronize the clocks",
    copy: "Candidate offsets become a shared timeline. Confidence and uncertainty remain visible, and an investigator can correct the alignment.",
    tag: "Human review",
    icon: GitMerge,
  },
  {
    number: "04",
    title: "Interrogate the evidence",
    copy: "Review events across perspectives and ask precise questions. Every answer points back to the files and moments that support it.",
    tag: "Cited answers",
    icon: MessageSquareText,
  },
];

function Reveal({ children, className = "", delay = 0 }: { children: React.ReactNode; className?: string; delay?: number }) {
  const reduceMotion = useReducedMotion();
  return (
    <motion.div
      className={className}
      initial={reduceMotion ? false : { opacity: 0, y: 28 }}
      whileInView={reduceMotion ? undefined : { opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.2 }}
      transition={{ duration: 0.65, delay, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </motion.div>
  );
}

function ReconstructionFigure() {
  const reduceMotion = useReducedMotion();
  return (
    <div className={styles.reconstruction} aria-label="Three evidence streams aligned to one shared incident clock">
      <div className={styles.figureHead}>
        <span><CircleDot size={13} /> RECONSTRUCTION / LIVE PREVIEW</span>
        <span className={styles.figureStatus}>SYNC RESOLVED <i /></span>
      </div>
      <div className={styles.streams}>
        {evidence.map(({ label, offset, confidence, icon: Icon, tone, image, alt }, index) => (
          <motion.div
            className={`${styles.stream} ${styles[tone]}`}
            key={label}
            initial={reduceMotion ? false : { opacity: 0, x: 34 }}
            animate={reduceMotion ? undefined : { opacity: 1, x: 0 }}
            transition={{ duration: 0.6, delay: 0.55 + index * 0.14 }}
          >
            <div className={styles.streamMeta}>
              <span><Icon size={13} /> CAM 0{index + 1}</span>
              <span>{confidence} MATCH</span>
            </div>
            <div className={styles.cameraScene}>
              <NextImage
                className={styles.sceneImage}
                src={image}
                alt={alt}
                fill
                priority={index === 0}
                sizes="(max-width: 780px) 32vw, (max-width: 1180px) 30vw, 16vw"
              />
              <span className={styles.sceneTime}>14:32:{11 + index}.084</span>
              <span className={styles.cameraReticle} aria-hidden="true" />
            </div>
            <div className={styles.waveform} aria-hidden="true">
              {[18, 42, 26, 66, 36, 78, 48, 28, 58, 82, 36, 54, 22, 70, 46, 30].map((height, bar) => (
                <i key={bar} style={{ height: `${height}%` }} />
              ))}
            </div>
            <div className={styles.streamFoot}><span>{label}</span><strong>{offset}</strong></div>
          </motion.div>
        ))}
      </div>
      <motion.div
        className={styles.playhead}
        initial={reduceMotion ? false : { left: "19%" }}
        animate={reduceMotion ? undefined : { left: ["19%", "73%", "56%"] }}
        transition={{ duration: 3.8, delay: 1.1, ease: "easeInOut" }}
      ><span /></motion.div>
      <div className={styles.sharedClock}>
        <span>SHARED INCIDENT TIME</span>
        <strong>00:14.82</strong>
        <span>± 0.31 SEC</span>
      </div>
    </div>
  );
}

export function LandingExperience() {
  const reduceMotion = useReducedMotion();

  return (
    <main className={styles.page}>
      <nav className={styles.nav} aria-label="Main navigation">
        <Link href="/" className={styles.brand}><Mark /></Link>
        <div className={styles.navLinks}>
          <a href="#problem">Why EchoTrace</a>
          <a href="#workflow">How it works</a>
          <a href="#trust">Evidence first</a>
        </div>
        <Link className={styles.navCta} href="/app">Open workspace <ArrowRight size={16} /></Link>
      </nav>

      <section className={styles.hero}>
        <div className={styles.heroGrid} aria-hidden="true" />
        <motion.div
          className={styles.heroCopy}
          initial={reduceMotion ? false : { opacity: 0, y: 24 }}
          animate={reduceMotion ? undefined : { opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
        >
          <p className={styles.kicker}><span /> EVIDENCE RECONSTRUCTION SYSTEM</p>
          <h1>The incident happened once. <em>The evidence starts everywhere.</em></h1>
          <p className={styles.heroLead}>EchoTrace aligns fragmented video, audio, images, and records into one inspectable timeline, with the source behind every conclusion.</p>
          <div className={styles.heroActions}>
            <Link className={styles.primaryAction} href="/app">Start a reconstruction <ArrowRight size={18} /></Link>
            <a className={styles.secondaryAction} href="#workflow"><Play size={15} fill="currentColor" /> See the method</a>
          </div>
          <div className={styles.proofLine}>
            <span><FileCheck2 size={15} /> Immutable originals</span>
            <span><ShieldCheck size={15} /> Investigator controlled</span>
            <span><GitMerge size={15} /> Cross-source alignment</span>
          </div>
        </motion.div>
        <motion.div
          className={styles.heroVisual}
          initial={reduceMotion ? false : { opacity: 0, x: 38 }}
          animate={reduceMotion ? undefined : { opacity: 1, x: 0 }}
          transition={{ duration: 0.8, delay: 0.2, ease: [0.22, 1, 0.36, 1] }}
        >
          <ReconstructionFigure />
        </motion.div>
        <a className={styles.scrollCue} href="#problem"><ArrowDown size={16} /> FOLLOW THE EVIDENCE</a>
      </section>

      <section className={styles.problem} id="problem">
        <Reveal className={styles.problemIntro}>
          <p className={styles.sectionLabel}>THE PROBLEM / 01</p>
          <h2>Five files. Five clocks. <span>One incident.</span></h2>
        </Reveal>
        <Reveal className={styles.problemBody} delay={0.08}>
          <p className={styles.lede}>When an incident happens, the truth is rarely inside a single file. It is split across devices, formats, timestamps, and points of view.</p>
          <p>Reviewers spend critical time renaming clips, scrubbing footage, comparing clocks, and rebuilding context by hand. The result can be slow, hard to audit, and easy to overstate.</p>
        </Reveal>
        <div className={styles.fragmentRail} aria-label="Example fragmented evidence sources">
          {[
            [Video, "CAB CAMERA", "14:32:11"],
            [Video, "ROAD CAMERA", "14:32:15"],
            [AudioLines, "WITNESS AUDIO", "14:32:10"],
            [ImageIcon, "SCENE PHOTO", "14:34:02"],
            [FileText, "DRIVER NOTE", "NO CLOCK"],
          ].map(([Icon, name, time], index) => {
            const SourceIcon = Icon as typeof Video;
            return <Reveal className={styles.fragment} delay={index * 0.06} key={name as string}><SourceIcon size={18} /><span>{name as string}</span><strong>{time as string}</strong></Reveal>;
          })}
        </div>
      </section>

      <section className={styles.transformation}>
        <div className={styles.sourceLedger}>
          <p className={styles.sectionLabel}>BEFORE</p>
          <h3>Fragments without shared context</h3>
          {evidence.map(({ label, offset, icon: Icon }) => (
            <div className={styles.ledgerRow} key={label}><Icon size={16} /><span>{label}</span><strong>{offset}</strong></div>
          ))}
          <div className={styles.ledgerRow}><FileText size={16} /><span>INCIDENT_REPORT.PDF</span><strong>UNTIMED</strong></div>
        </div>
        <div className={styles.engine}>
          <span className={styles.enginePulse}><Sparkles size={20} /></span>
          <p>ECHOTRACE ENGINE</p>
          <strong>Correlate signals<br />Preserve uncertainty<br />Expose provenance</strong>
          <ArrowRight size={28} />
        </div>
        <div className={styles.outcome}>
          <p className={styles.sectionLabel}>AFTER</p>
          <h3>A sequence you can inspect</h3>
          <div className={styles.miniTimeline}>
            <span /><i className={styles.eventOne} /><i className={styles.eventTwo} /><i className={styles.eventThree} />
          </div>
          <div className={styles.outcomeEvent}><time>00:09.40</time><span>Vehicle enters frame</span><b>2 sources</b></div>
          <div className={styles.outcomeEvent}><time>00:14.82</time><span>Impact signature</span><b>3 sources</b></div>
          <div className={styles.outcomeEvent}><time>00:21.06</time><span>Vehicle comes to rest</span><b>2 sources</b></div>
        </div>
      </section>

      <section className={styles.workflow} id="workflow">
        <div className={styles.workflowHeading}>
          <p className={styles.sectionLabel}>THE METHOD / 02</p>
          <h2>From raw files to a reviewable record.</h2>
          <p>EchoTrace supports the investigative workflow without replacing investigator judgment.</p>
        </div>
        <div className={styles.workflowSteps}>
          {workflow.map(({ number, title, copy, tag, icon: Icon }, index) => (
            <Reveal className={styles.workflowStep} delay={index * 0.05} key={number}>
              <span className={styles.stepNumber}>{number}</span>
              <span className={styles.stepIcon}><Icon size={23} /></span>
              <div><h3>{title}</h3><p>{copy}</p><small><Check size={12} /> {tag}</small></div>
              <ChevronRight className={styles.stepArrow} size={22} />
            </Reveal>
          ))}
        </div>
      </section>

      <section className={styles.trust} id="trust">
        <Reveal className={styles.trustHeading}>
          <p className={styles.sectionLabel}>EVIDENCE FIRST / 03</p>
          <h2>Answers should show their work.</h2>
          <p>Ask questions in plain language. EchoTrace retrieves the relevant moments and cites each source, so an answer can be checked instead of simply trusted.</p>
        </Reveal>
        <Reveal className={styles.answerDemo} delay={0.1}>
          <div className={styles.question}><span>INVESTIGATOR</span><p>What happened in the five seconds before impact?</p></div>
          <div className={styles.answer}>
            <div className={styles.answerLabel}><Sparkles size={15} /> ECHOTRACE / EVIDENCE-GROUNDED RESPONSE</div>
            <p>The delivery vehicle entered the intersection while the forward-facing camera shows the traffic signal changing. A horn is audible approximately 1.8 seconds before the impact signature.</p>
            <div className={styles.citations}>
              <button type="button"><Video size={13} /> Dashcam <b>00:09.40</b></button>
              <button type="button"><Video size={13} /> Dock cam <b>00:11.02</b></button>
              <button type="button"><AudioLines size={13} /> Witness audio <b>00:13.01</b></button>
            </div>
            <small>Illustrative reconstruction • Review source media before reaching a conclusion</small>
          </div>
        </Reveal>
      </section>

      <section className={styles.boundaries}>
        <Reveal className={styles.boundaryBlock}>
          <p className={styles.sectionLabel}>WHAT IT DOES</p>
          <h2>Reconstructs what the evidence shows.</h2>
          <ul><li><Check size={17} /> Aligns multiple perspectives</li><li><Check size={17} /> Makes uncertainty visible</li><li><Check size={17} /> Connects claims to source moments</li><li><Check size={17} /> Keeps the investigator in control</li></ul>
        </Reveal>
        <Reveal className={`${styles.boundaryBlock} ${styles.boundaryDark}`} delay={0.08}>
          <p className={styles.sectionLabel}>WHAT IT DOES NOT DO</p>
          <h2>It does not decide who is at fault.</h2>
          <p>EchoTrace organizes evidence and surfaces relationships. It does not replace legal judgment, make disciplinary decisions, or turn uncertainty into certainty.</p>
          <span><ShieldCheck size={19} /> Decision support, not decision authority</span>
        </Reveal>
      </section>

      <section className={styles.finalCta}>
        <div>
          <p className={styles.sectionLabel}>BUILD THE RECORD</p>
          <h2>Every perspective.<br />One accountable timeline.</h2>
        </div>
        <Link className={styles.finalAction} href="/app">Open EchoTrace <ArrowRight size={22} /></Link>
      </section>

      <footer className={styles.footer}>
        <Mark />
        <p>Evidence reconstruction for safer, clearer incident review.</p>
        <span><Clock3 size={14} /> BUILT FOR TRACEABILITY</span>
      </footer>
    </main>
  );
}
