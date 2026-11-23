"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BriefcaseBusiness,
  FileSearch,
  FileText,
  FileUser,
  LayoutDashboard,
  LogOut,
  Menu,
  Settings,
  ShieldCheck,
  Sparkles,
  Target,
  X,
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { AuthGate } from "./AuthGate";

const NAV_ITEMS = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/resumes", label: "My Resumes", icon: FileUser },
  { href: "/analyzer", label: "ATS Analyzer", icon: FileSearch },
  { href: "/jobs", label: "Job Intelligence", icon: Target },
  { href: "/cover-letters", label: "Cover Letters", icon: FileText },
  { href: "/career", label: "Career Development", icon: Sparkles },
  { href: "/applications", label: "Applications", icon: BriefcaseBusiness },
  { href: "/settings", label: "Settings & Privacy", icon: Settings },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, loading, logout } = useAuth();
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#0B0F19] text-sm text-[#9AA8BD]">
        Loading CareerIntel workspace…
      </div>
    );
  }

  if (!user) {
    return <AuthGate />;
  }

  return (
    <div className="min-h-screen bg-[#0B0F19] text-[#F4F7FB]">
      {/* Mobile top bar */}
      <div className="sticky top-0 z-30 flex items-center justify-between border-b border-white/10 bg-[#0E1421] px-4 py-3 md:hidden">
        <Link href="/" className="text-base font-semibold tracking-tight">
          Career<span className="text-[#5B8CFF]">Intel</span>
        </Link>
        <button
          type="button"
          onClick={() => setMobileOpen((prev) => !prev)}
          aria-label="Toggle navigation menu"
          aria-expanded={mobileOpen}
          className="rounded-lg border border-white/10 p-2 text-slate-300 hover:bg-white/5"
        >
          {mobileOpen ? <X size={18} /> : <Menu size={18} />}
        </button>
      </div>

      <div className="mx-auto flex max-w-[1440px]">
        {/* Persistent desktop sidebar & slide-over mobile drawer */}
        <aside
          aria-label="Primary navigation"
          className={`${
            mobileOpen ? "fixed inset-y-0 left-0 z-40 block" : "hidden"
          } min-h-screen w-64 shrink-0 border-r border-white/10 bg-[#0E1421] p-5 md:sticky md:top-0 md:block md:h-screen md:overflow-y-auto`}
        >
          <div className="mb-8 flex items-center justify-between">
            <Link
              href="/"
              onClick={() => setMobileOpen(false)}
              className="text-lg font-semibold tracking-tight"
            >
              Career<span className="text-[#5B8CFF]">Intel</span>
            </Link>
            <span className="rounded-full border border-[#35C98A]/30 bg-[#35C98A]/10 px-2 py-0.5 text-[11px] font-medium text-[#35C98A]">
              Free
            </span>
          </div>

          <nav className="space-y-1">
            {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
              const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
              return (
                <Link
                  key={href}
                  href={href}
                  onClick={() => setMobileOpen(false)}
                  aria-current={active ? "page" : undefined}
                  className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${
                    active
                      ? "bg-[#5B8CFF]/15 text-[#8AB0FF]"
                      : "text-slate-300 hover:bg-white/5 hover:text-white"
                  }`}
                >
                  <Icon size={17} aria-hidden="true" />
                  <span>{label}</span>
                </Link>
              );
            })}
          </nav>

          <div className="mt-8 rounded-2xl border border-white/10 bg-white/[0.03] p-4">
            <div className="flex items-center gap-2 text-xs font-medium text-[#35C98A]">
              <ShieldCheck size={15} aria-hidden="true" />
              <span>Local-first privacy</span>
            </div>
            <p className="mt-2 text-xs leading-5 text-[#9AA8BD]">
              External AI is disabled unless you record explicit consent in Settings.
            </p>
          </div>

          <div className="mt-6 border-t border-white/10 pt-4">
            <p className="truncate text-xs text-[#9AA8BD]" title={user.email}>
              {user.email}
            </p>
            <button
              type="button"
              onClick={() => void logout()}
              className="mt-2.5 flex w-full items-center gap-2 rounded-xl px-3 py-2 text-xs font-medium text-slate-300 transition hover:bg-white/5 hover:text-white"
            >
              <LogOut size={14} aria-hidden="true" />
              <span>Sign out</span>
            </button>
          </div>
        </aside>

        {mobileOpen && (
          <div
            className="fixed inset-0 z-30 bg-black/60 md:hidden"
            onClick={() => setMobileOpen(false)}
            aria-hidden="true"
          />
        )}

        <main className="min-w-0 flex-1 p-5 md:p-8 lg:p-10">{children}</main>
      </div>
    </div>
  );
}
