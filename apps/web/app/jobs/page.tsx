"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowUpRight, Plus, Save, Trash2 } from "lucide-react";
import { apiFetch } from "@/lib/api";

interface ExtractedRequirements {
  seniority?: string;
  min_years_experience?: number | null;
  required_skills?: string[];
  preferred_skills?: string[];
  soft_skills?: string[];
  education_requirements?: string[];
  certifications?: string[];
  responsibilities?: string[];
}

interface JobRecord {
  id: string;
  company_name: string | null;
  job_title: string;
  description: string;
  extracted_requirements: ExtractedRequirements;
  created_at: string;
}

export default function JobsPage() {
  const [jobs, setJobs] = useState<JobRecord[]>([]);
  const [selected, setSelected] = useState<JobRecord | null>(null);
  const [jobTitle, setJobTitle] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [description, setDescription] = useState("");
  const [reqSkillsEdit, setReqSkillsEdit] = useState("");
  const [prefSkillsEdit, setPrefSkillsEdit] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const loadJobs = useCallback(async () => {
    const data = await apiFetch<JobRecord[]>("/jobs");
    setJobs(data);
    return data;
  }, []);

  const selectJob = useCallback((job: JobRecord) => {
    setSelected(job);
    setReqSkillsEdit((job.extracted_requirements?.required_skills || []).join(", "));
    setPrefSkillsEdit((job.extracted_requirements?.preferred_skills || []).join(", "));
  }, []);

  useEffect(() => {
    let activeFlag = true;
    apiFetch<JobRecord[]>("/jobs")
      .then((list) => {
        if (!activeFlag) return;
        setJobs(list);
        if (list.length > 0) {
          setSelected(list[0]);
          setReqSkillsEdit((list[0].extracted_requirements?.required_skills || []).join(", "));
          setPrefSkillsEdit((list[0].extracted_requirements?.preferred_skills || []).join(", "));
        }
      })
      .catch((err) => {
        if (activeFlag) setError(err instanceof Error ? err.message : "Failed to load jobs");
      });
    return () => {
      activeFlag = false;
    };
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setMsg(null);
    setBusy(true);
    try {
      const created = await apiFetch<JobRecord>("/jobs", {
        method: "POST",
        body: JSON.stringify({
          job_title: jobTitle,
          company_name: companyName || undefined,
          description,
        }),
      });
      setJobTitle("");
      setCompanyName("");
      setDescription("");
      await loadJobs();
      selectJob(created);
      setMsg("Job description saved and requirements extracted.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save job");
    } finally {
      setBusy(false);
    }
  }

  async function handleSaveRequirements() {
    if (!selected) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await apiFetch<JobRecord>(`/jobs/${selected.id}`, {
        method: "PUT",
        body: JSON.stringify({
          extracted_requirements: {
            ...selected.extracted_requirements,
            required_skills: reqSkillsEdit
              .split(",")
              .map((s) => s.trim())
              .filter(Boolean),
            preferred_skills: prefSkillsEdit
              .split(",")
              .map((s) => s.trim())
              .filter(Boolean),
          },
        }),
      });
      await loadJobs();
      selectJob(updated);
      setMsg("Extracted requirements updated. These criteria will be used in ATS scoring.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(id: string) {
    await apiFetch(`/jobs/${id}`, { method: "DELETE" });
    const next = await loadJobs();
    if (selected?.id === id) {
      setSelected(next[0] || null);
      if (next[0]) selectJob(next[0]);
    }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Job Intelligence</h1>
        <p className="mt-1 text-sm text-[#9AA8BD]">
          Paste any job description to separate explicit required vs. preferred skills, review
          extracted qualifications, and correct criteria before running ATS compatibility scoring.
        </p>
      </header>

      {error && (
        <div role="alert" className="rounded-xl border border-[#F16B76]/30 bg-[#F16B76]/10 p-3.5 text-sm text-[#F16B76]">
          {error}
        </div>
      )}
      {msg && (
        <div role="status" className="rounded-xl border border-[#35C98A]/30 bg-[#35C98A]/10 p-3.5 text-sm text-[#35C98A]">
          {msg}
        </div>
      )}

      <form onSubmit={handleCreate} className="panel space-y-4 p-6">
        <h2 className="text-sm font-semibold">Add &amp; Parse Job Description</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          <input
            required
            placeholder="Job title (e.g. Cybersecurity Analyst)"
            value={jobTitle}
            onChange={(e) => setJobTitle(e.target.value)}
            className="input-field"
          />
          <input
            placeholder="Company name (optional)"
            value={companyName}
            onChange={(e) => setCompanyName(e.target.value)}
            className="input-field"
          />
        </div>
        <textarea
          required
          minLength={20}
          rows={5}
          placeholder="Paste the full job description here (include Required and Preferred sections if available)…"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className="input-field"
        />
        <button type="submit" disabled={busy} className="btn-primary">
          <Plus size={16} /> Save &amp; Extract Requirements
        </button>
      </form>

      <div className="grid gap-6 lg:grid-cols-12">
        <div className="panel space-y-2 p-4 lg:col-span-4">
          <h2 className="px-2 text-xs font-semibold uppercase tracking-wider text-[#9AA8BD]">
            Saved jobs ({jobs.length})
          </h2>
          {jobs.map((job) => (
            <div
              key={job.id}
              className={`flex items-center justify-between rounded-xl border p-3 ${
                selected?.id === job.id
                  ? "border-[#5B8CFF]/50 bg-[#5B8CFF]/10"
                  : "border-white/5 bg-[#0B0F19]"
              }`}
            >
              <button type="button" onClick={() => selectJob(job)} className="min-w-0 flex-1 text-left">
                <p className="truncate text-sm font-medium">{job.job_title}</p>
                <p className="mt-0.5 text-xs text-[#9AA8BD]">
                  {job.company_name || "Unspecified company"} · {job.extracted_requirements?.seniority || "Role"}
                </p>
              </button>
              <button
                type="button"
                onClick={() => void handleDelete(job.id)}
                aria-label={`Delete ${job.job_title}`}
                className="ml-2 rounded-lg p-1.5 text-slate-500 hover:bg-[#F16B76]/15 hover:text-[#F16B76]"
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>

        <div className="panel space-y-5 p-6 lg:col-span-8">
          {selected ? (
            <>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold">{selected.job_title}</h2>
                  <p className="text-xs text-[#9AA8BD]">
                    {selected.company_name || "Company not specified"} · Seniority (inferred):{" "}
                    {selected.extracted_requirements?.seniority || "Mid-level"}
                    {selected.extracted_requirements?.min_years_experience
                      ? ` · ${selected.extracted_requirements.min_years_experience}+ yrs`
                      : ""}
                  </p>
                </div>
                <Link href={`/analyzer?jobId=${selected.id}`} className="btn-primary">
                  Score against CV <ArrowUpRight size={15} />
                </Link>
              </div>

              <div className="space-y-3 rounded-xl border border-white/10 bg-[#0B0F19] p-4">
                <p className="text-xs font-semibold text-[#8AB0FF]">
                  Review &amp; edit extracted requirements before scoring
                </p>
                <div>
                  <label className="mb-1 block text-xs text-[#9AA8BD]">
                    Required skills (comma-separated)
                  </label>
                  <input
                    value={reqSkillsEdit}
                    onChange={(e) => setReqSkillsEdit(e.target.value)}
                    className="input-field"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-xs text-[#9AA8BD]">
                    Preferred / Nice-to-have skills (comma-separated)
                  </label>
                  <input
                    value={prefSkillsEdit}
                    onChange={(e) => setPrefSkillsEdit(e.target.value)}
                    className="input-field"
                  />
                </div>
                <button type="button" onClick={() => void handleSaveRequirements()} disabled={busy} className="btn-secondary">
                  <Save size={14} /> Save corrected requirements
                </button>
              </div>

              {(selected.extracted_requirements?.certifications || []).length > 0 && (
                <div>
                  <h3 className="mb-2 text-xs font-semibold uppercase text-[#9AA8BD]">Certifications</h3>
                  <div className="flex flex-wrap gap-2">
                    {selected.extracted_requirements.certifications?.map((c) => (
                      <span key={c} className="rounded-lg bg-[#5B8CFF]/15 px-2.5 py-1 text-xs text-[#8AB0FF]">
                        {c}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {(selected.extracted_requirements?.responsibilities || []).length > 0 && (
                <div>
                  <h3 className="mb-2 text-xs font-semibold uppercase text-[#9AA8BD]">Key responsibilities</h3>
                  <ul className="list-disc space-y-1 pl-5 text-xs leading-5 text-slate-300">
                    {selected.extracted_requirements.responsibilities?.slice(0, 8).map((r, i) => (
                      <li key={i}>{r}</li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          ) : (
            <p className="text-sm text-[#9AA8BD]">Select or add a job description to inspect extracted criteria.</p>
          )}
        </div>
      </div>
    </div>
  );
}
