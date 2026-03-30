"use client";

import { useEffect, useState, useCallback } from "react";
import { apiUrl } from "@/lib/api";

interface Project {
  id: string;
  title: string;
  description: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

const STATUS_STYLES: Record<string, string> = {
  draft: "bg-neutral-800 text-neutral-300",
  scripting: "bg-blue-900/50 text-blue-400",
  generating: "bg-purple-900/50 text-purple-400",
  composing: "bg-amber-900/50 text-amber-400",
  rendered: "bg-emerald-900/50 text-emerald-400",
  archived: "bg-neutral-800 text-neutral-500",
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [creating, setCreating] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");

  const fetchProjects = useCallback(async () => {
    try {
      const res = await fetch(apiUrl("/api/projects/"));
      if (res.ok) {
        const data = await res.json();
        setProjects(data.projects);
      }
    } catch {
      /* silent */
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  const createProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    setCreating(true);
    try {
      const res = await fetch(apiUrl("/api/projects/"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: title.trim(),
          description: description.trim() || null,
        }),
      });
      if (res.ok) {
        setTitle("");
        setDescription("");
        setShowForm(false);
        await fetchProjects();
      }
    } finally {
      setCreating(false);
    }
  };

  return (
    <main className="mx-auto max-w-5xl">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">프로젝트</h1>
          <p className="mt-1 text-sm text-neutral-500">
            {projects.length}개 프로젝트
          </p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium transition hover:bg-blue-500"
        >
          {showForm ? "취소" : "새 프로젝트"}
        </button>
      </div>

      {showForm && (
        <form
          onSubmit={createProject}
          className="mb-8 rounded-xl border border-neutral-800 bg-neutral-900/50 p-5 space-y-4"
        >
          <div>
            <label className="block text-sm font-medium text-neutral-300 mb-1">
              제목
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="프로젝트 제목"
              className="w-full rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-100 placeholder-neutral-500 focus:border-blue-500 focus:outline-none"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-neutral-300 mb-1">
              설명 (선택)
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="프로젝트에 대한 간단한 설명"
              rows={2}
              className="w-full rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-100 placeholder-neutral-500 focus:border-blue-500 focus:outline-none resize-none"
            />
          </div>
          <button
            type="submit"
            disabled={creating || !title.trim()}
            className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium transition hover:bg-emerald-500 disabled:opacity-50"
          >
            {creating ? "생성 중..." : "프로젝트 생성"}
          </button>
        </form>
      )}

      {loading && projects.length === 0 && (
        <p className="text-neutral-500">불러오는 중...</p>
      )}

      <div className="space-y-3">
        {projects.map((p) => (
          <a
            key={p.id}
            href={`/projects/${p.id}`}
            className="block rounded-xl border border-neutral-800 bg-neutral-900/50 px-5 py-4 transition hover:border-neutral-600 hover:bg-neutral-900"
          >
            <div className="flex items-center justify-between gap-4">
              <div className="min-w-0">
                <div className="flex items-center gap-2.5">
                  <span
                    className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold ${STATUS_STYLES[p.status] ?? "bg-neutral-800 text-neutral-400"}`}
                  >
                    {p.status}
                  </span>
                  <h2 className="text-base font-semibold truncate">
                    {p.title}
                  </h2>
                </div>
                {p.description && (
                  <p className="mt-1 text-sm text-neutral-400 truncate">
                    {p.description}
                  </p>
                )}
              </div>
              <div className="text-xs text-neutral-500 shrink-0 text-right">
                <div>{formatDate(p.created_at)}</div>
              </div>
            </div>
          </a>
        ))}
      </div>

      {!loading && projects.length === 0 && !showForm && (
        <div className="text-center py-16 text-neutral-500">
          <p className="text-lg mb-2">프로젝트가 없습니다</p>
          <p className="text-sm">
            &quot;새 프로젝트&quot; 버튼으로 첫 프로젝트를 만들어 보세요.
          </p>
        </div>
      )}
    </main>
  );
}
