"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowUpRight,
  BriefcaseBusiness,
  CheckCircle2,
  Circle,
  FileSearch,
  FileUser,
  ShieldCheck,
  Sparkles,
  Target,
} from "lucide-react";
import { apiFetch } from "@/lib/api";

interface DashboardSummary {
  profile_completeness_pct: number;
  resumes_count: number;
  jobs_count: number;
  analyses_count: number;
  cover_letters_count: number;
  active_applications_count: number;
  upcoming_interviews_count: number;
  application_pipeline: Record<string, number>;
  recent_analyses: Array<{
    id: string;
    job_title: string;
    company_name: string | null;
    status: string;
    overall_score: number | null;
    scoring_version: string;
    created_at: string;
  }>;
  ai_routing_status: {
    mode: string;
    user_preference: string;
    external_ai_enabled: boolean;
    local_model: string;
    local_first: boolean;
  };
}

function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

export default function OverviewPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<DashboardSummary>("/dashboard/summary")
      .then(setSummary)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load dashboard"));
  }, []);

  const onboardingSteps = [
    {
      label: "Complete verified candidate profile",
      done: (summary?.profile_completeness_pct ?? 0) >= 50,
      href: "/settings",
    },
    {
      label: "Upload or create your first resume",
      done: (summary?.resumes_count ?? 0) > 0,
      href: "/resumes",
    },
    {
      label: "Save a target job description",
      done: (summary?.jobs_count ?? 0) > 0,
      href: "/jobs",
    },
    {
      label: "Run an explainable ATS compatibility analysis",
      done: (summary?.analyses_count ?? 0) > 0,
      href: "/analyzer",
    },
  ];

  return (
    <div className="mx-auto max-w-6xl space-y-8">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-sm text-[#9AA8BD]">Career workspace</p>
          <h1 className="mt-1 text-3xl font-semibold tracking-tight">{getGreeting()}</h1>
        </div>
        <div className="flex items-center gap-3">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-[#35C98A]/30 bg-[#35C98A]/10 px-3 py-1.5 text-xs font-medium text-[#35C98A]">
            <ShieldCheck size={14} aria-hidden="true" />
            {summary?.ai_routing_status.external_ai_enabled
              ? `AI: ${summary.ai_routing_status.user_preference}`
              : `Local AI (${summary?.ai_routing_status.local_model ?? "ollama"})`}
          </span>
          <Link href="/analyzer" className="btn-primary">
            Analyze a job <ArrowUpRight size={16} aria-hidden="true" />
          </Link>
        </div>
      </header>

      {error && (
        <div role="alert" className="rounded-xl border border-[#F16B76]/30 bg-[#F16B76]/10 p-4 text-sm text-[#F16B76]">
          {error}
        </div>
      )}

      {/* Hero action card */}
      <div className="rounded-3xl border border-blue-400/20 bg-gradient-to-br from-[#5B8CFF]/15 via-[#121A2A] to-[#121A2A] p-7 md:p-8">
        <p className="text-xs font-semibold tracking-wider text-[#8AB0FF]">CAREER INTELLIGENCE</p>
        <h2 className="mt-2 max-w-2xl text-2xl font-semibold leading-tight md:text-3xl">
          Make every application transparent, evidence-backed, and intentional.
        </h2>
        <p className="mt-2.5 max-w-2xl text-sm leading-6 text-[#9AA8BD]">
          Understand explicit job requirements, evaluate alignment across 8 explainable dimensions,
          and refine your CV without fabricating skills or credentials.
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link href="/analyzer" className="btn-primary">
            <FileSearch size={16} aria-hidden="true" /> Start ATS analysis
          </Link>
          <Link href="/resumes" className="btn-secondary">
            <FileUser size={16} aria-hidden="true" /> Upload or edit resume
          </Link>
          <Link href="/jobs" className="btn-secondary">
            <Target size={16} aria-hidden="true" /> Add job description
          </Link>
        </div>
      </div>

      {/* KPI Metrics */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="panel p-5">
          <p className="text-xs font-medium text-[#9AA8BD]">Verified profile</p>
          <p className="mt-2 text-2xl font-semibold">{summary?.profile_completeness_pct ?? 0}%</p>
          <p className="mt-1 text-xs text-slate-500">Source of truth for evidence</p>
        </div>
        <div className="panel p-5">
          <p className="text-xs font-medium text-[#9AA8BD]">Saved resumes</p>
          <p className="mt-2 text-2xl font-semibold">{summary?.resumes_count ?? 0}</p>
          <p className="mt-1 text-xs text-slate-500">Private storage + versions</p>
        </div>
        <div className="panel p-5">
          <p className="text-xs font-medium text-[#9AA8BD]">Job analyses</p>
          <p className="mt-2 text-2xl font-semibold">{summary?.analyses_count ?? 0}</p>
          <p className="mt-1 text-xs text-slate-500">{summary?.jobs_count ?? 0} saved job specs</p>
        </div>
        <div className="panel p-5">
          <p className="text-xs font-medium text-[#9AA8BD]">Active applications</p>
          <p className="mt-2 text-2xl font-semibold">{summary?.active_applications_count ?? 0}</p>
          <p className="mt-1 text-xs text-slate-500">
            {summary?.upcoming_interviews_count ?? 0} upcoming interviews
          </p>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Recent Analyses */}
        <div className="panel p-6 lg:col-span-2">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-base font-semibold">Recent compatibility analyses</h3>
            <Link href="/analyzer" className="text-xs font-medium text-[#5B8CFF] hover:underline">
              Open analyzer
            </Link>
          </div>
          {summary && summary.recent_analyses.length > 0 ? (
            <div className="space-y-3">
              {summary.recent_analyses.map((item) => (
                <Link
                  key={item.id}
                  href={`/analyzer?analysisId=${item.id}`}
                  className="flex items-center justify-between rounded-xl border border-white/10 bg-[#0B0F19] p-4 transition hover:border-[#5B8CFF]/40"
                >
                  <div>
                    <p className="font-medium text-sm">{item.job_title}</p>
                    <p className="mt-0.5 text-xs text-[#9AA8BD]">
                      {item.company_name || "Target company"} · Scoring {item.scoring_version}
                    </p>
                  </div>
                  <div className="text-right">
                    <span className="inline-block rounded-lg bg-[#5B8CFF]/15 px-2.5 py-1 text-sm font-semibold text-[#8AB0FF]">
                      {item.overall_score !== null ? `${Math.round(item.overall_score)}%` : item.status}
                    </span>
                    <p className="mt-1 text-[11px] text-slate-500">Platform estimate</p>
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-white/10 p-6 text-center">
              <p className="text-sm text-[#9AA8BD]">No compatibility analyses yet.</p>
              <p className="mt-1 text-xs text-slate-500">
                Upload a resume and paste a job description to see an 8-dimension evidence breakdown.
              </p>
              <Link href="/analyzer" className="btn-secondary mt-4">
                Run your first analysis
              </Link>
            </div>
          )}
        </div>

        {/* Guided Checklist + Pipeline */}
        <div className="space-y-6">
          <div className="panel p-6">
            <h3 className="mb-3 text-base font-semibold">Workspace setup</h3>
            <ul className="space-y-2.5">
              {onboardingSteps.map((step) => (
                <li key={step.label}>
                  <Link
                    href={step.href}
                    className="flex items-center gap-2.5 rounded-lg p-1.5 text-sm transition hover:bg-white/5"
                  >
                    {step.done ? (
                      <CheckCircle2 size={16} className="shrink-0 text-[#35C98A]" aria-hidden="true" />
                    ) : (
                      <Circle size={16} className="shrink-0 text-slate-500" aria-hidden="true" />
                    )}
                    <span className={step.done ? "text-slate-400 line-through" : "text-slate-200"}>
                      {step.label}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          <div className="panel p-6">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-base font-semibold">Quick links</h3>
            </div>
            <div className="grid grid-cols-2 gap-2.5 text-xs">
              <Link href="/cover-letters" className="panel-elevated flex items-center gap-2 p-3 hover:border-[#5B8CFF]/40">
                <Sparkles size={15} className="text-[#5B8CFF]" /> Cover Letters
              </Link>
              <Link href="/applications" className="panel-elevated flex items-center gap-2 p-3 hover:border-[#5B8CFF]/40">
                <BriefcaseBusiness size={15} className="text-[#35C98A]" /> Applications
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
