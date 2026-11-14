import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"
import { toast } from "sonner"
import { api } from "@/api"
import OptionSelect from "@/components/OptionSelect"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import type { ActionRule, AuditEntry, Role, User } from "@/types"

const ROLES: Role[] = ["analyst", "supervisor", "admin"]

function ActiveButton({ active, onClick }: { active: boolean; onClick: () => void }) {
  return (
    <Button size="sm" variant={active ? "secondary" : "outline"} onClick={onClick}>
      {active ? "Active" : "Inactive"}
    </Button>
  )
}

function useSave(path: (id: number) => string, method: string, key: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: unknown }) =>
      api<unknown>(path(id), { method, body: JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: [key] }),
    onError: (e: Error) => toast.error(e.message),
  })
}

function CreateUser() {
  const qc = useQueryClient()
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState({ email: "", password: "", role: "analyst" as Role })
  const create = useMutation({
    mutationFn: () => api<User>("/api/users", { method: "POST", body: JSON.stringify(form) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["users"] })
      setOpen(false)
      setForm({ email: "", password: "", role: "analyst" })
    },
    onError: (e: Error) => toast.error(e.message),
  })
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>Create user</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create user</DialogTitle>
        </DialogHeader>
        <div className="flex flex-col gap-3">
          <Input placeholder="Email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          <Input
            type="password"
            placeholder="Password"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
          />
          <OptionSelect size="sm" className="w-36" options={ROLES} value={form.role} onChange={(role) => setForm({ ...form, role: role as Role })} />
        </div>
        <DialogFooter>
          <Button disabled={!form.email || !form.password || create.isPending} onClick={() => create.mutate()}>
            Create
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function Users() {
  const users = useQuery({ queryKey: ["users"], queryFn: () => api<User[]>("/api/users") })
  const save = useSave((id) => `/api/users/${id}`, "PATCH", "users")
  return (
    <div className="flex flex-col gap-4">
      <div className="flex justify-end">
        <CreateUser />
      </div>
      {users.isPending && <Skeleton className="h-48" />}
      {users.error && <p className="text-sm text-destructive">{users.error.message}</p>}
      {users.data && (
        <Card className="py-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Email</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {users.data.map((u) => (
                <TableRow key={u.id}>
                  <TableCell>{u.email}</TableCell>
                  <TableCell>
                    <OptionSelect size="sm" className="w-36" options={ROLES} value={u.role} onChange={(role) => save.mutate({ id: u.id, body: { role } })} />
                  </TableCell>
                  <TableCell>
                    <ActiveButton
                      active={u.is_active}
                      onClick={() => save.mutate({ id: u.id, body: { is_active: !u.is_active } })}
                    />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}
    </div>
  )
}

function RuleRow({ rule }: { rule: ActionRule }) {
  const save = useSave((id) => `/api/rules/${id}`, "PUT", "rules")
  const [cost, setCost] = useState(String(rule.cost_usd))
  const update = (body: Partial<ActionRule>) => save.mutate({ id: rule.id, body })
  const changed = Number(cost) !== rule.cost_usd
  return (
    <TableRow>
      <TableCell>
        <div className="font-medium">{rule.name}</div>
        <div className="text-xs text-muted-foreground">{rule.code.replaceAll("_", " ")}</div>
      </TableCell>
      <TableCell>
        <div className="flex gap-2">
          <Input type="number" min={0} className="h-8 w-28" value={cost} onChange={(e) => setCost(e.target.value)} />
          <Button size="sm" variant="outline" disabled={!changed || cost === ""} onClick={() => update({ cost_usd: Number(cost) })}>
            Save
          </Button>
        </div>
      </TableCell>
      <TableCell>
        <OptionSelect size="sm" className="w-36" options={ROLES} value={rule.approval_role} onChange={(role) => update({ approval_role: role as Role })} />
      </TableCell>
      <TableCell>
        <ActiveButton active={rule.is_active} onClick={() => update({ is_active: !rule.is_active })} />
      </TableCell>
    </TableRow>
  )
}

function Rules() {
  const rules = useQuery({ queryKey: ["rules"], queryFn: () => api<ActionRule[]>("/api/rules") })
  if (rules.isPending) return <Skeleton className="h-48" />
  if (rules.error) return <p className="text-sm text-destructive">{rules.error.message}</p>
  return (
    <Card className="py-0">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Rule</TableHead>
            <TableHead>Cost (USD)</TableHead>
            <TableHead>Approval role</TableHead>
            <TableHead>Status</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rules.data.map((r) => (
            <RuleRow key={r.id} rule={r} />
          ))}
        </TableBody>
      </Table>
    </Card>
  )
}

function Audit() {
  const audit = useQuery({ queryKey: ["audit"], queryFn: () => api<AuditEntry[]>("/api/users/audit") })
  if (audit.isPending) return <Skeleton className="h-48" />
  if (audit.error) return <p className="text-sm text-destructive">{audit.error.message}</p>
  return (
    <Card className="py-0">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Time</TableHead>
            <TableHead>User</TableHead>
            <TableHead>Action</TableHead>
            <TableHead>Entity</TableHead>
            <TableHead>Detail</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {audit.data.map((a) => (
            <TableRow key={a.id}>
              <TableCell className="whitespace-nowrap text-muted-foreground">
                {new Date(a.created_at).toLocaleString()}
              </TableCell>
              <TableCell>{a.user_email ?? a.user_id ?? "system"}</TableCell>
              <TableCell>
                <Badge variant="secondary">{a.action.replaceAll("_", " ")}</Badge>
              </TableCell>
              <TableCell>
                {a.entity.replaceAll("_", " ")}
                {a.entity_id && ` #${a.entity_id}`}
              </TableCell>
              <TableCell className="max-w-sm truncate font-mono text-xs text-muted-foreground">
                {a.detail ? JSON.stringify(a.detail) : ""}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Card>
  )
}

export default function Admin() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">Admin</h1>
        <p className="text-muted-foreground">Users, action rules and audit log.</p>
      </div>
      <Tabs defaultValue="users">
        <TabsList>
          <TabsTrigger value="users">Users</TabsTrigger>
          <TabsTrigger value="rules">Action rules</TabsTrigger>
          <TabsTrigger value="audit">Audit log</TabsTrigger>
        </TabsList>
        <TabsContent value="users">
          <Users />
        </TabsContent>
        <TabsContent value="rules">
          <Rules />
        </TabsContent>
        <TabsContent value="audit">
          <Audit />
        </TabsContent>
      </Tabs>
    </div>
  )
}
