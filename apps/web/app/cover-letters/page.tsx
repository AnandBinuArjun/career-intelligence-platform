"use client";

import React, { useEffect, useState } from "react";
import { CheckCircle2, Download, FileText, Save, Sparkles, Trash2 } from "lucide-react";
import { apiDownload, apiFetch } from "@/lib/api";

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

interface CoverLetterRecord {
  id: string;
  title: string | null;
  tone: string;
  content: string;
  evidence_references: Array<{ claim?: string; source?: string; excerpt?: string; verified?: boolean }>;
  model_metadata: { provider?: string; model?: string };
  version: number;
  updated_at: string;
}

export default function CoverLettersPage() {
  const [resumes, setResumes] = useState<ResumeSummary[]>([]);
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [letters, setLetters] = useState<CoverLetterRecord[]>([]);
  const [selected, setSelected] = useState<CoverLetterRecord | null>(null);
  const [editContent, setEditContent] = useState("");
  const [resumeVerId, setResumeVerId] = useState("");
  const [jobId, setJobId] = useState("");
  const [tone, setTone] = useState<"professional" | "concise" | "formal" | "executive">("professional");
  const [length, setLength] = useState<"short" | "medium" | "detailed">("medium");
  const [customNotes, setCustomNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let activeFlag = true;
    Promise.all([
      apiFetch<ResumeSummary[]>("/resumes"),
      apiFetch<JobSummary[]>("/jobs"),
      apiFetch<CoverLetterRecord[]>("/cover-letters"),
    ])
      .then(([rList, jList, cList]) => {
        if (!activeFlag) return;
        setResumes(rList);
        setJobs(jList);
        setLetters(cList);
        const firstVer = rList.find((r) => r.latest_version_id)?.latest_version_id || "";
        if (firstVer) setResumeVerId((prev) => prev || firstVer);
        if (jList[0]) setJobId((prev) => prev || jList[0].id);
        if (cList[0]) {
          setSelected((prev) => prev || cList[0]);
          setEditContent((prev) => prev || cList[0].content);
        }
      })
      .catch((err) => {
        if (activeFlag) setError(err instanceof Error ? err.message : "Failed to load studio");
      });
    return () => {
      activeFlag = false;
    };
  }, []);

  async function handleGenerate(e: React.FormEvent) {
    e.preventDefault();
    if (!resumeVerId || !jobId) return;
    setBusy(true);
    setError(null);
    setMsg(null);
    try {
      const created = await apiFetch<CoverLetterRecord>("/cover-letters/generate", {
        method: "POST",
        body: JSON.stringify({
          resume_version_id: resumeVerId,
          job_description_id: jobId,
          tone,
          length,
          custom_notes: customNotes || undefined,
        }),
      });
      setLetters((prev) => [created, ...prev]);
      setSelected(created);
      setEditContent(created.content);
      setCustomNotes("");
      setMsg("Evidence-grounded cover letter draft generated.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleSave() {
    if (!selected) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await apiFetch<CoverLetterRecord>(`/cover-letters/${selected.id}`, {
        method: "PUT",
        body: JSON.stringify({ content: editContent }),
      });
      setSelected(updated);
      setLetters((prev) => prev.map((l) => (l.id === updated.id ? updated : l)));
      setMsg(`Saved edits (v${updated.version}).`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(id: string) {
    await apiFetch(`/cover-letters/${id}`, { method: "DELETE" });
    const next = letters.filter((l) => l.id !== id);
    setLetters(next);
    if (selected?.id === id) {
      setSelected(next[0] || null);
      setEditContent(next[0]?.content || "");
    }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Cover Letter Studio</h1>
        <p className="mt-1 text-sm text-[#9AA8BD]">
          Generate editable, evidence-grounded cover letters tied to a specific resume version and
          job description, then export clean PDF, DOCX, or TXT files.
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

      <form onSubmit={handleGenerate} className="panel space-y-4 p-6">
        <div className="grid gap-3 md:grid-cols-4">
          <select value={resumeVerId} onChange={(e) => setResumeVerId(e.target.value)} className="input-field" required>
            <option value="">Select resume version…</option>
            {resumes
              .filter((r) => r.latest_version_id)
              .map((r) => (
                <option key={r.id} value={r.latest_version_id || ""}>
                  {r.title} (v{r.latest_version_number})
                </option>
              ))}
          </select>
          <select value={jobId} onChange={(e) => setJobId(e.target.value)} className="input-field" required>
            <option value="">Select job…</option>
            {jobs.map((j) => (
              <option key={j.id} value={j.id}>
                {j.job_title} {j.company_name ? `— ${j.company_name}` : ""}
              </option>
            ))}
          </select>
          <select
            value={tone}
            onChange={(e) => setTone(e.target.value as "professional" | "concise" | "formal" | "executive")}
            className="input-field"
          >
            <option value="professional">Tone: Professional</option>
            <option value="concise">Tone: Concise</option>
            <option value="formal">Tone: Formal</option>
            <option value="executive">Tone: Executive</option>
          </select>
          <select
            value={length}
            onChange={(e) => setLength(e.target.value as "short" | "medium" | "detailed")}
            className="input-field"
          >
            <option value="short">Length: Short</option>
            <option value="medium">Length: Medium</option>
            <option value="detailed">Length: Detailed</option>
          </select>
        </div>

        <input
          placeholder="Optional personal motivation or context to include (never fabricated)"
          value={customNotes}
          onChange={(e) => setCustomNotes(e.target.value)}
          className="input-field"
        />

        <button type="submit" disabled={busy || !resumeVerId || !jobId} className="btn-primary">
          <Sparkles size={15} /> {busy ? "Generating…" : "Generate Grounded Draft"}
        </button>
      </form>

      <div className="grid gap-6 lg:grid-cols-12">
        <div className="panel space-y-2 p-4 lg:col-span-3">
          <h2 className="px-2 text-xs font-semibold uppercase tracking-wider text-[#9AA8BD]">
            Saved drafts ({letters.length})
          </h2>
          {letters.map((l) => (
            <div
              key={l.id}
              className={`flex items-center justify-between rounded-xl border p-3 ${
                selected?.id === l.id
                  ? "border-[#5B8CFF]/50 bg-[#5B8CFF]/10"
                  : "border-white/5 bg-[#0B0F19]"
              }`}
            >
              <button
                type="button"
                onClick={() => {
                  setSelected(l);
                  setEditContent(l.content);
                }}
                className="min-w-0 flex-1 text-left"
              >
                <p className="truncate text-xs font-medium">{l.title || "Cover Letter"}</p>
                <p className="mt-0.5 text-[11px] text-[#9AA8BD]">
                  v{l.version} · {l.tone}
                </p>
              </button>
              <button
                type="button"
                onClick={() => void handleDelete(l.id)}
                aria-label="Delete cover letter"
                className="ml-2 rounded p-1 text-slate-500 hover:text-[#F16B76]"
              >
                <Trash2 size={13} />
              </button>
            </div>
          ))}
        </div>

        <div className="space-y-6 lg:col-span-9">
          {selected ? (
            <>
              <div className="panel space-y-4 p-6">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <h2 className="text-base font-semibold">{selected.title}</h2>
                    <p className="text-xs text-[#9AA8BD]">
                      Version {selected.version} · Tone: {selected.tone} · Provider:{" "}
                      {selected.model_metadata?.provider || "deterministic"}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() =>
                        void apiDownload(
                          `/cover-letters/${selected.id}/export?format=pdf`,
                          `${selected.title || "cover-letter"}.pdf`
                        )
                      }
                      className="btn-secondary py-2 text-xs"
                    >
                      <Download size={13} /> PDF
                    </button>
                    <button
                      type="button"
                      onClick={() =>
                        void apiDownload(
                          `/cover-letters/${selected.id}/export?format=docx`,
                          `${selected.title || "cover-letter"}.docx`
                        )
                      }
                      className="btn-secondary py-2 text-xs"
                    >
                      <Download size={13} /> DOCX
                    </button>
                    <button
                      type="button"
                      onClick={() =>
                        void apiDownload(
                          `/cover-letters/${selected.id}/export?format=txt`,
                          `${selected.title || "cover-letter"}.txt`
                        )
                      }
                      className="btn-secondary py-2 text-xs"
                    >
                      <FileText size={13} /> TXT
                    </button>
                    <button type="button" onClick={() => void handleSave()} disabled={busy} className="btn-primary py-2 text-xs">
                      <Save size={13} /> Save edits
                    </button>
                  </div>
                </div>

                <textarea
                  rows={14}
                  value={editContent}
                  onChange={(e) => setEditContent(e.target.value)}
                  className="input-field font-sans leading-relaxed"
                />
              </div>

              {/* Evidence Provenance Panel */}
              <div className="panel p-5">
                <h3 className="mb-3 text-sm font-semibold">Evidence Citations</h3>
                <ul className="space-y-2 text-xs">
                  {selected.evidence_references.map((ev, i) => (
                    <li
                      key={i}
                      className="flex items-start gap-2 rounded-xl border border-white/10 bg-[#0B0F19] p-3"
                    >
                      <CheckCircle2 size={14} className="mt-0.5 shrink-0 text-[#35C98A]" />
                      <div>
                        <p className="font-medium text-slate-200">{ev.claim}</p>
                        <p className="mt-0.5 text-[#9AA8BD]">
                          Source: {ev.source} {ev.excerpt ? `— "${ev.excerpt}"` : ""}
                        </p>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            </>
          ) : (
            <div className="panel p-10 text-center text-sm text-[#9AA8BD]">
              Select a resume version and target job above to generate an evidence-grounded cover letter.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
