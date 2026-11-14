import { useQuery } from "@tanstack/react-query"
import { api } from "@/api"
import StatCard from "@/components/StatCard"
import { Badge } from "@/components/ui/badge"
import { Card } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import type { OrderRow, Page } from "@/types"

export default function Orders() {
  const orders = useQuery({
    queryKey: ["orders"],
    queryFn: () => api<Page<OrderRow>>("/api/orders?page_size=20"),
  })

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">Orders</h1>
        <p className="text-muted-foreground">Late-risk scores for open orders.</p>
      </div>
      {orders.isPending && <Skeleton className="h-64" />}
      {orders.error && <p className="text-sm text-destructive">{orders.error.message}</p>}
      {orders.data && (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            <StatCard label="Orders" value={orders.data.total} />
          </div>
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
                  <TableRow key={order.id}>
                    <TableCell>{order.order_id}</TableCell>
                    <TableCell>{order.order_date.slice(0, 10)}</TableCell>
                    <TableCell>{order.market}</TableCell>
                    <TableCell>{order.shipping_mode}</TableCell>
                    <TableCell className="text-right tabular-nums">{order.order_total.toFixed(2)}</TableCell>
                    <TableCell>{order.risk_band && <Badge variant="secondary">{order.risk_band}</Badge>}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>
        </>
      )}
    </div>
  )
}
