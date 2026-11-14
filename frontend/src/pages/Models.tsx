import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useEffect, useState } from "react"
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts"
import { toast } from "sonner"
import { api } from "@/api"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { type ChartConfig, ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import type { EvalRun, Job, ModelVersion, User } from "@/types"

const FAMILIES = {
  risk: ["lr", "xgb"],
  incident: ["tfidf", "bilstm", "distilbert"],
} as const
type Task = keyof typeof FAMILIES

const statusVariant = { champion: "default", candidate: "secondary", retired: "outline", rejected: "destructive" } as const
const loeoConfig = { macro_f1: { label: "Macro-F1", color: "var(--chart-1)" } } satisfies ChartConfig

// Eval metrics are free-form JSON: walk a path and return undefined when any step is missing.
function dig(value: unknown, ...path: string[]): unknown {
  return path.reduce<unknown>((v, key) => (v && typeof v === "object" ? (v as Record<string, unknown>)[key] : undefined), value)
}

function num(value: unknown): string {
  return typeof value === "number" ? value.toFixed(3) : "n/a"
}

function EvalTable({ columns, rows }: { columns: string[]; rows: (string | number | undefined)[][] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          {columns.map((column, i) => (
            <TableHead key={column} className={i ? "text-right" : ""}>
              {column}
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((row) => (
          <TableRow key={String(row[0])}>
            {row.map((cell, i) => (
              <TableCell key={i} className={i ? "text-right tabular-nums" : "font-medium"}>
                {typeof cell === "number" ? cell.toFixed(3) : (cell ?? "n/a")}
              </TableCell>
            ))}
          </TableRow>
        ))}
        {!rows.length && (
          <TableRow>
            <TableCell colSpan={columns.length} className="py-6 text-center text-muted-foreground">
              No evaluation results loaded.
            </TableCell>
          </TableRow>
        )}
      </TableBody>
    </Table>
  )
}

function RiskComparison({ runs }: { runs: EvalRun[] }) {
  const rows = runs.map((run) => [
    run.name,
    ...["val", "s3"].flatMap((set) => ["roc_auc", "pr_auc", "brier"].map((m) => dig(run.metrics, set, m) as number)),
  ])
  return (
    <Card>
      <CardHeader>
        <CardTitle>Risk models</CardTitle>
        <CardDescription>
          Block s1 is all LATAM and s3 (the promotion set) is all Europe, so s3 scores measure transfer across markets,
          not drift within one market.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <EvalTable
          columns={["Model", "Val ROC-AUC", "Val PR-AUC", "Val Brier", "S3 ROC-AUC", "S3 PR-AUC", "S3 Brier"]}
          rows={rows}
        />
      </CardContent>
    </Card>
  )
}

function TextComparison({ models, folds }: { models: EvalRun[]; folds: EvalRun[] }) {
  const rows = models.map((run) => {
    const m = dig(run.metrics, "dev") ?? run.metrics
    return [
      run.name,
      dig(m, "macro_f1") as number,
      dig(m, "per_class_recall", "infrastructure") as number,
      dig(m, "screening_f1") as number,
    ]
  })
  const loeo = folds.find((run) => run.name.startsWith("loeo"))
  const events = Object.entries((dig(loeo?.metrics, "macro_f1_by_event") ?? {}) as Record<string, number>).map(
    ([event, macro_f1]) => ({ event: event.replaceAll("_", " "), macro_f1 }),
  )
  const cascade = folds.find((run) => run.name === "cascade")?.metrics
  const cascadeRows = ["distilbert_alone", "bilstm_screen_then_distilbert"].map((key) => [
    key.replaceAll("_", " "),
    dig(cascade, key, "macro_f1") as number,
    dig(cascade, key, "humanitarian_suppressed") as number,
  ])

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader>
          <CardTitle>Incident text models</CardTitle>
          <CardDescription>Five-class humanitarian classification on the dev split.</CardDescription>
        </CardHeader>
        <CardContent>
          <EvalTable columns={["Model", "Macro-F1", "Infrastructure recall", "Screening F1"]} rows={rows} />
        </CardContent>
      </Card>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Leave-one-event-out</CardTitle>
            <CardDescription>
              {loeo ? `${loeo.name}: macro-F1 on each held-out event` : "No leave-one-event-out run loaded."}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ChartContainer config={loeoConfig} className="h-72 w-full">
              <BarChart data={events} layout="vertical" margin={{ left: 40 }}>
                <CartesianGrid horizontal={false} />
                <XAxis type="number" domain={[0, 1]} tickLine={false} axisLine={false} />
                <YAxis type="category" dataKey="event" tickLine={false} axisLine={false} width={130} />
                <ChartTooltip content={<ChartTooltipContent />} />
                <Bar dataKey="macro_f1" fill="var(--color-macro_f1)" radius={4} />
              </BarChart>
            </ChartContainer>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Screening cascade</CardTitle>
            <CardDescription>
              Humanitarian reports suppressed (out of {String(dig(cascade, "humanitarian_reports") ?? "n/a")}) when a
              screening stage runs first.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <EvalTable columns={["Pipeline", "Macro-F1", "Reports suppressed"]} rows={cascadeRows} />
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

// Headline numbers of one version: the promotion-set block of its metrics.json, narrowed to its own family.
function headline(v: ModelVersion): string {
  if (v.task === "risk") {
    const m = dig(v.metrics, "s3", v.family.replace("risk_", "")) ?? dig(v.metrics, "s3") ?? v.metrics
    return `ROC-AUC ${num(dig(m, "roc_auc"))} · PR-AUC ${num(dig(m, "pr_auc"))} · Brier ${num(dig(m, "brier"))}`
  }
  const m = dig(v.metrics, "pool_holdout") ?? dig(v.metrics, "dev") ?? v.metrics
  return `Macro-F1 ${num(dig(m, "macro_f1"))} · Infra recall ${num(dig(m, "per_class_recall", "infrastructure"))}`
}

function GateBadge({ gate }: { gate: ModelVersion["gate"] }) {
  const passed = dig(gate, "passed") ?? dig(gate, "ok")
  if (typeof passed !== "boolean") return <span className="text-muted-foreground">n/a</span>
  const failed = Object.entries(gate ?? {}).filter(([, v]) => v === false && v !== passed).map(([k]) => k)
  return (
    <div className="flex flex-col items-start gap-1">
      <Badge variant={passed ? "outline" : "destructive"}>{passed ? "Pass" : "Fail"}</Badge>
      {!passed && failed.length > 0 && <span className="text-xs text-muted-foreground">{failed.join(", ")}</span>}
    </div>
  )
}

function Versions({ task, versions, isAdmin, onPromote }: {
  task: Task
  versions: ModelVersion[]
  isAdmin: boolean
  onPromote: (version: ModelVersion) => void
}) {
  const champion = versions.find((v) => v.status === "champion")
  return (
    <Card className="py-0">
      <CardHeader className="pt-6">
        <CardTitle className="capitalize">{task} model versions</CardTitle>
      </CardHeader>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Version</TableHead>
            <TableHead>Family</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Metrics</TableHead>
            <TableHead>Gate</TableHead>
            {isAdmin && <TableHead />}
          </TableRow>
        </TableHeader>
        <TableBody>
          {versions.map((v) => (
            <TableRow key={v.id}>
              <TableCell className="font-medium">v{v.version}</TableCell>
              <TableCell>{v.family}</TableCell>
              <TableCell>
                <Badge variant={statusVariant[v.status]}>{v.status}</Badge>
              </TableCell>
              <TableCell className="tabular-nums">{headline(v)}</TableCell>
              <TableCell>
                <GateBadge gate={v.gate} />
              </TableCell>
              {isAdmin && (
                <TableCell className="text-right">
                  {v.status !== "champion" && v.status !== "rejected" && (
                    <Button size="sm" variant="outline" onClick={() => onPromote(v)}>
                      {champion && v.version < champion.version ? "Roll back" : "Promote"}
                    </Button>
                  )}
                </TableCell>
              )}
            </TableRow>
          ))}
          {!versions.length && (
            <TableRow>
              <TableCell colSpan={isAdmin ? 6 : 5} className="py-6 text-center text-muted-foreground">
                No versions registered.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </Card>
  )
}

function Retrain({ onDone }: { onDone: () => void }) {
  const [task, setTask] = useState<Task>("risk")
  const [family, setFamily] = useState<string>(FAMILIES.risk[1])
  const [jobId, setJobId] = useState<number | null>(null)
  const start = useMutation({
    mutationFn: () => api<Job>("/api/models/retrain", { method: "POST", body: JSON.stringify({ task, family }) }),
    onSuccess: (job) => setJobId(job.id),
    onError: (e: Error) => toast.error(e.message),
  })
  const job = useQuery({
    queryKey: ["jobs", jobId],
    queryFn: () => api<Job>(`/api/jobs/${jobId}`),
    enabled: jobId !== null,
    refetchInterval: (query) => (["done", "failed"].includes(query.state.data?.status ?? "") ? false : 2000),
  })
  const status = job.data?.status
  const finished = status === "done" || status === "failed"
  useEffect(() => {
    if (finished) onDone()
  }, [finished]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="flex flex-wrap items-center gap-2">
      <Select
        value={task}
        onValueChange={(value) => {
          setTask(value as Task)
          setFamily(FAMILIES[value as Task][0])
        }}
      >
        <SelectTrigger className="w-32 bg-background">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {Object.keys(FAMILIES).map((t) => (
            <SelectItem key={t} value={t} className="capitalize">
              {t}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Select value={family} onValueChange={setFamily}>
        <SelectTrigger className="w-36 bg-background">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {FAMILIES[task].map((f) => (
            <SelectItem key={f} value={f}>
              {f}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Button variant="outline" disabled={start.isPending || (jobId !== null && !finished)} onClick={() => start.mutate()}>
        Retrain
      </Button>
      {jobId !== null && (
        <span className="text-sm text-muted-foreground">
          Job {jobId}: {status ?? "queued"}
          {job.data?.error && <span className="text-destructive"> ({job.data.error})</span>}
        </span>
      )}
    </div>
  )
}

export default function Models() {
  const queryClient = useQueryClient()
  const [confirm, setConfirm] = useState<ModelVersion | null>(null)
  const [block, setBlock] = useState("s1")
  const me = useQuery({ queryKey: ["me"], queryFn: () => api<User>("/api/auth/me") })
  const isAdmin = me.data?.role === "admin"
  const models = useQuery({ queryKey: ["models"], queryFn: () => api<ModelVersion[]>("/api/models") })
  const risk = useQuery({ queryKey: ["evals", "risk_models"], queryFn: () => api<EvalRun[]>("/api/evals?kind=risk_models") })
  const incident = useQuery({
    queryKey: ["evals", "incident_models"],
    queryFn: () => api<EvalRun[]>("/api/evals?kind=incident_models"),
  })
  const folds = useQuery({
    queryKey: ["evals", "incident_folds"],
    queryFn: () => api<EvalRun[]>("/api/evals?kind=incident_folds"),
  })

  const refresh = () => queryClient.invalidateQueries({ queryKey: ["models"] })
  const release = useMutation({
    mutationFn: () => api<{ released: number }>("/api/models/release-batch", { method: "POST", body: JSON.stringify({ block }) }),
    onSuccess: (data) => {
      toast.success(`Released ${data.released} orders from ${block}`)
      refresh()
    },
    onError: (e: Error) => toast.error(e.message),
  })
  const promote = useMutation({
    mutationFn: (id: number) => api<ModelVersion>(`/api/models/${id}/promote`, { method: "POST" }),
    onSuccess: (v) => {
      toast.success(`${v.task} v${v.version} is now champion`)
      setConfirm(null)
      refresh()
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const error = models.error ?? risk.error ?? incident.error ?? folds.error
  const byTask = (task: Task) => (models.data ?? []).filter((v) => v.task === task).sort((a, b) => b.version - a.version)
  const rollback = confirm && byTask(confirm.task).find((v) => v.status === "champion")
  const isRollback = !!rollback && !!confirm && confirm.version < rollback.version

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">Models</h1>
        <p className="text-muted-foreground">Model comparison, versions, retraining and promotion.</p>
      </div>
      {isAdmin && (
        <Card>
          <CardContent className="flex flex-wrap items-center gap-x-8 gap-y-3">
            <div className="flex items-center gap-2">
              <Select value={block} onValueChange={setBlock}>
                <SelectTrigger className="w-24 bg-background">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="s1">s1</SelectItem>
                  <SelectItem value="s2">s2</SelectItem>
                </SelectContent>
              </Select>
              <Button variant="outline" disabled={release.isPending} onClick={() => release.mutate()}>
                Release next batch
              </Button>
            </div>
            <Retrain onDone={refresh} />
          </CardContent>
        </Card>
      )}
      {error && <p className="text-sm text-destructive">{error.message}</p>}
      {models.isPending ? (
        <Skeleton className="h-64" />
      ) : (
        <div className="grid gap-4">
          <Versions task="risk" versions={byTask("risk")} isAdmin={isAdmin} onPromote={setConfirm} />
          <Versions task="incident" versions={byTask("incident")} isAdmin={isAdmin} onPromote={setConfirm} />
        </div>
      )}
      <RiskComparison runs={risk.data ?? []} />
      <TextComparison models={incident.data ?? []} folds={folds.data ?? []} />
      <Dialog open={confirm !== null} onOpenChange={(open) => !open && setConfirm(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {isRollback ? "Roll back" : "Promote"} {confirm?.task} v{confirm?.version}?
            </DialogTitle>
            <DialogDescription>
              {confirm?.family} becomes the champion and scores new orders and incidents from now on. The current champion
              (v{rollback?.version ?? "none"}) is retired.
              {isRollback && " This version is older than the current champion."}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirm(null)}>
              Cancel
            </Button>
            <Button disabled={promote.isPending} onClick={() => confirm && promote.mutate(confirm.id)}>
              Confirm
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
