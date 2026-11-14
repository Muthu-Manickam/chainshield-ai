import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"
import { ShieldCheck } from "lucide-react"
import { api } from "@/api"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import type { User } from "@/types"

export default function Login() {
  const queryClient = useQueryClient()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const login = useMutation({
    mutationFn: () =>
      api<User>("/api/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
    onSuccess: (user) => queryClient.setQueryData(["me"], user),
  })

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/30 p-6">
      <Card className="w-full max-w-sm">
        <CardHeader className="items-center text-center">
          <ShieldCheck className="size-8" />
          <CardTitle className="text-xl">ChainShield AI</CardTitle>
          <CardDescription>Sign in to continue</CardDescription>
        </CardHeader>
        <CardContent>
          <form
            className="flex flex-col gap-4"
            onSubmit={(e) => {
              e.preventDefault()
              login.mutate()
            }}
          >
            <label className="flex flex-col gap-2 text-sm font-medium">
              Email
              <Input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
            </label>
            <label className="flex flex-col gap-2 text-sm font-medium">
              Password
              <Input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </label>
            {login.error && <p className="text-sm text-destructive">{login.error.message}</p>}
            <Button type="submit" disabled={login.isPending}>
              Sign in
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
