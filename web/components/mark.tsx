import { AudioWaveform } from "lucide-react";

export function Mark({ compact = false }: { compact?: boolean }) {
  return (
    <span className="mark" aria-label="EchoTrace">
      <span className="mark-icon"><AudioWaveform size={18} strokeWidth={2.2} /></span>
      {!compact && <span>EchoTrace</span>}
    </span>
  );
}
