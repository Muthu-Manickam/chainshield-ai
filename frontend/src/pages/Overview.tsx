import { useQuery } from "@tanstack/react-query"
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts"
import { api } from "@/api"
import StatCard from "@/components/StatCard"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  type ChartConfig,
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart"
import { Skeleton } from "@/components/ui/skeleton"
import type { IncidentStats, OrderStats } from "@/types"

// The investigations stats route returns {by_status: {<status>: count}} (same shape as IncidentStats).
interface InvestigationStats {
  by_status?: Record<string, number>
}

// Each by_shipping_mode row: {shipping_mode, total, high, medium, low}.
interface ModeRisk {
  shipping_mode: string
  high: number
  medium: number
  low: number
}

const riskConfig = {
  high: { label: "High", color: "var(--chart-1)" },
  medium: { label: "Medium", color: "var(--chart-2)" },
  low: { label: "Low", color: "var(--chart-3)" },
} satisfies ChartConfig

const incidentConfig = { count: { label: "Incidents", color: "var(--chart-1)" } } satisfies ChartConfig

export default function Overview() {
  const orders = useQuery({ queryKey: ["orders", "stats"], queryFn: () => api<OrderStats>("/api/orders/stats") })
  const incidents = useQuery({
    queryKey: ["incidents", "stats"],
    queryFn: () => api<IncidentStats>("/api/incidents/stats"),
  })
  const investigations = useQuery({
    queryKey: ["investigations", "stats"],
    queryFn: () => api<InvestigationStats>("/api/investigations/stats"),
  })

  const error = orders.error ?? incidents.error ?? investigations.error
  if (error) return <p className="text-sm text-destructive">{error.message}</p>
  if (!orders.data || !incidents.data || !investigations.data) return <Skeleton className="h-96" />

  const status = investigations.data.by_status ?? {}
  const open = (status.running ?? 0) + (status.awaiting_approval ?? 0) + (status.reporting ?? 0)
  const byMode = orders.data.by_shipping_mode as unknown as ModeRisk[]
  const byLabel = Object.entries(incidents.data.by_label).map(([label, count]) => ({
    label: label.replaceAll("_", " "),
    count,
  }))

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">Overview</h1>
        <p className="text-muted-foreground">Risk, incident and investigation numbers at a glance.</p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Orders at risk" value={orders.data.by_band.high ?? 0} hint="High-risk band" />
        <StatCard label="Incidents to review" value={incidents.data.needs_review} hint="Awaiting an analyst" />
        <StatCard label="Open investigations" value={open} hint="Running, reporting or awaiting approval" />
        <StatCard label="Pending approvals" value={status.awaiting_approval ?? 0} hint="Waiting for a supervisor" />
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Risk by shipping mode</CardTitle>
            <CardDescription>Scored orders per risk band</CardDescription>
          </CardHeader>
          <CardContent>
            <ChartContainer config={riskConfig} className="h-72 w-full">
              <BarChart data={byMode}>
                <CartesianGrid vertical={false} />
                <XAxis dataKey="shipping_mode" tickLine={false} axisLine={false} />
                <YAxis tickLine={false} axisLine={false} />
                <ChartTooltip content={<ChartTooltipContent />} />
                <ChartLegend content={<ChartLegendContent />} />
                <Bar dataKey="high" stackId="risk" fill="var(--color-high)" />
                <Bar dataKey="medium" stackId="risk" fill="var(--color-medium)" />
                <Bar dataKey="low" stackId="risk" fill="var(--color-low)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ChartContainer>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Incidents by category</CardTitle>
            <CardDescription>Predicted or reviewed humanitarian label</CardDescription>
          </CardHeader>
          <CardContent>
            <ChartContainer config={incidentConfig} className="h-72 w-full">
              <BarChart data={byLabel} layout="vertical">
                <CartesianGrid horizontal={false} />
                <XAxis type="number" tickLine={false} axisLine={false} />
                <YAxis dataKey="label" type="category" width={110} tickLine={false} axisLine={false} />
                <ChartTooltip content={<ChartTooltipContent />} />
                <Bar dataKey="count" fill="var(--color-count)" radius={4} />
              </BarChart>
            </ChartContainer>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
