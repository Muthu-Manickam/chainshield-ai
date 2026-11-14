import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { type FormEvent, useEffect, useState } from "react"
import { useOutletContext } from "react-router"
import { api } from "@/api"
import OptionSelect from "@/components/OptionSelect"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import type { Document, Job, SearchResult, User } from "@/types"

const ORIGINS = ["team-authored", "public"]

function Upload() {
  const qc = useQueryClient()
  const [code, setCode] = useState("")
  const [title, setTitle] = useState("")
  const [origin, setOrigin] = useState("team-authored")
  const [file, setFile] = useState<File | null>(null)
  const [jobId, setJobId] = useState<number | null>(null)

  const upload = useMutation({
    mutationFn: (form: FormData) => api<Job>("/api/knowledge/documents", { method: "POST", body: form }),
    onSuccess: (job) => setJobId(job.id),
  })
  const job = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => api<Job>(`/api/jobs/${jobId}`),
    enabled: jobId !== null,
    refetchInterval: (q) => (q.state.data?.status === "queued" || q.state.data?.status === "running" ? 1000 : false),
  })

  const finished = job.data?.status === "done" || job.data?.status === "failed"
  useEffect(() => {
    if (finished) qc.invalidateQueries({ queryKey: ["documents"] })
  }, [finished, qc])

  const submit = (e: FormEvent) => {
    e.preventDefault()
    const form = new FormData()
    form.append("file", file!)
    form.append("code", code)
    form.append("title", title)
    form.append("origin", origin)
    upload.mutate(form)
  }

  return (
    <Card className="p-4">
      <form onSubmit={submit} className="flex flex-wrap items-center gap-3">
        <Input className="w-32" placeholder="Code" value={code} onChange={(e) => setCode(e.target.value)} required />
        <Input className="w-64" placeholder="Title" value={title} onChange={(e) => setTitle(e.target.value)} required />
        <OptionSelect className="w-40" options={ORIGINS} value={origin} onChange={setOrigin} />
        <Input className="w-64" type="file" onChange={(e) => setFile(e.target.files?.[0] ?? null)} required />
        <Button type="submit" disabled={!file || upload.isPending}>
          Upload
        </Button>
        {job.data && (
          <Badge variant={job.data.status === "failed" ? "destructive" : "secondary"}>
            {job.data.status}
            {job.data.error && `: ${job.data.error}`}
          </Badge>
        )}
        {upload.error && <span className="text-sm text-destructive">{upload.error.message}</span>}
      </form>
    </Card>
  )
}

export default function Knowledge() {
  const user = useOutletContext<User>()
  const [q, setQ] = useState("")
  const documents = useQuery({
    queryKey: ["documents"],
    queryFn: () => api<Document[]>("/api/knowledge/documents"),
    refetchInterval: (query) => (query.state.data?.some((d) => d.status === "processing") ? 2000 : false),
  })
  const search = useMutation({
    mutationFn: (query: string) => api<SearchResult>(`/api/knowledge/search?q=${encodeURIComponent(query)}`),
  })

  const submit = (e: FormEvent) => {
    e.preventDefault()
    if (q.trim()) search.mutate(q.trim())
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">Knowledge</h1>
        <p className="text-muted-foreground">Search the cited guidance library.</p>
      </div>

      <form onSubmit={submit} className="flex gap-2">
        <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="e.g. port closure" />
        <Button type="submit" disabled={search.isPending}>
          Search
        </Button>
      </form>
      {search.error && <p className="text-sm text-destructive">{search.error.message}</p>}
      {search.data?.evidence_gap && (
        <Card className="border-destructive/50 bg-destructive/5 p-4 text-sm">
          <span className="font-medium text-destructive">Evidence gap.</span> No guidance found for this query
          {search.data.best_score !== null && ` (best score ${search.data.best_score.toFixed(2)})`}.
        </Card>
      )}
      <div className="flex flex-col gap-3">
        {search.data?.chunks.map((c) => (
          <Card key={c.citation_key} className="gap-2 p-4">
            <div className="flex flex-wrap items-center gap-2">
              <Badge>{c.citation_key}</Badge>
              <span className="font-medium">{c.document_title}</span>
              {c.section && <span className="text-sm text-muted-foreground">{c.section}</span>}
              <Badge variant="outline" className="ml-auto tabular-nums">
                {c.score.toFixed(2)}
              </Badge>
            </div>
            <p className="text-sm">{c.text}</p>
          </Card>
        ))}
      </div>

      {user.role === "admin" && <Upload />}

      <h2 className="text-lg font-semibold tracking-tight">Documents</h2>
      {documents.isPending && <Skeleton className="h-40" />}
      {documents.error && <p className="text-sm text-destructive">{documents.error.message}</p>}
      {documents.data && (
        <Card className="py-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Code</TableHead>
                <TableHead>Title</TableHead>
                <TableHead>Origin</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Chunks</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {documents.data.map((d) => (
                <TableRow key={d.id}>
                  <TableCell>{d.code}</TableCell>
                  <TableCell>{d.title}</TableCell>
                  <TableCell>{d.origin}</TableCell>
                  <TableCell>
                    <Badge variant={d.status === "failed" ? "destructive" : "secondary"}>{d.status}</Badge>
                  </TableCell>
                  <TableCell className="text-right tabular-nums">{d.chunk_count}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}
    </div>
  )
}
