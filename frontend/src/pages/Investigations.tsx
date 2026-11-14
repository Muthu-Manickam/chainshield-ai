import { useEffect, useState } from "react"
import { stream } from "@/api"
import { Card, CardContent } from "@/components/ui/card"
import type { Step } from "@/types"

export default function Investigations() {
  const [events, setEvents] = useState<Step[]>([])
  const [error, setError] = useState("")

  useEffect(() => {
    const controller = new AbortController()
    stream<Step>("/api/investigations/1/stream", null, (event) => setEvents((all) => [...all, event]), controller.signal)
      .catch((e: Error) => controller.signal.aborted || setError(e.message))
    return () => controller.abort()
  }, [])

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">Investigations</h1>
        <p className="text-muted-foreground">Agent runs with live progress and approvals.</p>
      </div>
      {error && <p className="text-sm text-destructive">{error}</p>}
      <Card>
        <CardContent>
          <pre className="overflow-x-auto text-xs">{events.map((event) => JSON.stringify(event)).join("\n")}</pre>
        </CardContent>
      </Card>
    </div>
  )
}
