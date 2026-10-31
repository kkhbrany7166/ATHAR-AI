// Types mirror backend/athar/serializers.py.

export type Role = "professor" | "student";
export interface UserBrief { id: number; name: string; role: Role; is_synthetic: boolean }

export type Judgment = "met" | "partial" | "not_met" | "unclear" | "ai_unavailable" | "ai_failed";
export type Source = "tests" | "ai" | "professor" | "rules" | "baseline";

export interface Health { status: string; llm: { provider: string; model: string; configured: boolean } }

export interface GradingRun {
  id: number; status: "queued" | "running" | "done" | "failed"; stage: string; total: number;
  tests_done: number; ai_done: number; ai_failed: number;
  ai_status: "" | "used" | "baseline" | "unavailable" | "partial" | "failed" | "not_needed"; ai_provider: string;
  error: string; started_at: string | null; finished_at: string | null;
}

export interface CourseSummary { id: number; code: string; title: string; term: string; is_synthetic: boolean; student_count: number; assignment_count: number }

export interface CourseDetail {
  id: number; code: string; title: string; term: string; description: string; is_synthetic: boolean; student_count: number;
  objectives: { id: number; code: string; title: string; description: string; source: string; misconceptions: { code: string; title: string }[] }[];
  assignments: {
    id: number; title: string; kind: string; conditions: string; status: string; due_at: string | null; submitted: number; enrolled: number; targeted?: boolean;
    latest_run: GradingRun | null; insights: { id: number; kind: string; title: string; student_count: number }[];
  }[];
  materials: { id: number; title: string; kind: string; chars: number }[];
}

export interface Criterion { id: number; code: string; title: string; description: string; method: "tests" | "explanation"; max_points: number; objective_id: number | null; objective_code: string | null }
export interface TestCaseT { id: number; name: string; function: string; args: unknown[]; expected: unknown; hidden: boolean; criterion_id: number; probes: { misconception: string; on: string; error_types?: string[] }[] }

export interface AssignmentDetail {
  id: number; course_id: number; course_code: string; title: string; prompt: string; explanation_prompt: string;
  kind: string; conditions: string; ai_policy: string; status: string; due_at: string | null; reference_solution: string;
  criteria: Criterion[]; tests: TestCaseT[];
  misconceptions: { code: string; title: string; description: string; objective_id: number }[];
  latest_run: GradingRun | null;
  stats: { enrolled: number; submitted: number; graded: number; reviewed: number; published: number; needs_review: number };
}

export interface CriterionState { criterion_id: number; code: string; judgment: Judgment | null; source: Source | null; points: number | null; max_points: number; needs_review: boolean }

export interface SubmissionRow {
  id: number; student: UserBrief; attempt: number; submitted_at: string; grade_status: string; is_synthetic: boolean;
  criteria: CriterionState[]; total: number | null; max_total: number; includes_unconfirmed_ai: boolean;
  needs_review: boolean; misconceptions: string[]; has_ai_disclosure: boolean;
}

export interface Evidence {
  id: number; criterion_id: number; source: Source; judgment: Judgment; points: number | null; rationale: string; quotes: string[];
  confidence: string; needs_review: boolean; review_reasons: string[]; model: string; created_at: string;
}

export interface SubmissionDetail {
  id: number; assignment_id: number; assignment_title: string; student: UserBrief; attempt: number; submitted_at: string;
  conditions: string; code: string; explanation: string; ai_use_disclosure: string; is_synthetic: boolean; grade_status: string;
  total: number | null; max_total: number; includes_unconfirmed_ai: boolean; publish_blockers: string[];
  criteria: (Criterion & { state: CriterionState; evidence: Evidence[] })[];
  tests: { id: number; test_case_id: number; name: string; hidden: boolean; criterion_id: number; status: string; actual: string; expected: string; error_type: string; error_message: string }[];
  misconceptions: { id: number; code: string; source: Source; detail: string; quote: string; confidence: string; test_result_id: number | null }[];
  reading: null | {
    reader: string; source: string; prompt_version: string; abstained: boolean; abstain_reason: string; answer_type: string; code_issue: string;
    summary: string; objectives: { objective_code: string; status: string; quote: string }[]; contradictions: string[]; missing_evidence: string[];
    rejected_ideas: { code: string; quote: string; reasoning: string }[]; validation_notes: string[];
  };
}

export interface InsightEvidence {
  counts: { students: number; submitted: number; enrolled: number; tests_only: number; explanation_only: number; both: number; working_code_confused_reasoning: number };
  misconception: { code: string; title: string; description: string };
  why_it_matters: string;
  criteria: { criterion_id: number; code: string; title: string; method: string; linked: boolean; group_met: number; group_judged: number; others_met: number; others_judged: number }[];
  tests: { test_case_id: number; name: string; hidden: boolean; group_passed: number; group_total: number; others_passed: number; others_total: number; common_failures: { kind: string; count: number }[] }[];
  examples: { submission_id: number; student_id: number; student_name: string; is_synthetic: boolean; quote: string; test_evidence: string; sources: string[] }[];
  conditions: { kind: string; conditions: string; ai_policy: string };
  missing: { kind: string; count: number; text: string }[];
  contradictions: { kind: string; count: number; submission_ids: number[]; text: string }[];
  submission_ids: number[]; student_ids: number[];
  by_source: { tests_only: number[]; explanation_only: number[]; both: number[] };
  threshold: number;
}

export interface SupportEvidence {
  struggling: { submission_id: number; student_id: number; student_name: string; criteria_not_met: string[] }[];
  not_submitted: { student_id: number; student_name: string }[];
}

export interface Insight {
  id: number; assignment_id: number; run_id: number; kind: "misconception" | "needs_support";
  objective: { id: number; code: string; title: string } | null; misconception_code: string; title: string; summary: string;
  student_count: number; evidence: InsightEvidence | SupportEvidence; status: string; created_at: string;
}

export interface InsightDetail extends Insight {
  assignment: { id: number; title: string; course_id: number; course_code: string };
  run: GradingRun | null;
}

// Student
export interface StudentHome {
  student: UserBrief;
  tasks: { id: number; title: string; status: string; course_id: number; outcome: Outcome | null; assigned_at: string }[];
  courses: { id: number; code: string; title: string; term: string; professor: string;
    assignments: { id: number; title: string; kind: string; conditions: string; status: string; due_at: string | null; my_status: string }[] }[];
}

export interface StudentAssignment {
  assignment: { id: number; course_id: number; course_code: string; title: string; prompt: string; explanation_prompt: string; kind: string;
    conditions: string; ai_policy: string; starter_code: string; status: string; due_at: string | null;
    criteria: { code: string; title: string; description: string; max_points: number }[]; visible_tests: string[] };
  submissions: { id: number; attempt: number; submitted_at: string; code: string; explanation: string; status: string;
    feedback: null | { total: number | null; max_total: number;
      criteria: { code: string; title: string; max_points: number; judgment?: string; points?: number | null; comment?: string }[];
      tests: { name: string; passed: boolean }[] } }[];
}

// Interventions
export interface ItemValidation { valid: boolean; problems: string[]; reference_passed: number; total: number; misconception_caught_by: string[]; method: string }
export interface ItemTest { name: string; function: string; args: unknown[]; expected: unknown; criterion: string; hidden: boolean; probes: { misconception: string }[] }
export interface Item {
  id: number; key: string; role: string; title: string; prompt: string; explanation_prompt: string; starter_code: string; hint_count: number;
  source: string; tests: ItemTest[]; validation: ItemValidation; misconception_code: string; reference_solution: string; misconception_solution: string; hints: string[];
}
export type Outcome = "demonstrated" | "still_developing" | "insufficient_evidence";
export interface InterventionStudent {
  student_id: number; name: string; is_synthetic: boolean; is_demo_persona: boolean;
  before: { source: string; detail: string; quote: string }[];
  task: null | { id: number; status: string; is_simulated: boolean; hints_revealed: number; practice_attempts: number; has_initial: boolean; has_revised: boolean; has_reflection: boolean };
  verification: null | { outcome: Outcome; reasons: string[]; tests_passed: number; tests_total: number; submission_id: number; explanation_judgment: string; explanation_reader: string; rule_version: string; at: string };
}
export type InterventionKind = "concept_practice" | "debugging" | "explain_reasoning";
export interface Intervention {
  kind: InterventionKind;
  id: number; status: "draft" | "approved" | "active" | "completed" | "rejected"; title: string; misconception_code: string;
  course_id: number; course_code: string; assignment: { id: number; title: string }; insight_id: number | null;
  explanation: string; explanation_source: string; professor_note: string;
  practice_item: Item | null; followup_item: Item | null; followup_options: Item[]; followup_assignment_id: number | null;
  target_student_ids: number[]; students: InterventionStudent[]; execution_error: string;
  created_at: string; approved_at: string | null; executed_at: string | null; closed_at: string | null;
  progress: { targets: number; delivered: number; started: number; verified: number; simulated: number } & Record<Outcome, number>;
  recommendations: string[];
}

export interface StudentTask {
  kind: InterventionKind; my_original_code: string;
  id: number; status: string; title: string; course_code: string; from_assignment: string; my_earlier_evidence: string[];
  explanation: string; explanation_source: string; initial_reasoning: string; revised_reasoning: string; reflection: string;
  practice: null | { id: number; title: string; prompt: string; explanation_prompt: string; starter_code: string; hint_count: number; tests: string[] };
  hints: string[];
  practice_attempts: { id: number; passed: number; total: number; code: string; at: string; results: { name: string; status: string; actual: string; error_type: string; error_message: string }[] }[];
  messages: { id: number; role: string; content: string; source: string }[];
  check: null | { assignment_id: number; title: string; prompt: string; explanation_prompt: string; starter_code: string; conditions: string; ai_policy: string; visible_tests: string[] };
  results: { outcome: Outcome; label: string; reasons: string[]; tests_passed: number; tests_total: number; at: string }[];
  intervention_status: string;
}

export interface PlanGroup {
  category: string; misconception_code: string; label: string; action: string; action_label: string; action_why: string; draftable: boolean;
  students: { student_id: number; name: string; is_synthetic: boolean; submission_id: number | null; evidence: string[]; in_intervention: number | null }[];
}
export interface Plan { assignment_id: number; reader: string; reader_status: string; groups: PlanGroup[]; rules: string }
