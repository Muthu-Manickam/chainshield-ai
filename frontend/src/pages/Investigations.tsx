import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useEffect, useState } from "react"
import { Link, useNavigate, useParams, useSearchParams } from "react-router"
import { toast } from "sonner"
import { api, stream } from "@/api"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import type { Action, ActionRule, Investigation, InvestigationDetail, Step, User } from "@/types"

const MARKETS = ["Africa", "Europe", "LATAM", "Pacific Asia", "USCA"]
const SHIPPING_MODES = ["Standard Class", "Second Class", "First Class", "Same Day"]
const ANY = "any"

function StatusBadge({ status }: { status: string }) {
  const variant = status === "failed" ? "destructive" : status === "running" || status === "reporting" ? "secondary" : "outline"
  return <Badge variant={variant}>{status.replace("_", " ")}</Badge>
}

function ScopeSelect({ label, value, options, onChange }: { label: string; value: string; options: string[]; onChange: (v: string) => void }) {
  return (
    <div className="flex flex-col gap-1.5 text-sm">
      {label}
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger className="w-48">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={ANY}>Any</SelectItem>
          {options.map((o) => (
            <SelectItem key={o} value={o}>
              {o}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}

function scopeFromQuery(raw: string | null): Record<string, string> {
  try {
    return raw ? JSON.parse(raw) : {}
  } catch {
    return {}
  }
}

function NewInvestigation() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [params] = useSearchParams()
  const initial = scopeFromQuery(params.get("scope"))
  const [incidentId, setIncidentId] = useState(params.get("incident") ?? "")
  const [market, setMarket] = useState(initial.market ?? ANY)
  const [mode, setMode] = useState(initial.shipping_mode ?? ANY)

  const start = useMutation({
    mutationFn: () => {
      const scope: Record<string, string> = {}
      if (market !== ANY) scope.market = market
      if (mode !== ANY) scope.shipping_mode = mode
      return api<Investigation>("/api/investigations", {
        method: "POST",
        body: JSON.stringify({ incident_id: Number(incidentId), scope }),
      })
    },
    onSuccess: (created) => {
      qc.invalidateQueries({ queryKey: ["investigations"] })
      navigate(`/investigations/${created.id}`)
    },
    onError: (e: Error) => toast.error(e.message),
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle>New investigation</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <div className="flex flex-wrap items-end gap-4">
          <label className="flex flex-col gap-1.5 text-sm">
            Incident id
            <Input className="w-32" inputMode="numeric" value={incidentId} onChange={(e) => setIncidentId(e.target.value)} />
          </label>
          <ScopeSelect label="Market" value={market} options={MARKETS} onChange={setMarket} />
          <ScopeSelect label="Shipping mode" value={mode} options={SHIPPING_MODES} onChange={setMode} />
          <Button disabled={!/^\d+$/.test(incidentId) || start.isPending} onClick={() => start.mutate()}>
            Start
          </Button>
        </div>
        <p className="text-sm text-muted-foreground">Order scope chosen by analyst, not linked by data</p>
      </CardContent>
    </Card>
  )
}

function List() {
  const list = useQuery({ queryKey: ["investigations"], queryFn: () => api<Investigation[]>("/api/investigations") })
  return (
    <>
      <NewInvestigation />
      {list.isPending && <Skeleton className="h-48" />}
      {list.error && <p className="text-sm text-destructive">{list.error.message}</p>}
      {list.data && (
        <Card className="py-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>Incident</TableHead>
                <TableHead>Scope</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Started</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {list.data.map((i) => (
                <TableRow key={i.id}>
                  <TableCell>#{i.id}</TableCell>
                  <TableCell>#{i.incident_id}</TableCell>
                  <TableCell>{Object.values(i.scope).join(" · ") || "none"}</TableCell>
                  <TableCell>
                    <StatusBadge status={i.status} />
                    {i.degraded && <Badge variant="destructive" className="ml-2">degraded</Badge>}
                  </TableCell>
                  <TableCell>{new Date(i.created_at).toLocaleString()}</TableCell>
                  <TableCell>
                    <Button size="sm" variant="outline" asChild>
                      <Link to={`/investigations/${i.id}`}>Open</Link>
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
              {list.data.length === 0 && (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-muted-foreground">
                    No investigations yet.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </Card>
      )}
    </>
  )
}

const asList = (value: unknown): unknown[] => (Array.isArray(value) ? value : value ? [value] : [])
const citationKey = (c: unknown) => String((c as { citation_key?: string })?.citation_key ?? c)
const summarize = (output: unknown) => (output ? JSON.stringify(output).slice(0, 200) : "")

function Timeline({ steps }: { steps: Step[] }) {
  return (
    <Card className="py-0">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Step</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Duration</TableHead>
            <TableHead>Output</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {steps.map((s) => (
            <TableRow key={s.id}>
              <TableCell className="font-medium">{s.node}</TableCell>
              <TableCell>
                <Badge variant={s.status === "ok" ? "outline" : "destructive"}>{s.status}</Badge>
              </TableCell>
              <TableCell className="tabular-nums">{s.duration_ms} ms</TableCell>
              <TableCell className="max-w-xl whitespace-normal break-words text-xs text-muted-foreground">
                {s.error ?? summarize(s.output)}
              </TableCell>
            </TableRow>
          ))}
          {steps.length === 0 && (
            <TableRow>
              <TableCell colSpan={4} className="text-center text-muted-foreground">
                Waiting for the first step…
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </Card>
  )
}

function Actions({ actions, canDecide, onDecide }: { actions: Action[]; canDecide: boolean; onDecide: (a: Action, d: "approved" | "rejected") => void }) {
  const rules = useQuery({ queryKey: ["rules"], queryFn: () => api<ActionRule[]>("/api/rules") })
  const sorted = [...actions].sort((a, b) => Number(b.eligible) - Number(a.eligible) || (a.rank ?? 99) - (b.rank ?? 99))
  return (
    <Card className="py-0">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Rank</TableHead>
            <TableHead>Action</TableHead>
            <TableHead>Eligibility</TableHead>
            <TableHead>Cost</TableHead>
            <TableHead>Approval role</TableHead>
            <TableHead>Rationale</TableHead>
            <TableHead>Decision</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {sorted.map((a) => {
            const rule = rules.data?.find((r) => r.code === a.rule_code)
            return (
            <TableRow key={a.id}>
              <TableCell>{a.rank ?? "-"}</TableCell>
              <TableCell className="font-medium">{a.name}</TableCell>
              <TableCell className="max-w-xs whitespace-normal">
                <Badge variant={a.eligible ? "secondary" : "destructive"}>{a.eligible ? "eligible" : "rejected"}</Badge>
                <p className="mt-1 text-xs text-muted-foreground">{a.reason}</p>
              </TableCell>
              <TableCell className="tabular-nums">{rule ? `$${rule.cost_usd.toLocaleString()}` : "-"}</TableCell>
              <TableCell>{rule?.approval_role ?? "-"}</TableCell>
              <TableCell className="max-w-sm whitespace-normal text-sm">{a.rationale}</TableCell>
              <TableCell>
                {a.decision !== "pending" && <Badge variant="outline">{a.decision}</Badge>}
                {a.decision === "pending" && a.eligible && canDecide && (
                  <div className="flex gap-2">
                    <Button size="sm" onClick={() => onDecide(a, "approved")}>Approve</Button>
                    <Button size="sm" variant="outline" onClick={() => onDecide(a, "rejected")}>Reject</Button>
                  </div>
                )}
              </TableCell>
            </TableRow>
            )
          })}
        </TableBody>
      </Table>
    </Card>
  )
}

function Detail({ id }: { id: string }) {
  const qc = useQueryClient()
  const me = useQuery({ queryKey: ["me"], queryFn: () => api<User>("/api/auth/me") })
  const detail = useQuery({
    queryKey: ["investigation", id],
    queryFn: () => api<InvestigationDetail>(`/api/investigations/${id}`),
    refetchInterval: (q) => (["running", "reporting"].includes(q.state.data?.status ?? "running") ? 3000 : false),
  })
  const [live, setLive] = useState<Step[]>([])

  useEffect(() => {
    const controller = new AbortController()
    setLive([])
    stream<Step | { type: "done" }>(
      `/api/investigations/${id}/stream`,
      null,
      (event) => {
        if ("type" in event) qc.invalidateQueries({ queryKey: ["investigation", id] })
        else setLive((all) => [...all.filter((s) => s.id !== event.id), event])
      },
      controller.signal,
    ).catch((e: Error) => controller.signal.aborted || toast.error(e.message))
    return () => controller.abort()
  }, [id, qc])

  const decide = useMutation({
    mutationFn: ({ action, decision }: { action: Action; decision: string }) =>
      api<Action>(`/api/investigations/${id}/actions/${action.id}/decision`, {
        method: "POST",
        body: JSON.stringify({ decision }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["investigation", id] }),
    onError: (e: Error) => toast.error(e.message),
  })

  if (detail.isPending) return <Skeleton className="h-64" />
  if (detail.error) return <p className="text-sm text-destructive">{detail.error.message}</p>
  const d = detail.data
  const findings = asList(d.state.findings)
  const citations = asList(d.state.citations)
  const canDecide = me.data?.role === "supervisor" || me.data?.role === "admin"

  return (
    <>
      <div className="flex flex-wrap items-center gap-3">
        <Button variant="outline" size="sm" asChild>
          <Link to="/investigations">Back</Link>
        </Button>
        <h2 className="text-lg font-semibold">Investigation #{d.id}</h2>
        <StatusBadge status={d.status} />
        <span className="text-sm text-muted-foreground">Scope: {Object.values(d.scope).join(" · ") || "none"}</span>
      </div>
      {d.degraded && (
        <div className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
          Degraded: the AI output failed validation, so a template summary is shown instead.
        </div>
      )}
      <Card>
        <CardHeader>
          <CardTitle>Incident #{d.incident.id}</CardTitle>
        </CardHeader>
        <CardContent className="text-sm">{d.incident.text}</CardContent>
      </Card>

      <h3 className="font-semibold">Steps</h3>
      <Timeline steps={live.length ? live : d.steps} />

      {(findings.length > 0 || citations.length > 0) && (
        <Card>
          <CardHeader>
            <CardTitle>Findings and cited guidance</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3 text-sm">
            <ul className="list-disc pl-5">
              {findings.map((f, i) => (
                <li key={i}>{typeof f === "string" ? f : JSON.stringify(f)}</li>
              ))}
            </ul>
            <div className="flex flex-wrap gap-2">
              {citations.map((c) => (
                <Badge key={citationKey(c)} variant="secondary">{citationKey(c)}</Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {d.actions.length > 0 && (
        <>
          <h3 className="font-semibold">Actions</h3>
          <Actions actions={d.actions} canDecide={canDecide} onDecide={(action, decision) => decide.mutate({ action, decision })} />
        </>
      )}

      {d.report && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Report</CardTitle>
            <Button size="sm" variant="outline" className="print:hidden" onClick={() => window.print()}>
              Print
            </Button>
          </CardHeader>
          <CardContent>
            <pre className="whitespace-pre-wrap font-sans text-sm">{d.report}</pre>
          </CardContent>
        </Card>
      )}
    </>
  )
}

export default function Investigations() {
  const { id } = useParams()
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">Investigations</h1>
        <p className="text-muted-foreground">Agent runs with live progress and approvals.</p>
      </div>
      {id ? <Detail id={id} /> : <List />}
    </div>
  )
}
