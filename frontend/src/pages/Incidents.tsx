import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"
import { Link } from "react-router"
import { toast } from "sonner"
import { api } from "@/api"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Textarea } from "@/components/ui/textarea"
import type { Incident, Page, User } from "@/types"

const LABELS = ["infrastructure", "affected_people", "rescue_donation", "other_relevant", "not_humanitarian"]
const STATUSES = ["pool", "classified", "needs_review", "reviewed"]
const ALL = "all"

function FilterSelect({ value, options, onChange }: { value: string; options: string[]; onChange: (v: string) => void }) {
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger className="w-48">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value={ALL}>All</SelectItem>
        {options.map((o) => (
          <SelectItem key={o} value={o}>
            {o}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}

export default function Incidents() {
  const qc = useQueryClient()
  const me = useQuery({ queryKey: ["me"], queryFn: () => api<User>("/api/auth/me") })
  const [status, setStatus] = useState(ALL)
  const [label, setLabel] = useState(ALL)
  const [page, setPage] = useState(1)
  const [text, setText] = useState("")
  const [picks, setPicks] = useState<Record<number, string>>({})

  const params = new URLSearchParams({ page: String(page) })
  if (status !== ALL) params.set("status", status)
  if (label !== ALL) params.set("label", label)
  const incidents = useQuery({
    queryKey: ["incidents", status, label, page],
    queryFn: () => api<Page<Incident>>(`/api/incidents?${params}`),
  })

  const run = useMutation({
    mutationFn: ({ path, body }: { path: string; body?: unknown }) =>
      api<unknown>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["incidents"] }),
    onError: (e: Error) => toast.error(e.message),
  })

  const addMessage = () =>
    run.mutate({ path: "/api/incidents", body: { text } }, { onSuccess: () => setText("") })

  const pages = Math.max(1, Math.ceil((incidents.data?.total ?? 0) / 50))

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-start justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-semibold tracking-tight">Incidents</h1>
          <p className="text-muted-foreground">Screen, classify and review disaster reports.</p>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => run.mutate({ path: "/api/incidents/release", body: { count: 10 } })}>
            Release next 10
          </Button>
          {me.data?.role === "admin" && (
            <Button
              variant="outline"
              onClick={() => run.mutate({ path: "/api/incidents/release-gold" }, { onSuccess: () => toast.success("Gold labels released") })}
            >
              Release gold labels
            </Button>
          )}
        </div>
      </div>

      <Card className="gap-3 p-4">
        <Textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Paste a message to classify…"
        />
        <Button className="self-start" disabled={!text.trim() || run.isPending} onClick={addMessage}>
          Add message
        </Button>
      </Card>

      <div className="flex gap-3">
        <FilterSelect value={status} options={STATUSES} onChange={(v) => { setStatus(v); setPage(1) }} />
        <FilterSelect value={label} options={LABELS} onChange={(v) => { setLabel(v); setPage(1) }} />
      </div>

      {incidents.isPending && <Skeleton className="h-64" />}
      {incidents.error && <p className="text-sm text-destructive">{incidents.error.message}</p>}
      {incidents.data && (
        <Card className="py-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Text</TableHead>
                <TableHead>Predicted</TableHead>
                <TableHead>Confidence</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Review</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {incidents.data.items.map((i) => {
                const pick = picks[i.id] ?? i.reviewed_label ?? i.predicted_label ?? undefined
                return (
                  <TableRow key={i.id}>
                    <TableCell className="max-w-md whitespace-normal">{i.text}</TableCell>
                    <TableCell>{i.predicted_label && <Badge variant="secondary">{i.predicted_label}</Badge>}</TableCell>
                    <TableCell className="tabular-nums">
                      {i.confidence !== null && `${(i.confidence * 100).toFixed(0)}%`}
                    </TableCell>
                    <TableCell>
                      <Badge variant={i.status === "needs_review" ? "destructive" : "outline"}>{i.status}</Badge>
                    </TableCell>
                    <TableCell>
                      {i.status !== "pool" && (
                        <div className="flex gap-2">
                          <Select value={pick} onValueChange={(v) => setPicks({ ...picks, [i.id]: v })}>
                            <SelectTrigger size="sm" className="w-44">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {LABELS.map((l) => (
                                <SelectItem key={l} value={l}>
                                  {l}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={!pick}
                            onClick={() => run.mutate({ path: `/api/incidents/${i.id}/review`, body: { label: pick } })}
                          >
                            {pick === i.predicted_label ? "Confirm" : "Correct"}
                          </Button>
                        </div>
                      )}
                    </TableCell>
                    <TableCell>
                      <Button size="sm" asChild>
                        <Link to={`/investigations?incident=${i.id}`}>Investigate</Link>
                      </Button>
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </Card>
      )}

      <div className="flex items-center justify-end gap-3 text-sm text-muted-foreground">
        {incidents.data?.total ?? 0} incidents · page {page} of {pages}
        <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage(page - 1)}>
          Previous
        </Button>
        <Button size="sm" variant="outline" disabled={page >= pages} onClick={() => setPage(page + 1)}>
          Next
        </Button>
      </div>
    </div>
  )
}
