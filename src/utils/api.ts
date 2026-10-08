import {
  buildCloudAgentHeaders,
  CLOUD_AGENT_URL,
} from "@/utils/ai.functions"

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(
    buildCloudAgentHeaders(true),
  )

  new Headers(options.headers).forEach(
    (value, name) => headers.set(name, value),
  )

  const authHeaders = buildCloudAgentHeaders()
  if (authHeaders["X-API-Key"]) {
    headers.set(
      "X-API-Key",
      authHeaders["X-API-Key"],
    )
  }

  const response = await fetch(
    `${CLOUD_AGENT_URL}${path}`,
    {
      ...options,
      headers,
    },
  )

  const data = await response.json()

  if (!response.ok) {
    throw new Error(
      data?.message ||
        "API request failed.",
    )
  }

  return data as T
}
