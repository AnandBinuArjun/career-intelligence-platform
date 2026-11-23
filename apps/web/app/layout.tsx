import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/auth-context";
import { AppShell } from "@/components/AppShell";

export const metadata: Metadata = {
  title: "CareerIntel — Privacy-First ATS & Career Intelligence",
  description:
    "Free, privacy-first career intelligence platform for resume analysis, job matching, evidence-backed optimization, cover letters, and application tracking.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="dark">
      <body>
        <AuthProvider>
          <AppShell>{children}</AppShell>
        </AuthProvider>
      </body>
    </html>
  );
}
