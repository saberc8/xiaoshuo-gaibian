export type Chapter = { id: string; index: number; title: string; word_count: number }
export type Book = {
  id: string; title: string; author: string; filename: string; created_at: string;
  is_demo: boolean; word_count: number; chapter_count: number; chapters: Chapter[];
  source_format?: 'txt' | 'epub'; source?: BookSource; source_sha256?: string;
}
export type Comparison = { chapter_id: string; title: string; paragraphs: { id: string; original: string }[]; layout_notes?: { paragraph_id: string; kind: string; text: string }[] }
export type SystemInfo = {
  mcp: { command: string; args: string[]; cwd: string; api_url: string };
  limits: { max_upload_mb: number }; storage: string; name: string; version: string;
}
export type Handoff = { project_id: string; revision: number; framework_revision: number; prompt: string }

export type BookSource = {
  title?: string; author?: string;
  language: string; edition: string; translator: string; source_url: string;
  rights_basis: 'unknown' | 'public_domain' | 'permission' | 'own_work'; territory: string; rights_note: string;
}
export type SourceCatalog = {
  works: { id: string; title: string; author: string; language: string; hook: string; direction: string; url: string; edition_note: string }[];
  presets: { id: string; name: string; description: string }[]; note: string; rights_reference: string;
}
export type AdaptationBrief = {
  idea: string; preset: string; target_language: string; naming_style: string; audience: string; tone: string;
  preserve: string[]; change: string[]; constraints: string[]; target_units: number; unit_characters: number;
  rewrite?: RewriteRequirements | null;
}
export type RewriteRequirements = { dimensions: string[]; narrative_strategy: string; ending_direction: string; avoid: string[] }
export type BaselineEvidence = { source: 'original' | 'adaptation'; chapter_id: string; paragraph_id: string; quote: string }
export type RewriteDesign = { diagnosis: string; narrative_strategy: string; ending: string; retained_elements: string[]; removed_elements: string[];
  changes: { dimension: string; before: string; after: string; reason: string; target_unit_ids: string[]; evidence: BaselineEvidence[] }[] }
export type RewriteAudit = { summary: string; passed: boolean; assessment: string; remaining_risks: string[]; unit_revisions: Record<string,number>; reviewed_chunk_ids: string[];
  comparisons: { dimension: string; unit_id: string; paragraph_id: string; quote: string; baseline: BaselineEvidence[]; judgment: string; passed: boolean }[] }
export type AdaptationFramework = {
  era: string; time_span: string; locations: string[]; historical_policy: string; naming_policy: string;
  characters: { id: string; source_names: string[]; target_name: string; target_aliases: string[]; role: string }[];
  setting_mappings: { source: string; target: string; rationale: string }[];
  plot_spine: string[]; allowed_inventions: string[]; prohibited_elements: string[]; forbidden_terms: string[]; scope_note: string;
}
export type StoryBible = {
  setting: string; tone: string; naming_strategy: string;
  characters: { id: string; source_names: string[]; target_name: string; target_aliases: string[]; role: string; motivation: string; arc: string; relationships: string[] }[];
  world_rules: { id: string; rule: string; cost: string; limit: string }[]; immutable_facts: string[];
  power_system: { realms: string[]; advancement: string; costs: string[]; limits: string[] } | null;
  system_mechanics: { name: string; trigger: string; abilities: string[]; costs: string[]; limits: string[] } | null;
}
export type AdaptationPlan = {
  logline: string; synopsis: string; bible: StoryBible;
  units: { id: string; title: string; source_chapter_ids: string[]; objective: string; conflict: string; turning_point: string; cliffhanger: string; beats: string[] }[];
  omitted_chapters: { chapter_id: string; reason: string }[];
  rewrite_design?: RewriteDesign | null;
}
export type AdaptationDraft = { title: string; paragraphs: string[]; summary: string; continuity_notes: string[]; change_notes: string[]; source_chunk_ids: string[]; source_paragraph_ids?: string[] }
export type AdaptationReview = {
  draft_revision: number; summary: string; passed: boolean; checks: Record<string, boolean>;
  findings: { category: string; severity: 'error' | 'warning' | 'info'; message: string }[];
}
export type AdaptationUnit = {
  id: string; title: string; draft_revision: number; continuity_stale: boolean; review: AdaptationReview | null;
  draft: (Omit<AdaptationDraft, 'paragraphs'> & { character_count: number; paragraph_count: number; aligned_paragraph_count?: number }) | null;
}
export type AdaptationRelease = { id: string; name: string; created_at: string; chapter_count: number; character_count: number; source_sha256: string }
export type Adaptation = {
  id: string; book_id: string; name: string; book_title: string; chapter_ids: string[]; brief: AdaptationBrief; source: BookSource;
  source_sha256: string; revision: number; status: 'framing' | 'analyzing' | 'planning' | 'writing' | 'reviewing' | 'auditing' | 'ready' | 'completed';
  mode?: 'adaptation' | 'translation' | 'deep_rewrite'; parent_mode?: 'adaptation' | 'translation' | 'deep_rewrite'; parent_project_id?: string; parent_name?: string; parent_release_sha256?: string;
  original_chapter_ids?: string[]; original_source_sha256?: string; reference_chapters?: Chapter[]; rewrite_audit?: RewriteAudit | null;
  framework_required?: boolean; framework: AdaptationFramework | null; framework_confirmed?: boolean; framework_revision?: number; framework_confirmed_at?: string | null;
  created_at: string; updated_at: string; completed_chunks: number; total_chunks: number; plan: AdaptationPlan | null;
  units: AdaptationUnit[]; release: AdaptationRelease | null;
  next_action: { stage: string; expected_revision: number; unit_id?: string; instruction: string };
  events: { revision: number; at: string; action: string; unit_id?: string }[];
}
