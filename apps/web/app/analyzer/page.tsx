"use client";

import React, { useEffect, useState } from "react";
import {
  AlertCircle,
  Check,
  CheckCircle2,
  FileSearch,
  Info,
  SlidersHorizontal,
  X,
} from "lucide-react";
import { apiFetch } from "@/lib/api";

interface ResumeSummary {
  id: string;
  title: string;
  latest_version_id: string | null;
  latest_version_number: number;
}

interface JobSummary {
  id: string;
  job_title: string;
  company_name: string | null;
}

interface RecommendationItem {
  id: string;
  category: string;
  original_text: string | null;
  suggested_text: string | null;
  rationale: string | null;
  evidence_reference: Record<string, unknown>;
  requires_user_confirmation: boolean;
  status: string;
}

interface RequirementRow {
  requirement: string;
  priority: string;
  match_state: "direct_match" | "possible_match" | "missing_evidence";
  evidence: { source?: string; excerpt?: string } | null;
  note: string;
}

interface AnalysisRecord {
  id: string;
  job_title: string | null;
  company_name: string | null;
  resume_title: string | null;
  status: string;
  overall_score: number | null;
  scoring_version: string;
  methodology_note: string | null;
  scoring_data: {
    alignment_band?: string;
    mandatory_cap_applied?: boolean;
    dimensions?: Record<string, { score: number; label: string }>;
    requirement_matrix?: RequirementRow[];
    missing_required_skills?: string[];
  };
  model_metadata: { provider?: string; model?: string };
  recommendations: RecommendationItem[];
  created_at: string;
}

const DEFAULT_WEIGHTS = {
  skills_relevance: 30,
  experience_relevance: 25,
  keyword_coverage: 15,
  education_certification: 10,
  achievement_evidence: 10,
  document_readability: 10,
};

export default function AnalyzerPage() {
  const [resumes, setResumes] = useState<ResumeSummary[]>([]);
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [analyses, setAnalyses] = useState<AnalysisRecord[]>([]);
  const [selectedResumeVer, setSelectedResumeVer] = useState("");
  const [selectedJob, setSelectedJob] = useState("");
  const [weights, setWeights] = useState(DEFAULT_WEIGHTS);
  const [showWeights, setShowWeights] = useState(false);
  const [active, setActive] = useState<AnalysisRecord | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let activeFlag = true;
    Promise.all([
      apiFetch<ResumeSummary[]>("/resumes"),
      apiFetch<JobSummary[]>("/jobs"),
      apiFetch<AnalysisRecord[]>("/analyses"),
    ])
      .then(([rList, jList, aList]) => {
        if (!activeFlag) return;
        setResumes(rList);
        setJobs(jList);
        setAnalyses(aList);
        const firstVer = rList.find((r) => r.latest_version_id)?.latest_version_id || "";
        if (firstVer) setSelectedResumeVer((prev) => prev || firstVer);
        if (jList[0]) setSelectedJob((prev) => prev || jList[0].id);
        if (aList[0]) setActive((prev) => prev || aList[0]);
      })
      .catch((err) => {
        if (activeFlag) setError(err instanceof Error ? err.message : "Failed to load analyzer");
      });
    return () => {
      activeFlag = false;
    };
  }, []);

  async function handleRunAnalysis(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedResumeVer || !selectedJob) return;
    setError(null);
    setRunning(true);
    try {
      const total = Object.values(weights).reduce((a, b) => a + b, 0) || 100;
      const normalized = {
        skills_relevance: weights.skills_relevance / total,
        experience_relevance: weights.experience_relevance / total,
        keyword_coverage: weights.keyword_coverage / total,
        education_certification: weights.education_certification / total,
        achievement_evidence: weights.achievement_evidence / total,
        document_readability: weights.document_readability / total,
      };
      const created = await apiFetch<AnalysisRecord>("/analyses", {
        method: "POST",
        body: JSON.stringify({
          resume_version_id: selectedResumeVer,
          job_description_id: selectedJob,
          weights: normalized,
        }),
      });
      setActive(created);
      setAnalyses((prev) => [created, ...prev]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setRunning(false);
    }
  }

  async function handleRecommendationAction(recId: string, status: "accepted" | "rejected") {
    if (!active) return;
    const updated = await apiFetch<RecommendationItem>(
      `/analyses/${active.id}/recommendations/${recId}`,
      {
        method: "PATCH",
        body: JSON.stringify({ status }),
      }
    );
    setActive({
      ...active,
      recommendations: active.recommendations.map((r) => (r.id === recId ? updated : r)),
    });
  }

  const dimensions = Object.entries(active?.scoring_data?.dimensions || {}).filter(
    ([key]) => key !== "document_readability"
  );

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">ATS Compatibility Engine</h1>
        <p className="mt-1 text-sm text-[#9AA8BD]">
          Deterministic, explainable compatibility estimates across 8 dimensions — separating
          missing evidence from missing capability.
        </p>
      </header>

      {error && (
        <div role="alert" className="rounded-xl border border-[#F16B76]/30 bg-[#F16B76]/10 p-3.5 text-sm text-[#F16B76]">
          {error}
        </div>
      )}

      {/* 3-Panel Input Workspace */}
      <form onSubmit={handleRunAnalysis} className="panel space-y-4 p-6">
        <div className="grid gap-4 md:grid-cols-3">
          <div>
            <label htmlFor="select-resume" className="mb-1.5 block text-xs font-medium text-[#9AA8BD]">
              1. Resume version
            </label>
            <select
              id="select-resume"
              value={selectedResumeVer}
              onChange={(e) => setSelectedResumeVer(e.target.value)}
              className="input-field"
              required
            >
              <option value="">Select resume…</option>
              {resumes
                .filter((r) => r.latest_version_id)
                .map((r) => (
                  <option key={r.id} value={r.latest_version_id || ""}>
                    {r.title} (v{r.latest_version_number})
                  </option>
                ))}
            </select>
          </div>

          <div>
            <label htmlFor="select-job" className="mb-1.5 block text-xs font-medium text-[#9AA8BD]">
              2. Target job description
            </label>
            <select
              id="select-job"
              value={selectedJob}
              onChange={(e) => setSelectedJob(e.target.value)}
              className="input-field"
              required
            >
              <option value="">Select saved job…</option>
              {jobs.map((j) => (
                <option key={j.id} value={j.id}>
                  {j.job_title} {j.company_name ? `— ${j.company_name}` : ""}
                </option>
              ))}
            </select>
          </div>

          <div className="flex flex-col justify-end gap-2">
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setShowWeights((p) => !p)}
                className="btn-secondary flex-1"
              >
                <SlidersHorizontal size={15} /> Weights
              </button>
              <button
                type="submit"
                disabled={running || !selectedResumeVer || !selectedJob}
                className="btn-primary flex-1"
              >
                <FileSearch size={15} /> {running ? "Scoring…" : "Run Analysis"}
              </button>
            </div>
          </div>
        </div>

        {showWeights && (
          <div className="grid gap-3 rounded-xl border border-white/10 bg-[#0B0F19] p-4 sm:grid-cols-3">
            {(Object.keys(weights) as Array<keyof typeof DEFAULT_WEIGHTS>).map((key) => (
              <label key={key} className="text-xs text-[#9AA8BD]">
                <span className="flex justify-between">
                  <span className="capitalize">{key.replace(/_/g, " ")}</span>
                  <span className="font-semibold text-white">{weights[key]}%</span>
                </span>
                <input
                  type="range"
                  min={0}
                  max={60}
                  value={weights[key]}
                  onChange={(e) => setWeights({ ...weights, [key]: Number(e.target.value) })}
                  className="mt-1 w-full accent-[#5B8CFF]"
                />
              </label>
            ))}
          </div>
        )}
      </form>

      {/* Past analyses pills */}
      {analyses.length > 1 && (
        <div className="flex flex-wrap gap-2">
          {analyses.slice(0, 6).map((a) => (
            <button
              key={a.id}
              type="button"
              onClick={() => setActive(a)}
              className={`rounded-xl border px-3 py-1.5 text-xs transition ${
                active?.id === a.id
                  ? "border-[#5B8CFF] bg-[#5B8CFF]/15 text-[#8AB0FF]"
                  : "border-white/10 bg-[#121A2A] text-[#9AA8BD] hover:text-white"
              }`}
            >
              {a.job_title} ({a.overall_score !== null ? `${Math.round(a.overall_score)}%` : a.status})
            </button>
          ))}
        </div>
      )}

      {/* Results View */}
      {active && (
        <div className="space-y-6">
          {/* Score Overview + Methodology Disclaimer */}
          <div className="grid gap-6 lg:grid-cols-12">
            <div className="panel flex flex-col justify-between p-6 lg:col-span-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-[#8AB0FF]">
                  Compatibility Estimate ({active.scoring_version})
                </p>
                <div className="mt-3 flex items-baseline gap-3">
                  <span className="text-5xl font-bold tracking-tight">
                    {active.overall_score !== null ? `${Math.round(active.overall_score)}%` : "—"}
                  </span>
                  <span className="rounded-lg bg-[#5B8CFF]/15 px-2.5 py-1 text-xs font-medium text-[#8AB0FF]">
                    {active.scoring_data?.alignment_band || "Evaluated"}
                  </span>
                </div>
                <p className="mt-2 text-sm font-medium">{active.job_title}</p>
                <p className="text-xs text-[#9AA8BD]">
                  Resume: {active.resume_title} · Recommendations: {active.model_metadata?.provider || "deterministic"}
                </p>
              </div>

              {active.scoring_data?.mandatory_cap_applied && (
                <div className="mt-4 rounded-xl border border-[#F5B94C]/30 bg-[#F5B94C]/10 p-3 text-xs text-[#F5B94C]">
                  Mandatory-skill guardrail applied: score capped because fewer than 35% of
                  required skills have direct evidence in this resume version.
                </div>
              )}

              <div className="mt-4 flex items-start gap-2 rounded-xl border border-white/10 bg-[#0B0F19] p-3 text-[11px] leading-4 text-[#9AA8BD]">
                <Info size={14} className="mt-0.5 shrink-0 text-[#5B8CFF]" />
                <span>
                  {active.methodology_note ||
                    "Platform compatibility estimate only — not a proprietary ATS vendor score."}
                </span>
              </div>
            </div>

            {/* 8-Dimension Breakdown */}
            <div className="panel p-6 lg:col-span-8">
              <h2 className="mb-4 text-sm font-semibold">8-Dimension Compatibility Breakdown</h2>
              <div className="grid gap-4 sm:grid-cols-2">
                {dimensions.map(([key, dim]) => (
                  <div key={key} className="space-y-1.5">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-slate-300">{dim.label}</span>
                      <span className="font-semibold text-white">{Math.round(dim.score)}%</span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-white/10">
                      <div
                        className="h-full rounded-full bg-[#5B8CFF]"
                        style={{ width: `${Math.min(100, Math.max(0, dim.score))}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Requirement-by-Requirement Evidence Matrix */}
          <div className="panel p-6">
            <h2 className="mb-4 text-sm font-semibold">Requirement-by-Requirement Evidence Matrix</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-white/10 text-[#9AA8BD]">
                  <tr>
                    <th className="pb-2.5 pr-4">Requirement</th>
                    <th className="pb-2.5 pr-4">Priority</th>
                    <th className="pb-2.5 pr-4">Status</th>
                    <th className="pb-2.5">Evidence / Explanation</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {(active.scoring_data?.requirement_matrix || []).map((row, idx) => (
                    <tr key={idx}>
                      <td className="py-3 pr-4 font-medium text-white">{row.requirement}</td>
                      <td className="py-3 pr-4 capitalize text-[#9AA8BD]">{row.priority}</td>
                      <td className="py-3 pr-4">
                        {row.match_state === "direct_match" ? (
                          <span className="inline-flex items-center gap-1 rounded-full bg-[#35C98A]/15 px-2.5 py-0.5 text-[#35C98A]">
                            <CheckCircle2 size={12} /> Direct match
                          </span>
                        ) : row.match_state === "possible_match" ? (
                          <span className="inline-flex items-center gap-1 rounded-full bg-[#F5B94C]/15 px-2.5 py-0.5 text-[#F5B94C]">
                            <AlertCircle size={12} /> Possible match
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 rounded-full bg-[#F16B76]/15 px-2.5 py-0.5 text-[#F16B76]">
                            <X size={12} /> Missing evidence
                          </span>
                        )}
                      </td>
                      <td className="py-3 text-[#9AA8BD]">
                        {row.evidence?.excerpt ? (
                          <span>
                            <strong className="text-slate-300">[{row.evidence.source}]</strong>{" "}
                            {row.evidence.excerpt}
                          </span>
                        ) : (
                          row.note
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Evidence-Backed Optimization Review */}
          <div className="panel p-6">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
              <div>
                <h2 className="text-sm font-semibold">Evidence-Backed Optimization Review</h2>
                <p className="text-xs text-[#9AA8BD]">
                  Suggestions are drafts — nothing modifies your verified profile without your
                  explicit approval.
                </p>
              </div>
            </div>

            <div className="space-y-3">
              {active.recommendations.map((rec) => (
                <div key={rec.id} className="rounded-xl border border-white/10 bg-[#0B0F19] p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded bg-white/10 px-2 py-0.5 text-[11px] font-medium uppercase text-slate-300">
                        {rec.category.replace(/_/g, " ")}
                      </span>
                      {rec.requires_user_confirmation && (
                        <span className="rounded bg-[#F5B94C]/15 px-2 py-0.5 text-[11px] font-medium text-[#F5B94C]">
                          Requires your confirmation (no silent insertion)
                        </span>
                      )}
                      <span className="text-[11px] capitalize text-[#9AA8BD]">Status: {rec.status}</span>
                    </div>
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => void handleRecommendationAction(rec.id, "accepted")}
                        className="inline-flex items-center gap-1 rounded-lg bg-[#35C98A]/15 px-2.5 py-1 text-xs font-medium text-[#35C98A] hover:bg-[#35C98A]/25"
                      >
                        <Check size={13} /> Accept
                      </button>
                      <button
                        type="button"
                        onClick={() => void handleRecommendationAction(rec.id, "rejected")}
                        className="inline-flex items-center gap-1 rounded-lg bg-[#F16B76]/15 px-2.5 py-1 text-xs font-medium text-[#F16B76] hover:bg-[#F16B76]/25"
                      >
                        <X size={13} /> Reject
                      </button>
                    </div>
                  </div>
                  {rec.original_text && (
                    <p className="mt-2.5 rounded-lg bg-white/[0.03] p-2.5 text-xs text-slate-400">
                      <strong className="text-slate-300">Original:</strong> {rec.original_text}
                    </p>
                  )}
                  <p className="mt-2 text-sm text-slate-100">{rec.suggested_text}</p>
                  {rec.rationale && <p className="mt-1 text-xs text-[#9AA8BD]">{rec.rationale}</p>}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
