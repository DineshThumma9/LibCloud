import { z } from 'zod';
import { readSSEStream, type StreamOptions } from './streaming';

export const LibCloudParamsSchema = z.object({
  username: z.string().min(1, "Username is required"),
  max_logos: z.number().int().min(1).max(500).optional().default(100),
  order_by: z.string().optional().default("max-frequency"),
  preset: z.string().optional().default("web"),
  theme: z.string().optional().default("Minimal"),
  bg_color: z.string().optional(),
  include_forks: z.boolean().optional().default(false),
  include_private: z.boolean().optional().default(false),
  token: z.string().optional(),
});
export type LibCloudParams = z.input<typeof LibCloudParamsSchema>;

/**
 * Initiates SSE streaming connection to the backend.
 */
export async function startLibCloudStream(
  params: LibCloudParams,
  options: StreamOptions = {}
): Promise<void> {
  const query = new URLSearchParams({
    username: params.username.trim(),
    max_logos: String(params.max_logos || 100),
    order_by: params.order_by || "max-frequency",
  });

  if (params.preset) query.set("preset", params.preset);
  if (params.theme) query.set("theme", params.theme);
  if (params.bg_color) query.set("bg_color", params.bg_color);
  if (params.token) query.set("token", params.token);

  const endpoint = `/framecloud?${query.toString()}`;

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
