"use client";

import React, { useEffect, useState } from "react";
import { BookOpen, Compass, MessageSquareQuote, Sparkles } from "lucide-react";
import { apiFetch } from "@/lib/api";

interface CareerOverview {
  target_roles: string[];
  verified_skills_count: number;
  analyzed_jobs_count: number;
  top_skill_gaps: Array<{ skill: string; gap_weight: number; status: string }>;
  learning_plan: Array<{
    skill: string;
    priority: string;
    demand_count: number;
    recommended_step: string;
    evidence_goal: string;
  }>;
  interview_questions: Array<{
    category: string;
    topic: string;
    question: string;
    evidence_tip: string;
  }>;
}

interface JobSummary {
  id: string;
  job_title: string;
  company_name: string | null;
}

export default function CareerPage() {
  const [overview, setOverview] = useState<CareerOverview | null>(null);
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [selectedJob, setSelectedJob] = useState("");
  const [prepQuestions, setPrepQuestions] = useState<CareerOverview["interview_questions"]>([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    Promise.all([
      apiFetch<CareerOverview>("/career/overview"),
      apiFetch<JobSummary[]>("/jobs"),
    ]).then(([ov, jList]) => {
      setOverview(ov);
      setPrepQuestions(ov.interview_questions);
      setJobs(jList);
      if (jList[0]) setSelectedJob(jList[0].id);
    });
  }, []);

  async function handleGeneratePrep() {
    if (!selectedJob) return;
    setBusy(true);
    try {
      const data = await apiFetch<{ questions: CareerOverview["interview_questions"] }>(
        "/career/interview-prep",
        {
          method: "POST",
          body: JSON.stringify({ job_description_id: selectedJob }),
        }
      );
      setPrepQuestions(data.questions);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Career Development</h1>
        <p className="mt-1 text-sm text-[#9AA8BD]">
          Aggregated skill gaps across your analyzed jobs, verifiable learning plans, and tailored
          interview questions grounded in your evidence.
        </p>
      </header>

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="panel p-5">
          <p className="text-xs text-[#9AA8BD]">Verified skills</p>
          <p className="mt-1.5 text-2xl font-semibold">{overview?.verified_skills_count ?? 0}</p>
        </div>
        <div className="panel p-5">
          <p className="text-xs text-[#9AA8BD]">Analyzed jobs</p>
          <p className="mt-1.5 text-2xl font-semibold">{overview?.analyzed_jobs_count ?? 0}</p>
        </div>
        <div className="panel p-5">
          <p className="text-xs text-[#9AA8BD]">Priority skill gaps</p>
          <p className="mt-1.5 text-2xl font-semibold">{overview?.top_skill_gaps.length ?? 0}</p>
        </div>
      </div>

      {/* Skill Gaps & Learning Plan */}
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="panel p-6">
          <div className="mb-4 flex items-center gap-2 text-sm font-semibold">
            <Compass size={16} className="text-[#F5B94C]" /> Highest-Leverage Skill Gaps
          </div>
          {overview && overview.top_skill_gaps.length > 0 ? (
            <div className="space-y-3">
              {overview.top_skill_gaps.map((g) => (
                <div
                  key={g.skill}
                  className="flex items-center justify-between rounded-xl border border-white/10 bg-[#0B0F19] px-4 py-3 text-sm"
                >
                  <span className="font-medium">{g.skill}</span>
                  <span className="rounded-full bg-[#F5B94C]/15 px-2.5 py-0.5 text-xs text-[#F5B94C]">
                    Demand weight: {g.gap_weight}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-[#9AA8BD]">
              Run at least one ATS Compatibility Analysis to aggregate recurring skill gaps across
              target jobs.
            </p>
          )}
        </div>

        <div className="panel p-6">
          <div className="mb-4 flex items-center gap-2 text-sm font-semibold">
            <BookOpen size={16} className="text-[#35C98A]" /> Verifiable Learning Roadmap
          </div>
          {overview && overview.learning_plan.length > 0 ? (
            <div className="space-y-3">
              {overview.learning_plan.map((item) => (
                <div key={item.skill} className="rounded-xl border border-white/10 bg-[#0B0F19] p-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-semibold">{item.skill}</span>
                    <span className="rounded bg-[#5B8CFF]/15 px-2 py-0.5 text-[11px] text-[#8AB0FF]">
                      {item.priority} priority
                    </span>
                  </div>
                  <p className="mt-1.5 text-xs leading-5 text-slate-300">{item.recommended_step}</p>
                  <p className="mt-1 text-[11px] text-[#35C98A]">Goal: {item.evidence_goal}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-[#9AA8BD]">
              Your learning plan populates automatically once missing skills are identified.
            </p>
          )}
        </div>
      </div>

      {/* Interview Prep Studio */}
      <div className="panel space-y-4 p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-sm font-semibold">
            <MessageSquareQuote size={16} className="text-[#5B8CFF]" /> Evidence-Grounded Interview
            Preparation
          </div>
          <div className="flex flex-wrap gap-2">
            <select
              value={selectedJob}
              onChange={(e) => setSelectedJob(e.target.value)}
              className="rounded-xl border border-white/15 bg-[#0B0F19] px-3 py-2 text-xs text-slate-200"
            >
              <option value="">General prep</option>
              {jobs.map((j) => (
                <option key={j.id} value={j.id}>
                  {j.job_title} {j.company_name ? `— ${j.company_name}` : ""}
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={() => void handleGeneratePrep()}
              disabled={busy || !selectedJob}
              className="btn-primary py-2 text-xs"
            >
              <Sparkles size={14} /> Tailor for role
            </button>
          </div>
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          {prepQuestions.map((q, i) => (
            <div key={i} className="rounded-xl border border-white/10 bg-[#0B0F19] p-4">
              <div className="flex items-center justify-between text-[11px]">
                <span className="rounded bg-[#5B8CFF]/15 px-2 py-0.5 font-medium text-[#8AB0FF]">
                  {q.category}
                </span>
                <span className="text-[#9AA8BD]">{q.topic}</span>
              </div>
              <p className="mt-2.5 text-sm font-medium text-slate-100">{q.question}</p>
              <p className="mt-2 text-xs leading-5 text-[#9AA8BD]">{q.evidence_tip}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
