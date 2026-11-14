import { useEffect, useRef, useState } from "react"
import { api, stream } from "@/api"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import type { ChatEvent, ChatMessage } from "@/types"

const SESSION_KEY = "chainshield.chat.session"
const STARTERS = [
  "Why is order 4411 high risk?",
  "Which shipping modes carry the most high-risk orders?",
  "What does guidance say about port closures?",
  "What is waiting for approval?",
]

interface Turn {
  role: "user" | "assistant"
  content: string
  tools: string[]
  citations: string[]
  degraded: boolean
  error?: boolean
}

const keysOf = (citations: unknown[] | null) =>
  (citations ?? []).map((c) => String((c as { citation_key: string }).citation_key))

const fromHistory = (m: ChatMessage): Turn => ({
  role: m.role,
  content: m.content,
  tools: (m.tool_calls ?? []).map((t) => String(t.name)),
  citations: keysOf(m.citations),
  degraded: m.content.startsWith("I could not produce a verified answer"),
})

function Bubble({ turn }: { turn: Turn }) {
  const user = turn.role === "user"
  return (
    <div className={`flex flex-col gap-1.5 ${user ? "items-end" : "items-start"}`}>
      {turn.tools.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {turn.tools.map((t, i) => (
            <Badge key={i} variant="outline" className="font-normal text-muted-foreground">
              used tool {t}
            </Badge>
          ))}
        </div>
      )}
      <div
        className={`max-w-[80%] whitespace-pre-wrap rounded-xl px-4 py-2.5 text-sm ${
          user ? "bg-primary text-primary-foreground" : turn.error ? "bg-destructive/10 text-destructive" : "bg-muted"
        }`}
      >
        {turn.content}
      </div>
      {(turn.degraded || turn.citations.length > 0) && (
        <div className="flex flex-wrap gap-1.5">
          {turn.degraded && (
            <Badge variant="outline" className="border-amber-300 bg-amber-50 text-amber-800">
              Degraded answer: raw tool results
            </Badge>
          )}
          {turn.citations.map((k) => (
            <Badge key={k} variant="secondary">
              {k}
            </Badge>
          ))}
        </div>
      )}
    </div>
  )
}

export default function Assistant() {
  const [sessionId, setSessionId] = useState<string | null>(() => sessionStorage.getItem(SESSION_KEY))
  const [turns, setTurns] = useState<Turn[]>([])
  const [input, setInput] = useState("")
  const [sending, setSending] = useState(false)
  const [tools, setTools] = useState<string[]>([])
  const bottom = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (sessionId) api<ChatMessage[]>(`/api/chat/${sessionId}`).then((m) => setTurns(m.map(fromHistory)), () => {})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    bottom.current?.scrollIntoView({ block: "end" })
  }, [turns, tools])

  const send = async (message: string) => {
    if (!message.trim() || sending) return
    setInput("")
    setSending(true)
    setTools([])
    setTurns((t) => [...t, { role: "user", content: message, tools: [], citations: [], degraded: false }])
    const used: string[] = []
    let finished: string | null = sessionId
    try {
      await stream<ChatEvent>("/api/chat", { session_id: sessionId, message }, (e) => {
        if (e.type === "tool" && e.name) {
          used.push(e.name)
          setTools([...used])
        } else if (e.type === "answer" || e.type === "error") {
          setTurns((t) => [
            ...t,
            {
              role: "assistant",
              content: e.content ?? "",
              tools: [...used],
              citations: keysOf(e.citations ?? null),
              degraded: !!e.degraded,
              error: e.type === "error",
            },
          ])
        } else if (e.type === "done" && e.content) finished = e.content
      })
    } catch (err) {
      const content = err instanceof Error ? err.message : "Request failed"
      setTurns((t) => [...t, { role: "assistant", content, tools: [], citations: [], degraded: false, error: true }])
    }
    setTools([])
    setSending(false)
    if (finished && finished !== sessionId) {
      setSessionId(finished)
      sessionStorage.setItem(SESSION_KEY, finished)
    }
  }

  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col gap-4">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">Assistant</h1>
        <p className="text-muted-foreground">
          Read-only assistant: it answers from ChainShield data and cites sources; it does not take actions.
        </p>
      </div>

      <Card className="min-h-0 flex-1 gap-4 overflow-y-auto p-4">
        {turns.length === 0 && !sending && (
          <div className="m-auto flex max-w-xl flex-col items-center gap-3 text-center">
            <p className="text-sm text-muted-foreground">Try a question:</p>
            <div className="flex flex-wrap justify-center gap-2">
              {STARTERS.map((s) => (
                <Button key={s} variant="outline" size="sm" onClick={() => send(s)}>
                  {s}
                </Button>
              ))}
            </div>
          </div>
        )}
        {turns.map((t, i) => (
          <Bubble key={i} turn={t} />
        ))}
        {sending && (
          <div className="flex flex-col items-start gap-1.5">
            <div className="flex flex-wrap gap-1.5">
              {tools.map((t, i) => (
                <Badge key={i} variant="outline" className="font-normal text-muted-foreground">
                  used tool {t}
                </Badge>
              ))}
            </div>
            <span className="text-sm text-muted-foreground">Thinking…</span>
          </div>
        )}
        <div ref={bottom} />
      </Card>

      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault()
          send(input)
        }}
      >
        <Input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask about orders, incidents or guidance…" />
        <Button type="submit" disabled={sending || !input.trim()}>
          Send
        </Button>
      </form>
    </div>
  )
}
