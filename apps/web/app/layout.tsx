import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CodeMigrator AI · Powered by NVIDIA Nemotron 3",
  description:
    "Multi-agent legacy code migration. COBOL → Python at scale, with Super + Nano routing.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-slate-950 text-slate-100 antialiased">{children}</body>
    </html>
  );
}
