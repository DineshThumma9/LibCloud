import { readSSEStream, type StreamOptions } from "./streaming";

export type LibCloudParams = {
  username: string;
  token?: string;
};

/**
 * Starts the SSE scan. Display controls are client-side, so only the scan
 * identity goes to the backend. The token travels in the Authorization header,
 * never in the URL.
 */
export async function startLibCloudStream(
  params: LibCloudParams,
  options: StreamOptions = {}
): Promise<void> {
  const query = new URLSearchParams({ username: params.username.trim() });
  const endpoint = `/framecloud/stream?${query.toString()}`;

  const response = await fetch(endpoint, {
    method: "GET",
    headers: {
      Accept: "text/event-stream",
      ...(params.token ? { Authorization: `Bearer ${params.token}` } : {}),
    },
    signal: options.signal,
  });

  if (!response.ok) {
    let errorDetail = `HTTP ${response.status}`;
    try {
      const data = await response.json();
      if (typeof data?.detail === "string") {
        errorDetail = data.detail;
      } else if (Array.isArray(data?.detail)) {
        errorDetail = data.detail.map((m: any) => m.msg || m.message).join(", ");
      } else if (data?.message) {
        errorDetail = data.message;
      }
    } catch {
      try {
        const text = await response.text();
        if (text) errorDetail = text;
      } catch {
        // ignore
      }
    }
    throw new Error(errorDetail);
  }

  await readSSEStream(response, options);
}

export interface ShareResponse {
  share_id: string;
  page_url: string;
  svg_url: string;
  png_url: string;
  og_url: string;
  markdown: string;
}

export async function createShare(payload: {
  username: string;
  svg_data: string;
  png_base64?: string;
  title?: string;
}): Promise<ShareResponse> {
  const response = await fetch('/api/shares', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Failed to create share: ${response.statusText}`);
  }

  return response.json();
}
