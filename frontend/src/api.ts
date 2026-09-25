import { useEffect, useState } from "react";
export async function request<T>(
  endpoint: string,
  body: unknown,
  signal?: AbortSignal,
): Promise<T> {
  const response = await fetch(`/api/${endpoint}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(
      typeof error.detail === "string"
        ? error.detail
        : `Simulation unavailable (${response.status}). Check the settings and try again.`,
    );
  }
  return response.json();
}
export function useResource<T>(endpoint: string, settings: unknown) {
  const key = JSON.stringify(settings);
  const [state, setState] = useState<{
    data?: T;
    error?: string;
    loading: boolean;
  }>({ loading: true });
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    setState({ loading: true });
    request<T>(endpoint, JSON.parse(key), controller.signal)
      .then((data) => {
        if (active) setState({ data, loading: false });
      })
      .catch((error: Error) => {
        if (active && error.name !== "AbortError")
          setState({ error: error.message, loading: false });
      });
    return () => {
      active = false;
      controller.abort();
    };
  }, [endpoint, key, revision]);
  return { ...state, retry: () => setRevision((v) => v + 1) };
}
export function download(
  name: string,
  content: string,
  type = "application/json",
) {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
