async function request(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers)
  if (!(init.body instanceof FormData)) headers.set("Content-Type", "application/json")
  const res = await fetch(path, { credentials: "include", ...init, headers })
  if (res.status === 401 && window.location.pathname !== "/login") {
    window.location.assign("/login")
  }
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(typeof body?.detail === "string" ? body.detail : res.statusText)
  }
  return res
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const text = await (await request(path, init)).text()
  return (text ? JSON.parse(text) : undefined) as T
}

// Reads a text/event-stream response; each `data: <json>` line becomes one onEvent call.
export async function stream<T>(
  path: string,
  body: unknown,
  onEvent: (event: T) => void,
  signal?: AbortSignal,
): Promise<void> {
  const init: RequestInit = body === null ? { signal } : { method: "POST", body: JSON.stringify(body), signal }
  const res = await request(path, init)
  const reader = res.body!.pipeThrough(new TextDecoderStream()).getReader()
  let buffer = ""
  for (;;) {
    const { done, value } = await reader.read()
    if (done) return
    buffer += value
    const messages = buffer.split("\n\n")
    buffer = messages.pop()!
    for (const message of messages) {
      if (message.startsWith("data: ")) onEvent(JSON.parse(message.slice(6)))
    }
  }
}
