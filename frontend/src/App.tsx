import { useQuery } from "@tanstack/react-query"
import { Navigate, Route, Routes } from "react-router"
import { api } from "@/api"
import AppShell from "@/components/AppShell"
import { Skeleton } from "@/components/ui/skeleton"
import Admin from "@/pages/Admin"
import Assistant from "@/pages/Assistant"
import Incidents from "@/pages/Incidents"
import Investigations from "@/pages/Investigations"
import Knowledge from "@/pages/Knowledge"
import Login from "@/pages/Login"
import Models from "@/pages/Models"
import Orders from "@/pages/Orders"
import Overview from "@/pages/Overview"
import type { User } from "@/types"

export default function App() {
  const { data: user, isPending } = useQuery({
    queryKey: ["me"],
    queryFn: () => api<User>("/api/auth/me"),
    retry: false,
  })

  if (isPending) return <Skeleton className="m-8 h-64" />

  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/" replace /> : <Login />} />
      <Route element={user ? <AppShell user={user} /> : <Navigate to="/login" replace />}>
        <Route index element={<Overview />} />
        <Route path="orders" element={<Orders />} />
        <Route path="incidents" element={<Incidents />} />
        <Route path="investigations" element={<Investigations />} />
        <Route path="investigations/:id" element={<Investigations />} />
        <Route path="assistant" element={<Assistant />} />
        <Route path="knowledge" element={<Knowledge />} />
        <Route path="models" element={<Models />} />
        <Route
          path="admin"
          element={user?.role === "admin" ? <Admin /> : <Navigate to="/" replace />}
        />
      </Route>
    </Routes>
  )
}
