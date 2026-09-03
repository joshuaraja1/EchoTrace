export type User = { user_id: string; name: string; email: string };

export type Investigation = {
  investigation_id: string;
  title: string;
  incident_type: string;
  incident_date: string;
  approximate_time?: string | null;
  location: string;
  description?: string | null;
  status: string;
  created_at: string;
  evidence?: Evidence[];
};

export type Evidence = {
  evidence_id: string;
  investigation_id: string;
  original_filename: string;
  media_type: string;
  sha256: string;
  processing_status: string;
  metadata?: Record<string, unknown> | null;
  estimated_offset: number;
  manual_offset?: number | null;
  effective_offset: number;
  sync_confidence?: number | null;
  uploaded_at: string;
};

export type Citation = {
  evidence_id: string;
  source: string;
  local_timestamp_seconds: number;
  global_timestamp_seconds: number;
  frame_url?: string;
  confidence: number;
};

export type TimelineEvent = {
  event_id: string;
  event_type: string;
  global_timestamp_seconds: number;
  description: string;
  confidence: number;
  evidence_count: number;
  evidence: Citation[];
  review_status: string;
};

export type Timeline = {
  clock: string;
  source_count: number;
  event_count: number;
  events: TimelineEvent[];
};

export type ObjectMatch = {
  match_id: string;
  first: { evidence_id: string; source: string; track_id: number; class_name: string };
  second: { evidence_id: string; source: string; track_id: number; class_name: string };
  probability: number;
  review_status: string;
  signals: Record<string, number>;
};

export type EvidenceGraph = {
  nodes: Array<Record<string, string | number>>;
  edges: Array<{ source: string; target: string; relation: string; confidence: number }>;
};
