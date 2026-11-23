"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Calendar, KanbanSquare, List, Plus, Trash2 } from "lucide-react";
import { apiFetch } from "@/lib/api";

const STATUSES = [
  "draft",
  "ready",
  "applied",
  "screening",
  "interview",
  "assessment",
  "offer",
  "rejected",
  "withdrawn",
] as const;

interface InterviewItem {
  id: string;
  scheduled_at: string | null;
  interview_type: string | null;
  notes: string | null;
  outcome: string | null;
}

interface ApplicationRecord {
  id: string;
  company_name: string | null;
  position: string;
  status: string;
  location: string | null;
  salary_range: string | null;
  notes: string | null;
  applied_at: string | null;
  follow_up_at: string | null;
  interviews: InterviewItem[];
}

export default function ApplicationsPage() {
  const [apps, setApps] = useState<ApplicationRecord[]>([]);
  const [view, setView] = useState<"board" | "list">("board");
  const [position, setPosition] = useState("");
  const [company, setCompany] = useState("");
  const [status, setStatus] = useState<(typeof STATUSES)[number]>("draft");
  const [notes, setNotes] = useState("");
  const [interviewAppId, setInterviewAppId] = useState<string | null>(null);
  const [interviewType, setInterviewType] = useState("Technical screen");
  const [interviewDate, setInterviewDate] = useState("");
  const [interviewNotes, setInterviewNotes] = useState("");
  const [error, setError] = useState<string | null>(null);

  const loadApps = useCallback(async () => {
    const data = await apiFetch<ApplicationRecord[]>("/applications");
    setApps(data);
  }, []);

  useEffect(() => {
    let activeFlag = true;
    apiFetch<ApplicationRecord[]>("/applications")
      .then((data) => {
        if (activeFlag) setApps(data);
      })
      .catch((err) => {
        if (activeFlag) setError(err instanceof Error ? err.message : "Failed to load applications");
      });
    return () => {
      activeFlag = false;
    };
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    await apiFetch<ApplicationRecord>("/applications", {
      method: "POST",
      body: JSON.stringify({
        position,
        company_name: company || undefined,
        status,
        notes: notes || undefined,
      }),
    });
    setPosition("");
    setCompany("");
    setNotes("");
    await loadApps();
  }

  async function handleStatusChange(appId: string, nextStatus: string) {
    await apiFetch(`/applications/${appId}`, {
      method: "PATCH",
      body: JSON.stringify({ status: nextStatus }),
    });
    await loadApps();
  }

  async function handleDelete(appId: string) {
    await apiFetch(`/applications/${appId}`, { method: "DELETE" });
    await loadApps();
  }

  async function handleAddInterview(e: React.FormEvent) {
    e.preventDefault();
    if (!interviewAppId) return;
    await apiFetch(`/applications/${interviewAppId}/interviews`, {
      method: "POST",
      body: JSON.stringify({
        interview_type: interviewType,
        scheduled_at: interviewDate ? new Date(interviewDate).toISOString() : undefined,
        notes: interviewNotes || undefined,
      }),
    });
    setInterviewAppId(null);
    setInterviewNotes("");
    setInterviewDate("");
    await loadApps();
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Application Tracker</h1>
          <p className="mt-1 text-sm text-[#9AA8BD]">
            Track every opportunity from draft to offer, link resume versions, and log interviews.
          </p>
        </div>
        <div className="flex rounded-xl border border-white/10 bg-[#121A2A] p-1">
          <button
            type="button"
            onClick={() => setView("board")}
            className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium ${
              view === "board" ? "bg-[#5B8CFF] text-white" : "text-[#9AA8BD]"
            }`}
          >
            <KanbanSquare size={14} /> Board
          </button>
          <button
            type="button"
            onClick={() => setView("list")}
            className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium ${
              view === "list" ? "bg-[#5B8CFF] text-white" : "text-[#9AA8BD]"
            }`}
          >
            <List size={14} /> List
          </button>
        </div>
      </header>

      {error && (
        <div role="alert" className="rounded-xl border border-[#F16B76]/30 bg-[#F16B76]/10 p-3.5 text-sm text-[#F16B76]">
          {error}
        </div>
      )}

      {/* Quick Create */}
      <form onSubmit={handleCreate} className="panel grid gap-3 p-5 md:grid-cols-4">
        <input
          required
          placeholder="Position (e.g. Senior Security Engineer)"
          value={position}
          onChange={(e) => setPosition(e.target.value)}
          className="input-field"
        />
        <input
          placeholder="Company"
          value={company}
          onChange={(e) => setCompany(e.target.value)}
          className="input-field"
        />
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value as (typeof STATUSES)[number])}
          className="input-field"
        >
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              Status: {s}
            </option>
          ))}
        </select>
        <button type="submit" className="btn-primary">
          <Plus size={15} /> Add Application
        </button>
      </form>

      {/* Interview modal-inline */}
      {interviewAppId && (
        <form onSubmit={handleAddInterview} className="panel-elevated space-y-3 p-5">
          <h2 className="text-sm font-semibold">Log Interview Record</h2>
          <div className="grid gap-3 sm:grid-cols-3">
            <input
              value={interviewType}
              onChange={(e) => setInterviewType(e.target.value)}
              placeholder="Type (e.g. Technical, Hiring Manager)"
              className="input-field"
            />
            <input
              type="datetime-local"
              value={interviewDate}
              onChange={(e) => setInterviewDate(e.target.value)}
              className="input-field"
            />
            <input
              value={interviewNotes}
              onChange={(e) => setInterviewNotes(e.target.value)}
              placeholder="Prep notes or outcome"
              className="input-field"
            />
          </div>
          <div className="flex gap-2">
            <button type="submit" className="btn-primary py-2 text-xs">
              Save Interview
            </button>
            <button
              type="button"
              onClick={() => setInterviewAppId(null)}
              className="btn-secondary py-2 text-xs"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {view === "board" ? (
        <div className="grid gap-4 overflow-x-auto md:grid-cols-3 lg:grid-cols-4">
          {STATUSES.map((colStatus) => {
            const colApps = apps.filter((a) => a.status === colStatus);
            return (
              <div key={colStatus} className="panel min-h-[180px] space-y-2.5 p-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-xs font-semibold uppercase tracking-wider text-[#9AA8BD]">
                    {colStatus}
                  </h2>
                  <span className="rounded-full bg-white/10 px-2 py-0.5 text-[11px] text-slate-300">
                    {colApps.length}
                  </span>
                </div>
                {colApps.map((app) => (
                  <div key={app.id} className="space-y-2 rounded-xl border border-white/10 bg-[#0B0F19] p-3">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <p className="text-sm font-medium">{app.position}</p>
                        <p className="text-xs text-[#9AA8BD]">{app.company_name || "Company"}</p>
                      </div>
                      <button
                        type="button"
                        onClick={() => void handleDelete(app.id)}
                        aria-label={`Delete ${app.position}`}
                        className="text-slate-500 hover:text-[#F16B76]"
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                    <select
                      aria-label={`Change status for ${app.position}`}
                      value={app.status}
                      onChange={(e) => void handleStatusChange(app.id, e.target.value)}
                      className="w-full rounded-lg border border-white/10 bg-[#121A2A] px-2 py-1 text-xs text-slate-200"
                    >
                      {STATUSES.map((s) => (
                        <option key={s} value={s}>
                          {s}
                        </option>
                      ))}
                    </select>
                    <div className="flex items-center justify-between text-[11px] text-[#9AA8BD]">
                      <span>{app.interviews.length} interviews</span>
                      <button
                        type="button"
                        onClick={() => setInterviewAppId(app.id)}
                        className="inline-flex items-center gap-1 text-[#8AB0FF] hover:underline"
                      >
                        <Calendar size={11} /> + Interview
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            );
          })}
        </div>
      ) : (
        <div className="panel overflow-x-auto p-5">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-white/10 text-[#9AA8BD]">
              <tr>
                <th className="pb-2.5 pr-4">Position</th>
                <th className="pb-2.5 pr-4">Company</th>
                <th className="pb-2.5 pr-4">Status</th>
                <th className="pb-2.5 pr-4">Interviews</th>
                <th className="pb-2.5">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {apps.map((app) => (
                <tr key={app.id}>
                  <td className="py-3 pr-4 font-medium text-white">{app.position}</td>
                  <td className="py-3 pr-4 text-[#9AA8BD]">{app.company_name || "—"}</td>
                  <td className="py-3 pr-4">
                    <select
                      value={app.status}
                      onChange={(e) => void handleStatusChange(app.id, e.target.value)}
                      className="rounded-lg border border-white/10 bg-[#0B0F19] px-2 py-1 text-xs text-slate-200"
                    >
                      {STATUSES.map((s) => (
                        <option key={s} value={s}>
                          {s}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="py-3 pr-4 text-[#9AA8BD]">{app.interviews.length}</td>
                  <td className="flex gap-3 py-3">
                    <button
                      type="button"
                      onClick={() => setInterviewAppId(app.id)}
                      className="text-[#8AB0FF] hover:underline"
                    >
                      Add interview
                    </button>
                    <button
                      type="button"
                      onClick={() => void handleDelete(app.id)}
                      className="text-[#F16B76] hover:underline"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
