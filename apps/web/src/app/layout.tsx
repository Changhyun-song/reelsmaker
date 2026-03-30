import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ReelsMaker",
  description: "AI 영상 제작 파이프라인",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body className="min-h-screen bg-neutral-950 text-neutral-50 antialiased">
        <nav className="border-b border-neutral-800 px-6 py-4">
          <div className="mx-auto flex max-w-5xl items-center justify-between">
            <a href="/" className="text-lg font-bold tracking-tight">
              ReelsMaker
            </a>
            <div className="flex gap-4 text-sm text-neutral-400">
              <a href="/" className="hover:text-neutral-50 transition">
                Home
              </a>
              <a href="/projects" className="hover:text-neutral-50 transition">
                Projects
              </a>
              <a href="/jobs" className="hover:text-neutral-50 transition">
                Jobs
              </a>
              <a href="/ops" className="hover:text-neutral-50 transition">
                Ops
              </a>
              <a href="/status" className="hover:text-neutral-50 transition">
                Status
              </a>
            </div>
          </div>
        </nav>
        <div className="px-6 py-4">{children}</div>
      </body>
    </html>
  );
}
