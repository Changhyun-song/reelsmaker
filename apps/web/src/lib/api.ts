export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function apiUrl(path: string): string {
  return `${API_BASE}${path}`;
}

/**
 * Authenticated fetch wrapper. Attaches Clerk session token when available.
 * Falls back to regular fetch for unauthenticated/local-dev requests.
 */
export async function authFetch(
  url: string,
  init?: RequestInit,
  getToken?: () => Promise<string | null>,
): Promise<Response> {
  const headers = new Headers(init?.headers);

  if (getToken) {
    try {
      const token = await getToken();
      if (token) {
        headers.set("Authorization", `Bearer ${token}`);
      }
    } catch {
      // Clerk not available (local dev without keys) — proceed without auth
    }
  }

  return fetch(url, { ...init, headers });
}
