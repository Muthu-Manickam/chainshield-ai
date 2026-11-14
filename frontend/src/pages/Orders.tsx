import { keepPreviousData, useQuery } from "@tanstack/react-query"
import { useState } from "react"
import { Link } from "react-router"
import { api } from "@/api"
import OptionSelect from "@/components/OptionSelect"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { type Band, MARKETS, type OrderDetail, type OrderRow, type Page, SHIPPING_MODES } from "@/types"

const BANDS: Band[] = ["high", "medium", "low"]
const PAGE_SIZE = 20

const bandVariant = { high: "destructive", medium: "secondary", low: "outline" } as const

function OrderDialog({ orderId, onClose }: { orderId: number | null; onClose: () => void }) {
  const order = useQuery({
    queryKey: ["orders", orderId],
    queryFn: () => api<OrderDetail>(`/api/orders/${orderId}`),
    enabled: orderId !== null,
  })
  const data = order.data
  const scope = data && JSON.stringify({ market: data.market, shipping_mode: data.shipping_mode })

  return (
    <Dialog open={orderId !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Order {data?.order_id ?? ""}</DialogTitle>
          <DialogDescription>
            {data ? `${data.market} · ${data.shipping_mode} · ${data.order_date.slice(0, 10)}` : "Loading order"}
          </DialogDescription>
        </DialogHeader>
        {order.isPending && <Skeleton className="h-40" />}
        {order.error && <p className="text-sm text-destructive">{order.error.message}</p>}
        {data && (
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-2">
              {data.risk_band && <Badge variant={bandVariant[data.risk_band]}>{data.risk_band} risk</Badge>}
              {data.risk_score !== null && (
                <span className="text-sm tabular-nums">{(data.risk_score * 100).toFixed(1)}% late probability</span>
              )}
              <span className="ml-auto text-sm text-muted-foreground">Model version {data.model_version_id ?? "n/a"}</span>
            </div>
            <div>
              <h3 className="mb-2 text-sm font-medium">Top factors</h3>
              <ul className="flex flex-col divide-y rounded-md border text-sm">
                {(data.factors ?? []).map((factor) => (
                  <li key={factor.feature} className="flex justify-between px-3 py-2">
                    <span>
                      {factor.feature.replaceAll("_", " ")}
                      <span className="text-muted-foreground"> = {String(factor.value)}</span>
                    </span>
                    <span className="tabular-nums">
                      {factor.impact > 0 ? "+" : ""}
                      {factor.impact.toFixed(3)}
                    </span>
                  </li>
                ))}
                {!data.factors?.length && <li className="px-3 py-2 text-muted-foreground">No factors recorded.</li>}
              </ul>
            </div>
          </div>
        )}
        {scope && (
          <DialogFooter>
            <Button asChild>
              <Link to={`/investigations?scope=${encodeURIComponent(scope)}`}>Investigate this scope</Link>
            </Button>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  )
}

export default function Orders() {
  const [market, setMarket] = useState("all")
  const [mode, setMode] = useState("all")
  const [band, setBand] = useState("all")
  const [includeTrained, setIncludeTrained] = useState(false)
  const [draft, setDraft] = useState("")
  const [q, setQ] = useState("")
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState<number | null>(null)

  const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) })
  if (market !== "all") params.set("market", market)
  if (mode !== "all") params.set("shipping_mode", mode)
  if (band !== "all") params.set("band", band)
  if (q) params.set("q", q)
  if (includeTrained) params.set("include_trained", "true")

  const orders = useQuery({
    queryKey: ["orders", params.toString()],
    queryFn: () => api<Page<OrderRow>>(`/api/orders?${params}`),
    placeholderData: keepPreviousData,
  })

  // Any filter change returns to the first page.
  const filter = (set: (value: string) => void) => (value: string) => {
    set(value)
    setPage(1)
  }
  const pages = Math.max(1, Math.ceil((orders.data?.total ?? 0) / PAGE_SIZE))

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">Orders</h1>
        <p className="text-muted-foreground">Late-risk scores for open orders.</p>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <OptionSelect all="All markets" options={MARKETS} value={market} onChange={filter(setMarket)} />
        <OptionSelect all="All shipping modes" options={SHIPPING_MODES} value={mode} onChange={filter(setMode)} />
        <OptionSelect all="All bands" options={BANDS} value={band} onChange={filter(setBand)} />
        <form
          className="flex gap-2"
          onSubmit={(event) => {
            event.preventDefault()
            setQ(draft.trim())
            setPage(1)
          }}
        >
          <Input
            className="w-56 bg-background"
            placeholder="Search order id"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
          />
          <Button type="submit" variant="outline">
            Search
          </Button>
        </form>
        <Button
          variant={includeTrained ? "default" : "outline"}
          aria-pressed={includeTrained}
          onClick={() => {
            setIncludeTrained(!includeTrained)
            setPage(1)
          }}
        >
          Include trained
        </Button>
      </div>
      {orders.isPending && <Skeleton className="h-64" />}
      {orders.error && <p className="text-sm text-destructive">{orders.error.message}</p>}
      {orders.data && (
        <>
          <Card className="py-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Order</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead>Market</TableHead>
                  <TableHead>Shipping mode</TableHead>
                  <TableHead className="text-right">Total</TableHead>
                  <TableHead>Risk</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {orders.data.items.map((order) => (
                  <TableRow key={order.id} className="cursor-pointer" onClick={() => setSelected(order.order_id)}>
                    <TableCell>{order.order_id}</TableCell>
                    <TableCell>{order.order_date.slice(0, 10)}</TableCell>
                    <TableCell>{order.market}</TableCell>
                    <TableCell>{order.shipping_mode}</TableCell>
                    <TableCell className="text-right tabular-nums">{order.order_total.toFixed(2)}</TableCell>
                    <TableCell>
                      {order.risk_band && <Badge variant={bandVariant[order.risk_band]}>{order.risk_band}</Badge>}
                    </TableCell>
                  </TableRow>
                ))}
                {!orders.data.items.length && (
                  <TableRow>
                    <TableCell colSpan={6} className="py-8 text-center text-muted-foreground">
                      No orders match these filters.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </Card>
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <span>{orders.data.total} orders</span>
            <div className="flex items-center gap-3">
              <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>
                Previous
              </Button>
              <span>
                Page {page} of {pages}
              </span>
              <Button variant="outline" size="sm" disabled={page >= pages} onClick={() => setPage(page + 1)}>
                Next
              </Button>
            </div>
          </div>
        </>
      )}
      <OrderDialog orderId={selected} onClose={() => setSelected(null)} />
    </div>
  )
}
