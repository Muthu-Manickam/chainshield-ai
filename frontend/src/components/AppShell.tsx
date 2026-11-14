import {
  BookOpen,
  Brain,
  ClipboardCheck,
  LayoutDashboard,
  LogOut,
  MessageSquare,
  Package,
  Settings,
  ShieldCheck,
  TriangleAlert,
} from "lucide-react"
import { NavLink, Outlet } from "react-router"
import { api } from "@/api"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import type { User } from "@/types"

const NAV = [
  { to: "/", label: "Overview", icon: LayoutDashboard },
  { to: "/orders", label: "Orders", icon: Package },
  { to: "/incidents", label: "Incidents", icon: TriangleAlert },
  { to: "/investigations", label: "Investigations", icon: ClipboardCheck },
  { to: "/assistant", label: "Assistant", icon: MessageSquare },
  { to: "/knowledge", label: "Knowledge", icon: BookOpen },
  { to: "/models", label: "Models", icon: Brain },
  { to: "/admin", label: "Admin", icon: Settings, adminOnly: true },
]

export default function AppShell({ user }: { user: User }) {
  const logout = () =>
    api("/api/auth/logout", { method: "POST" }).then(() => window.location.assign("/login"))

  return (
    <div className="flex min-h-screen">
      <aside className="flex w-60 shrink-0 flex-col gap-8 border-r bg-card p-4">
        <div className="flex items-center gap-2 px-2 pt-2 text-lg font-semibold tracking-tight">
          <ShieldCheck className="size-6" />
          ChainShield AI
        </div>
        <nav className="flex flex-col gap-1">
          {NAV.filter((item) => !item.adminOnly || user.role === "admin").map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                  isActive ? "bg-accent text-accent-foreground" : "text-muted-foreground hover:bg-accent"
                }`
              }
            >
              <Icon className="size-4" />
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-16 items-center justify-end gap-3 border-b px-8">
          <span className="text-sm text-muted-foreground">{user.email}</span>
          <Badge variant="secondary" className="capitalize">
            {user.role}
          </Badge>
          <Button variant="ghost" size="sm" onClick={logout}>
            <LogOut />
            Log out
          </Button>
        </header>
        <main className="flex-1 bg-muted/30 p-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
