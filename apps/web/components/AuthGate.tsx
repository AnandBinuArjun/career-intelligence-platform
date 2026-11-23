"use client";

import React, { useState } from "react";
import { ShieldCheck, Lock, Sparkles } from "lucide-react";
import { useAuth } from "@/lib/auth-context";

export function AuthGate() {
  const { login, register } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (mode === "register") {
        await register(email, password, fullName);
      } else {
        await login(email, password);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#0B0F19] px-4 py-10">
      <div className="grid w-full max-w-4xl gap-8 md:grid-cols-2">
        <div className="flex flex-col justify-between rounded-3xl border border-blue-400/20 bg-gradient-to-br from-[#5B8CFF]/15 via-[#121A2A] to-[#121A2A] p-8">
          <div>
            <div className="text-xl font-semibold tracking-tight">
              Career<span className="text-[#5B8CFF]">Intel</span>
            </div>
            <h1 className="mt-6 text-3xl font-semibold leading-tight text-[#F4F7FB]">
              Your career deserves better intelligence.
            </h1>
            <p className="mt-3 text-sm leading-6 text-[#9AA8BD]">
              Analyse job requirements, score resume compatibility transparently, optimize with
              evidence, generate grounded cover letters, and track applications — 100% free.
            </p>
          </div>

          <ul className="mt-8 space-y-3 text-xs text-slate-300">
            <li className="flex items-start gap-2.5">
              <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-[#35C98A]" />
              <span>Privacy-first: private storage, row-level isolation, local AI by default.</span>
            </li>
            <li className="flex items-start gap-2.5">
              <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-[#5B8CFF]" />
              <span>Evidence before generation: never fabricates skills, dates, or credentials.</span>
            </li>
            <li className="flex items-start gap-2.5">
              <Lock className="mt-0.5 h-4 w-4 shrink-0 text-[#F5B94C]" />
              <span>Free forever: no paywalls, no watermarked exports, no selling CV data.</span>
            </li>
          </ul>
        </div>

        <div className="panel p-8">
          <div className="mb-6 flex rounded-xl border border-white/10 bg-[#0B0F19] p-1">
            <button
              type="button"
              onClick={() => {
                setMode("login");
                setError(null);
              }}
              className={`flex-1 rounded-lg py-2 text-sm font-medium transition ${
                mode === "login"
                  ? "bg-[#5B8CFF] text-white"
                  : "text-[#9AA8BD] hover:text-white"
              }`}
            >
              Sign in
            </button>
            <button
              type="button"
              onClick={() => {
                setMode("register");
                setError(null);
              }}
              className={`flex-1 rounded-lg py-2 text-sm font-medium transition ${
                mode === "register"
                  ? "bg-[#5B8CFF] text-white"
                  : "text-[#9AA8BD] hover:text-white"
              }`}
            >
              Create account
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === "register" && (
              <div>
                <label htmlFor="full-name" className="mb-1.5 block text-xs font-medium text-[#9AA8BD]">
                  Full name (optional)
                </label>
                <input
                  id="full-name"
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Alex Morgan"
                  className="input-field"
                />
              </div>
            )}

            <div>
              <label htmlFor="auth-email" className="mb-1.5 block text-xs font-medium text-[#9AA8BD]">
                Email address
              </label>
              <input
                id="auth-email"
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="input-field"
              />
            </div>

            <div>
              <label htmlFor="auth-password" className="mb-1.5 block text-xs font-medium text-[#9AA8BD]">
                Password {mode === "register" && <span className="text-slate-500">(min 12 characters)</span>}
              </label>
              <input
                id="auth-password"
                type="password"
                required
                minLength={mode === "register" ? 12 : 1}
                autoComplete={mode === "register" ? "new-password" : "current-password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="input-field"
              />
            </div>

            {error && (
              <div
                role="alert"
                className="rounded-xl border border-[#F16B76]/30 bg-[#F16B76]/10 px-3.5 py-2.5 text-xs text-[#F16B76]"
              >
                {error}
              </div>
            )}

            <button type="submit" disabled={submitting} className="btn-primary w-full">
              {submitting
                ? "Please wait…"
                : mode === "register"
                  ? "Create free account"
                  : "Sign in to workspace"}
            </button>
          </form>

          <p className="mt-5 text-xs leading-5 text-slate-500">
            External AI providers are disabled by default. You can export or delete all personal
            documents at any time in Settings &amp; Privacy.
          </p>
        </div>
      </div>
    </div>
  );
}
