"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  AlertTriangle,
  Download,
  FilePlus2,
  History,
  RotateCcw,
  Save,
  Trash2,
  Upload,
} from "lucide-react";
import { apiDownload, apiFetch } from "@/lib/api";

interface ResumeSummary {
  id: string;
  title: string;
  file_type: string | null;
  upload_status: string;
  parse_status: string;
  latest_version_id: string | null;
  latest_version_number: number;
  updated_at: string;
}

interface ResumeVersion {
  id: string;
  resume_id: string;
  version_number: number;
  content: ResumeContent;
  source: string;
  created_at: string;
}

interface ResumeExperience {
  job_title: string;
  employer: string;
  period: string;
  bullets: string[];
}

interface ResumeEducation {
  institution: string;
  qualification: string;
  period?: string;
}

interface ResumeContent {
  full_name?: string;
  professional_title?: string;
  contact?: { email?: string; phone?: string; location?: string };
  summary?: string;
  skills?: string[];
  experiences?: ResumeExperience[];
  education?: ResumeEducation[];
  certifications?: Array<{ name: string } | string>;
  extraction_confidence?: number;
  diagnostics?: {
    readability_score?: number;
    page_count?: number;
    word_count?: number;
    detected_sections?: string[];
    warnings?: string[];
  };
}

interface ResumeDetail extends ResumeSummary {
  file_sha256: string | null;
  parsed_content: ResumeContent;
  versions: ResumeVersion[];
}

export default function ResumesPage() {
  const [resumes, setResumes] = useState<ResumeSummary[]>([]);
  const [selected, setSelected] = useState<ResumeDetail | null>(null);
  const [editor, setEditor] = useState<ResumeContent>({});
  const [skillsInput, setSkillsInput] = useState("");
  const [uploadTitle, setUploadTitle] = useState("");
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [newTitle, setNewTitle] = useState("");
  const [exportTemplate, setExportTemplate] = useState<"classic" | "modern" | "compact">("classic");
  const [statusMsg, setStatusMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const loadList = useCallback(async () => {
    const data = await apiFetch<ResumeSummary[]>("/resumes");
    setResumes(data);
    return data;
  }, []);

  const openResume = useCallback(async (id: string) => {
    const detail = await apiFetch<ResumeDetail>(`/resumes/${id}`);
    setSelected(detail);
    const activeContent = detail.versions[0]?.content || detail.parsed_content || {};
    setEditor(activeContent);
    setSkillsInput((activeContent.skills || []).join(", "));
  }, []);

  useEffect(() => {
    let activeFlag = true;
    apiFetch<ResumeSummary[]>("/resumes")
      .then(async (list) => {
        if (!activeFlag) return;
        setResumes(list);
        if (list.length > 0) {
          const detail = await apiFetch<ResumeDetail>(`/resumes/${list[0].id}`);
          if (!activeFlag) return;
          setSelected(detail);
          const activeContent = detail.versions[0]?.content || detail.parsed_content || {};
          setEditor(activeContent);
          setSkillsInput((activeContent.skills || []).join(", "));
        }
      })
      .catch((err) => {
        if (activeFlag) setError(err instanceof Error ? err.message : "Failed to load resumes");
      });
    return () => {
      activeFlag = false;
    };
  }, []);

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!uploadFile) return;
    setError(null);
    setStatusMsg(null);
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("title", uploadTitle.trim() || uploadFile.name.replace(/\.[^.]+$/, ""));
      fd.append("auto_parse", "true");
      fd.append("file", uploadFile);
      const created = await apiFetch<ResumeDetail>("/resumes/upload", {
        method: "POST",
        body: fd,
      });
      setUploadTitle("");
      setUploadFile(null);
      await loadList();
      setSelected(created);
      const activeContent = created.versions[0]?.content || created.parsed_content || {};
      setEditor(activeContent);
      setSkillsInput((activeContent.skills || []).join(", "));
      setStatusMsg("Resume uploaded, validated (SHA-256), and parsed into version 1.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleCreateBlank(e: React.FormEvent) {
    e.preventDefault();
    if (!newTitle.trim()) return;
    setError(null);
    setBusy(true);
    try {
      const created = await apiFetch<ResumeDetail>("/resumes", {
        method: "POST",
        body: JSON.stringify({
          title: newTitle.trim(),
          content: {
            full_name: "",
            professional_title: "",
            summary: "",
            skills: [],
            experiences: [],
            education: [],
            certifications: [],
          },
        }),
      });
      setNewTitle("");
      await loadList();
      setSelected(created);
      setEditor(created.versions[0]?.content || {});
      setSkillsInput("");
      setStatusMsg("Structured resume created.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Creation failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleSaveVersion() {
    if (!selected) return;
    setError(null);
    setBusy(true);
    try {
      const nextContent: ResumeContent = {
        ...editor,
        skills: skillsInput
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
      };
      await apiFetch(`/resumes/${selected.id}/versions`, {
        method: "POST",
        body: JSON.stringify({ content: nextContent, source: "user" }),
      });
      await loadList();
      await openResume(selected.id);
      setStatusMsg("Saved new immutable resume version.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save version");
    } finally {
      setBusy(false);
    }
  }

  async function handleRestoreVersion(versionId: string) {
    if (!selected) return;
    setBusy(true);
    try {
      await apiFetch(`/resumes/${selected.id}/versions/${versionId}/restore`, { method: "POST" });
      await openResume(selected.id);
      setStatusMsg("Restored snapshot as a new immutable version.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Restore failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(id: string) {
    setBusy(true);
    try {
      await apiFetch(`/resumes/${id}`, { method: "DELETE" });
      const next = await loadList();
      if (selected?.id === id) {
        setSelected(null);
        if (next.length > 0) await openResume(next[0].id);
      }
      setStatusMsg("Resume and private storage object deleted.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setBusy(false);
    }
  }

  function addExperienceRow() {
    setEditor((prev) => ({
      ...prev,
      experiences: [
        ...(prev.experiences || []),
        { job_title: "", employer: "", period: "", bullets: [""] },
      ],
    }));
  }

  function addEducationRow() {
    setEditor((prev) => ({
      ...prev,
      education: [...(prev.education || []), { institution: "", qualification: "", period: "" }],
    }));
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">My Resumes</h1>
          <p className="mt-1 text-sm text-[#9AA8BD]">
            Upload PDF, DOCX, or TXT resumes into private storage, edit structured sections, track
            immutable versions, and export watermark-free ATS-safe documents.
          </p>
        </div>
      </header>

      {error && (
        <div role="alert" className="rounded-xl border border-[#F16B76]/30 bg-[#F16B76]/10 p-3.5 text-sm text-[#F16B76]">
          {error}
        </div>
      )}
      {statusMsg && (
        <div role="status" className="rounded-xl border border-[#35C98A]/30 bg-[#35C98A]/10 p-3.5 text-sm text-[#35C98A]">
          {statusMsg}
        </div>
      )}

      {/* Upload & Create Row */}
      <div className="grid gap-4 md:grid-cols-2">
        <form onSubmit={handleUpload} className="panel space-y-3 p-5">
          <div className="flex items-center gap-2 text-sm font-semibold">
            <Upload size={16} className="text-[#5B8CFF]" /> Upload existing CV (PDF, DOCX, TXT)
          </div>
          <input
            type="text"
            placeholder="Resume title (e.g. Cybersecurity Analyst CV)"
            value={uploadTitle}
            onChange={(e) => setUploadTitle(e.target.value)}
            className="input-field"
          />
          <input
            type="file"
            accept=".pdf,.docx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
            onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
            className="block w-full text-xs text-[#9AA8BD] file:mr-3 file:rounded-lg file:border-0 file:bg-[#5B8CFF]/15 file:px-3 file:py-2 file:text-xs file:font-medium file:text-[#8AB0FF]"
          />
          <button type="submit" disabled={!uploadFile || busy} className="btn-primary">
            Upload &amp; Parse CV
          </button>
        </form>

        <form onSubmit={handleCreateBlank} className="panel flex flex-col justify-between space-y-3 p-5">
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-sm font-semibold">
              <FilePlus2 size={16} className="text-[#35C98A]" /> Create structured resume from scratch
            </div>
            <input
              type="text"
              required
              placeholder="New resume title (e.g. Platform Engineer 2026)"
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              className="input-field"
            />
          </div>
          <div>
            <button type="submit" disabled={busy} className="btn-secondary">
              Create structured CV
            </button>
          </div>
        </form>
      </div>

      {/* Library + Editor */}
      <div className="grid gap-6 lg:grid-cols-12">
        <div className="panel space-y-2 p-4 lg:col-span-3">
          <h2 className="px-2 text-xs font-semibold uppercase tracking-wider text-[#9AA8BD]">
            Resume library ({resumes.length})
          </h2>
          {resumes.length === 0 ? (
            <p className="px-2 py-4 text-xs text-slate-500">No resumes yet. Upload or create one above.</p>
          ) : (
            resumes.map((r) => (
              <div
                key={r.id}
                className={`flex items-center justify-between rounded-xl border p-3 transition ${
                  selected?.id === r.id
                    ? "border-[#5B8CFF]/50 bg-[#5B8CFF]/10"
                    : "border-white/5 bg-[#0B0F19] hover:border-white/15"
                }`}
              >
                <button
                  type="button"
                  onClick={() => void openResume(r.id)}
                  className="min-w-0 flex-1 text-left"
                >
                  <p className="truncate text-sm font-medium">{r.title}</p>
                  <p className="mt-0.5 text-[11px] text-[#9AA8BD]">
                    v{r.latest_version_number} · {r.parse_status}
                  </p>
                </button>
                <button
                  type="button"
                  onClick={() => void handleDelete(r.id)}
                  aria-label={`Delete ${r.title}`}
                  className="ml-2 rounded-lg p-1.5 text-slate-500 hover:bg-[#F16B76]/15 hover:text-[#F16B76]"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))
          )}
        </div>

        <div className="space-y-6 lg:col-span-9">
          {selected ? (
            <>
              {/* Editor Toolbar */}
              <div className="panel flex flex-wrap items-center justify-between gap-3 p-4">
                <div>
                  <h2 className="text-base font-semibold">{selected.title}</h2>
                  <p className="text-xs text-[#9AA8BD]">
                    Latest version: v{selected.latest_version_number}
                    {selected.file_sha256 ? ` · SHA-256 ${selected.file_sha256.slice(0, 12)}…` : ""}
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <select
                    aria-label="Export PDF template"
                    value={exportTemplate}
                    onChange={(e) => setExportTemplate(e.target.value as "classic" | "modern" | "compact")}
                    className="rounded-xl border border-white/15 bg-[#0B0F19] px-3 py-2 text-xs text-slate-200"
                  >
                    <option value="classic">Classic template</option>
                    <option value="modern">Modern accent</option>
                    <option value="compact">Compact single-col</option>
                  </select>
                  <button
                    type="button"
                    onClick={() =>
                      void apiDownload(
                        `/resumes/${selected.id}/export?format=pdf&template=${exportTemplate}`,
                        `${selected.title}.pdf`
                      )
                    }
                    className="btn-secondary"
                  >
                    <Download size={14} /> PDF
                  </button>
                  <button
                    type="button"
                    onClick={() =>
                      void apiDownload(
                        `/resumes/${selected.id}/export?format=docx`,
                        `${selected.title}.docx`
                      )
                    }
                    className="btn-secondary"
                  >
                    <Download size={14} /> DOCX
                  </button>
                  <button type="button" onClick={() => void handleSaveVersion()} disabled={busy} className="btn-primary">
                    <Save size={14} /> Save new version
                  </button>
                </div>
              </div>

              {/* Parsing & ATS Readability Diagnostics */}
              {editor.diagnostics && (
                <div className="panel p-5">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <h3 className="text-sm font-semibold">ATS Readability &amp; Extraction Diagnostics</h3>
                    <div className="flex gap-3 text-xs">
                      <span className="rounded-lg bg-[#35C98A]/15 px-2.5 py-1 text-[#35C98A]">
                        Readability: {editor.diagnostics.readability_score ?? 100}%
                      </span>
                      {editor.extraction_confidence !== undefined && (
                        <span className="rounded-lg bg-[#5B8CFF]/15 px-2.5 py-1 text-[#8AB0FF]">
                          Extraction confidence: {Math.round(editor.extraction_confidence * 100)}%
                        </span>
                      )}
                    </div>
                  </div>
                  {(editor.diagnostics.warnings || []).length > 0 && (
                    <ul className="mt-3 space-y-1.5 text-xs text-[#F5B94C]">
                      {editor.diagnostics.warnings?.map((w, i) => (
                        <li key={i} className="flex items-start gap-2">
                          <AlertTriangle size={14} className="mt-0.5 shrink-0" />
                          <span>{w}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}

              {/* Structured Sections Editor */}
              <div className="panel space-y-5 p-6">
                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <label className="mb-1 block text-xs font-medium text-[#9AA8BD]">Full name</label>
                    <input
                      value={editor.full_name || ""}
                      onChange={(e) => setEditor({ ...editor, full_name: e.target.value })}
                      className="input-field"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-xs font-medium text-[#9AA8BD]">Professional title</label>
                    <input
                      value={editor.professional_title || ""}
                      onChange={(e) => setEditor({ ...editor, professional_title: e.target.value })}
                      className="input-field"
                    />
                  </div>
                </div>

                <div>
                  <label className="mb-1 block text-xs font-medium text-[#9AA8BD]">Professional summary</label>
                  <textarea
                    rows={3}
                    value={editor.summary || ""}
                    onChange={(e) => setEditor({ ...editor, summary: e.target.value })}
                    className="input-field"
                  />
                </div>

                <div>
                  <label className="mb-1 block text-xs font-medium text-[#9AA8BD]">
                    Skills (comma-separated, normalized by ATS engine)
                  </label>
                  <input
                    value={skillsInput}
                    onChange={(e) => setSkillsInput(e.target.value)}
                    placeholder="Python, PostgreSQL, FastAPI, Docker, SIEM"
                    className="input-field"
                  />
                </div>

                {/* Experience */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-semibold">Experience</h3>
                    <button type="button" onClick={addExperienceRow} className="btn-secondary py-1.5 text-xs">
                      + Add role
                    </button>
                  </div>
                  {(editor.experiences || []).map((exp, idx) => (
                    <div key={idx} className="space-y-2.5 rounded-xl border border-white/10 bg-[#0B0F19] p-4">
                      <div className="grid gap-2.5 sm:grid-cols-3">
                        <input
                          placeholder="Job title"
                          value={exp.job_title || ""}
                          onChange={(e) => {
                            const next = [...(editor.experiences || [])];
                            next[idx] = { ...exp, job_title: e.target.value };
                            setEditor({ ...editor, experiences: next });
                          }}
                          className="input-field"
                        />
                        <input
                          placeholder="Employer"
                          value={exp.employer || ""}
                          onChange={(e) => {
                            const next = [...(editor.experiences || [])];
                            next[idx] = { ...exp, employer: e.target.value };
                            setEditor({ ...editor, experiences: next });
                          }}
                          className="input-field"
                        />
                        <input
                          placeholder="Period (e.g. 2022 - Present)"
                          value={exp.period || ""}
                          onChange={(e) => {
                            const next = [...(editor.experiences || [])];
                            next[idx] = { ...exp, period: e.target.value };
                            setEditor({ ...editor, experiences: next });
                          }}
                          className="input-field"
                        />
                      </div>
                      <textarea
                        rows={3}
                        placeholder="Achievements & responsibilities (one bullet per line)"
                        value={(exp.bullets || []).join("\n")}
                        onChange={(e) => {
                          const next = [...(editor.experiences || [])];
                          next[idx] = { ...exp, bullets: e.target.value.split("\n") };
                          setEditor({ ...editor, experiences: next });
                        }}
                        className="input-field"
                      />
                    </div>
                  ))}
                </div>

                {/* Education */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-semibold">Education</h3>
                    <button type="button" onClick={addEducationRow} className="btn-secondary py-1.5 text-xs">
                      + Add qualification
                    </button>
                  </div>
                  {(editor.education || []).map((edu, idx) => (
                    <div key={idx} className="grid gap-2.5 rounded-xl border border-white/10 bg-[#0B0F19] p-4 sm:grid-cols-3">
                      <input
                        placeholder="Qualification / Degree"
                        value={edu.qualification || ""}
                        onChange={(e) => {
                          const next = [...(editor.education || [])];
                          next[idx] = { ...edu, qualification: e.target.value };
                          setEditor({ ...editor, education: next });
                        }}
                        className="input-field"
                      />
                      <input
                        placeholder="Institution"
                        value={edu.institution || ""}
                        onChange={(e) => {
                          const next = [...(editor.education || [])];
                          next[idx] = { ...edu, institution: e.target.value };
                          setEditor({ ...editor, education: next });
                        }}
                        className="input-field"
                      />
                      <input
                        placeholder="Dates"
                        value={edu.period || ""}
                        onChange={(e) => {
                          const next = [...(editor.education || [])];
                          next[idx] = { ...edu, period: e.target.value };
                          setEditor({ ...editor, education: next });
                        }}
                        className="input-field"
                      />
                    </div>
                  ))}
                </div>
              </div>

              {/* Immutable Version History */}
              <div className="panel p-5">
                <div className="mb-3 flex items-center gap-2 text-sm font-semibold">
                  <History size={16} className="text-[#5B8CFF]" /> Immutable Version History
                </div>
                <div className="space-y-2">
                  {selected.versions.map((v) => (
                    <div
                      key={v.id}
                      className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-white/10 bg-[#0B0F19] px-4 py-2.5 text-xs"
                    >
                      <div>
                        <span className="font-semibold text-white">Version {v.version_number}</span>
                        <span className="ml-2 rounded bg-white/10 px-1.5 py-0.5 text-[11px] text-[#9AA8BD]">
                          {v.source}
                        </span>
                        <span className="ml-2 text-slate-500">
                          {new Date(v.created_at).toLocaleString()}
                        </span>
                      </div>
                      <button
                        type="button"
                        onClick={() => void handleRestoreVersion(v.id)}
                        className="inline-flex items-center gap-1 text-[#8AB0FF] hover:underline"
                      >
                        <RotateCcw size={12} /> Restore snapshot
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <div className="panel p-10 text-center text-sm text-[#9AA8BD]">
              Select a resume from the library or upload a PDF/DOCX/TXT document to begin editing.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
