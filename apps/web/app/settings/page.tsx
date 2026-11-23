"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Download, Plus, Save, ShieldCheck, Trash2, UserCheck } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

interface FullProfile {
  email: string;
  full_name: string | null;
  professional_title: string | null;
  summary: string | null;
  location: string | null;
  target_roles: string[];
  experiences: Array<{ id: string; job_title: string; employer: string | null; description: string | null }>;
  education: Array<{ id: string; institution: string; qualification: string | null }>;
  skills: Array<{ id: string; name: string; proficiency: string | null }>;
  certifications: Array<{ id: string; name: string; issuer: string | null }>;
}

interface PrivacySettings {
  retention_days: number;
  ai_routing_preference: "local" | "external_with_consent";
  external_ai_server_enabled: boolean;
  active_provider: string;
}

interface ConsentItem {
  id: string;
  purpose: string;
  provider: string | null;
  policy_version: string;
  granted: boolean;
  recorded_at: string;
  withdrawn_at: string | null;
}

interface AuditItem {
  id: string;
  action: string;
  resource_type: string | null;
  created_at: string;
}

export default function SettingsPage() {
  const { logout } = useAuth();
  const [profile, setProfile] = useState<FullProfile | null>(null);
  const [privacy, setPrivacy] = useState<PrivacySettings | null>(null);
  const [consents, setConsents] = useState<ConsentItem[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditItem[]>([]);
  const [targetRolesInput, setTargetRolesInput] = useState("");
  const [newSkill, setNewSkill] = useState("");
  const [newExpTitle, setNewExpTitle] = useState("");
  const [newExpEmployer, setNewExpEmployer] = useState("");
  const [newEduInst, setNewEduInst] = useState("");
  const [newEduQual, setNewEduQual] = useState("");
  const [deleteConfirm, setDeleteConfirm] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadAll = useCallback(async () => {
    const [p, ps, cs, al] = await Promise.all([
      apiFetch<FullProfile>("/profile"),
      apiFetch<PrivacySettings>("/privacy/settings"),
      apiFetch<ConsentItem[]>("/privacy/consents"),
      apiFetch<AuditItem[]>("/privacy/audit-logs"),
    ]);
    setProfile(p);
    setTargetRolesInput((p.target_roles || []).join(", "));
    setPrivacy(ps);
    setConsents(cs);
    setAuditLogs(al);
  }, []);

  useEffect(() => {
    let activeFlag = true;
    Promise.all([
      apiFetch<FullProfile>("/profile"),
      apiFetch<PrivacySettings>("/privacy/settings"),
      apiFetch<ConsentItem[]>("/privacy/consents"),
      apiFetch<AuditItem[]>("/privacy/audit-logs"),
    ])
      .then(([p, ps, cs, al]) => {
        if (!activeFlag) return;
        setProfile(p);
        setTargetRolesInput((p.target_roles || []).join(", "));
        setPrivacy(ps);
        setConsents(cs);
        setAuditLogs(al);
      })
      .catch((err) => {
        if (activeFlag) setError(err instanceof Error ? err.message : "Failed to load settings");
      });
    return () => {
      activeFlag = false;
    };
  }, []);

  async function handleSaveProfile(e: React.FormEvent) {
    e.preventDefault();
    if (!profile) return;
    setError(null);
    await apiFetch("/profile", {
      method: "PUT",
      body: JSON.stringify({
        full_name: profile.full_name,
        professional_title: profile.professional_title,
        summary: profile.summary,
        location: profile.location,
        target_roles: targetRolesInput
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
      }),
    });
    setMsg("Verified candidate profile saved.");
    await loadAll();
  }

  async function handleAddSkill(e: React.FormEvent) {
    e.preventDefault();
    if (!newSkill.trim()) return;
    await apiFetch("/profile/skills", {
      method: "POST",
      body: JSON.stringify({ name: newSkill.trim() }),
    });
    setNewSkill("");
    await loadAll();
  }

  async function handleAddExp(e: React.FormEvent) {
    e.preventDefault();
    if (!newExpTitle.trim()) return;
    await apiFetch("/profile/experiences", {
      method: "POST",
      body: JSON.stringify({ job_title: newExpTitle.trim(), employer: newExpEmployer.trim() || undefined }),
    });
    setNewExpTitle("");
    setNewExpEmployer("");
    await loadAll();
  }

  async function handleAddEdu(e: React.FormEvent) {
    e.preventDefault();
    if (!newEduInst.trim()) return;
    await apiFetch("/profile/education", {
      method: "POST",
      body: JSON.stringify({ institution: newEduInst.trim(), qualification: newEduQual.trim() || undefined }),
    });
    setNewEduInst("");
    setNewEduQual("");
    await loadAll();
  }

  async function handleSavePrivacy(e: React.FormEvent) {
    e.preventDefault();
    if (!privacy) return;
    await apiFetch("/privacy/settings", {
      method: "PUT",
      body: JSON.stringify({
        retention_days: privacy.retention_days,
        ai_routing_preference: privacy.ai_routing_preference,
      }),
    });
    setMsg("Privacy & retention settings updated.");
    await loadAll();
  }

  async function handleConsent(granted: boolean) {
    await apiFetch("/privacy/consents", {
      method: "POST",
      body: JSON.stringify({
        purpose: "external_ai_processing",
        provider: "configured_external_llm",
        policy_version: "1.0",
        granted,
      }),
    });
    setMsg(granted ? "External AI consent recorded." : "External AI consent withdrawn.");
    await loadAll();
  }

  async function handleExportJson() {
    const data = await apiFetch<Record<string, unknown>>("/account/export");
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "careerintel-personal-data-export.json";
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  }

  async function handleDeleteAccount() {
    if (deleteConfirm !== "DELETE") return;
    await apiFetch("/account", { method: "DELETE" });
    await logout();
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Settings, Profile &amp; Privacy</h1>
        <p className="mt-1 text-sm text-[#9AA8BD]">
          Manage your verified candidate source of truth, AI provider consent, retention policy,
          portable data export, and account deletion.
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

      {/* Verified Candidate Profile */}
      {profile && (
        <section className="panel space-y-5 p-6">
          <div className="flex items-center gap-2 text-base font-semibold">
            <UserCheck size={18} className="text-[#5B8CFF]" /> Verified Candidate Profile (Source of
            Truth)
          </div>
          <form onSubmit={handleSaveProfile} className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-2">
              <input
                placeholder="Full name"
                value={profile.full_name || ""}
                onChange={(e) => setProfile({ ...profile, full_name: e.target.value })}
                className="input-field"
              />
              <input
                placeholder="Professional title"
                value={profile.professional_title || ""}
                onChange={(e) => setProfile({ ...profile, professional_title: e.target.value })}
                className="input-field"
              />
              <input
                placeholder="Location"
                value={profile.location || ""}
                onChange={(e) => setProfile({ ...profile, location: e.target.value })}
                className="input-field"
              />
              <input
                placeholder="Target roles (comma-separated)"
                value={targetRolesInput}
                onChange={(e) => setTargetRolesInput(e.target.value)}
                className="input-field"
              />
            </div>
            <textarea
              rows={3}
              placeholder="Verified career summary"
              value={profile.summary || ""}
              onChange={(e) => setProfile({ ...profile, summary: e.target.value })}
              className="input-field"
            />
            <button type="submit" className="btn-primary">
              <Save size={15} /> Save Profile
            </button>
          </form>

          {/* Verified Skills */}
          <div className="border-t border-white/10 pt-4">
            <h3 className="mb-2 text-xs font-semibold uppercase text-[#9AA8BD]">Verified Skills</h3>
            <form onSubmit={handleAddSkill} className="mb-3 flex gap-2">
              <input
                placeholder="Add verified skill (e.g. SIEM, Python, Kubernetes)"
                value={newSkill}
                onChange={(e) => setNewSkill(e.target.value)}
                className="input-field max-w-sm"
              />
              <button type="submit" className="btn-secondary">
                <Plus size={14} /> Add
              </button>
            </form>
            <div className="flex flex-wrap gap-2">
              {profile.skills.map((s) => (
                <span
                  key={s.id}
                  className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-[#0B0F19] px-3 py-1 text-xs"
                >
                  {s.name}
                  <button
                    type="button"
                    onClick={() =>
                      void apiFetch(`/profile/skills/${s.id}`, { method: "DELETE" }).then(() => loadAll())
                    }
                    aria-label={`Remove ${s.name}`}
                    className="text-slate-500 hover:text-[#F16B76]"
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          </div>

          {/* Verified Experience & Education quick add */}
          <div className="grid gap-4 border-t border-white/10 pt-4 md:grid-cols-2">
            <div>
              <h3 className="mb-2 text-xs font-semibold uppercase text-[#9AA8BD]">Verified Roles</h3>
              <form onSubmit={handleAddExp} className="mb-2 flex gap-2">
                <input
                  placeholder="Job title"
                  value={newExpTitle}
                  onChange={(e) => setNewExpTitle(e.target.value)}
                  className="input-field"
                />
                <input
                  placeholder="Employer"
                  value={newExpEmployer}
                  onChange={(e) => setNewExpEmployer(e.target.value)}
                  className="input-field"
                />
                <button type="submit" className="btn-secondary px-3">
                  <Plus size={14} />
                </button>
              </form>
              <ul className="space-y-1.5 text-xs text-slate-300">
                {profile.experiences.map((ex) => (
                  <li key={ex.id} className="flex justify-between rounded-lg bg-[#0B0F19] px-3 py-2">
                    <span>
                      {ex.job_title} {ex.employer ? `— ${ex.employer}` : ""}
                    </span>
                    <button
                      type="button"
                      onClick={() =>
                        void apiFetch(`/profile/experiences/${ex.id}`, { method: "DELETE" }).then(() =>
                          loadAll()
                        )
                      }
                      className="text-slate-500 hover:text-[#F16B76]"
                    >
                      Remove
                    </button>
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <h3 className="mb-2 text-xs font-semibold uppercase text-[#9AA8BD]">Verified Education</h3>
              <form onSubmit={handleAddEdu} className="mb-2 flex gap-2">
                <input
                  placeholder="Institution"
                  value={newEduInst}
                  onChange={(e) => setNewEduInst(e.target.value)}
                  className="input-field"
                />
                <input
                  placeholder="Qualification"
                  value={newEduQual}
                  onChange={(e) => setNewEduQual(e.target.value)}
                  className="input-field"
                />
                <button type="submit" className="btn-secondary px-3">
                  <Plus size={14} />
                </button>
              </form>
              <ul className="space-y-1.5 text-xs text-slate-300">
                {profile.education.map((ed) => (
                  <li key={ed.id} className="flex justify-between rounded-lg bg-[#0B0F19] px-3 py-2">
                    <span>
                      {ed.qualification || ed.institution} ({ed.institution})
                    </span>
                    <button
                      type="button"
                      onClick={() =>
                        void apiFetch(`/profile/education/${ed.id}`, { method: "DELETE" }).then(() =>
                          loadAll()
                        )
                      }
                      className="text-slate-500 hover:text-[#F16B76]"
                    >
                      Remove
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </section>
      )}

      {/* AI Routing & Privacy Consent */}
      {privacy && (
        <section className="panel space-y-4 p-6">
          <div className="flex items-center gap-2 text-base font-semibold">
            <ShieldCheck size={18} className="text-[#35C98A]" /> Privacy, AI Routing &amp; Consent
          </div>
          <p className="text-xs leading-5 text-[#9AA8BD]">
            Active inference provider: <strong className="text-white">{privacy.active_provider}</strong>.
            External AI processing is{" "}
            <strong className="text-white">
              {privacy.external_ai_server_enabled ? "available with consent" : "disabled on server"}
            </strong>
            . Personal CVs are never sent to external providers silently.
          </p>

          <form onSubmit={handleSavePrivacy} className="grid gap-3 sm:grid-cols-3">
            <div>
              <label className="mb-1 block text-xs text-[#9AA8BD]">Document retention (days)</label>
              <input
                type="number"
                min={7}
                max={3650}
                value={privacy.retention_days}
                onChange={(e) => setPrivacy({ ...privacy, retention_days: Number(e.target.value) })}
                className="input-field"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-[#9AA8BD]">AI routing preference</label>
              <select
                value={privacy.ai_routing_preference}
                onChange={(e) =>
                  setPrivacy({
                    ...privacy,
                    ai_routing_preference: e.target.value as "local" | "external_with_consent",
                  })
                }
                className="input-field"
              >
                <option value="local">Local-only (Ollama / Deterministic)</option>
                <option value="external_with_consent">External AI (explicit consent required)</option>
              </select>
            </div>
            <div className="flex items-end">
              <button type="submit" className="btn-secondary w-full">
                Save preferences
              </button>
            </div>
          </form>

          <div className="flex flex-wrap gap-2 pt-2">
            <button type="button" onClick={() => void handleConsent(true)} className="btn-secondary text-xs">
              Grant external AI consent (v1.0)
            </button>
            <button type="button" onClick={() => void handleConsent(false)} className="btn-danger text-xs">
              Withdraw external AI consent
            </button>
          </div>

          {consents.length > 0 && (
            <div className="space-y-1.5 pt-2">
              <h3 className="text-xs font-semibold uppercase text-[#9AA8BD]">Consent History</h3>
              {consents.slice(0, 5).map((c) => (
                <div
                  key={c.id}
                  className="flex items-center justify-between rounded-lg bg-[#0B0F19] px-3 py-2 text-xs"
                >
                  <span>
                    {c.purpose} ({c.granted && !c.withdrawn_at ? "Active" : "Withdrawn/Denied"})
                  </span>
                  <span className="text-slate-500">{new Date(c.recorded_at).toLocaleString()}</span>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {/* Data Export, Audit & Deletion */}
      <section className="panel space-y-4 p-6">
        <h2 className="text-base font-semibold">Data Portability, Activity &amp; Account Deletion</h2>
        <div className="flex flex-wrap gap-3">
          <button type="button" onClick={() => void handleExportJson()} className="btn-secondary">
            <Download size={15} /> Export all personal data (JSON)
          </button>
        </div>

        {auditLogs.length > 0 && (
          <div className="space-y-1.5">
            <h3 className="text-xs font-semibold uppercase text-[#9AA8BD]">Recent Security Activity</h3>
            {auditLogs.slice(0, 6).map((a) => (
              <div key={a.id} className="flex justify-between rounded-lg bg-[#0B0F19] px-3 py-2 text-xs">
                <span className="font-mono text-slate-300">{a.action}</span>
                <span className="text-slate-500">{new Date(a.created_at).toLocaleString()}</span>
              </div>
            ))}
          </div>
        )}

        <div className="rounded-xl border border-[#F16B76]/30 bg-[#F16B76]/5 p-4">
          <h3 className="text-sm font-semibold text-[#F16B76]">Delete Account &amp; All Documents</h3>
          <p className="mt-1 text-xs text-[#9AA8BD]">
            Permanently deletes your account, verified profile, all resume versions, private stored
            files, analyses, cover letters, and application records. Type <strong>DELETE</strong> to
            confirm.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <input
              placeholder="Type DELETE to confirm"
              value={deleteConfirm}
              onChange={(e) => setDeleteConfirm(e.target.value)}
              className="input-field max-w-xs"
            />
            <button
              type="button"
              disabled={deleteConfirm !== "DELETE"}
              onClick={() => void handleDeleteAccount()}
              className="btn-danger"
            >
              <Trash2 size={15} /> Permanently delete account
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
