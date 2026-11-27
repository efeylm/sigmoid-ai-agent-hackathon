"use client"

import { useCallback, useEffect, useState } from "react"
import { KeyRound, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  ACCESS_INVALID_EVENT,
  getAccessCode,
  isAccessCodeRequired,
  setAccessCode,
  verifyAccessCode,
} from "@/lib/api/access"

type GateState = "checking" | "locked" | "open" | "offline"

/**
 * Shows an access code screen until the visitor enters a valid code.
 * A code can also be passed in the URL (?code=XXXX) so a shared link unlocks directly.
 */
export function AccessGate({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<GateState>("checking")
  const [code, setCode] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const check = useCallback(async () => {
    setState("checking")
    try {
      if (!(await isAccessCodeRequired())) {
        setState("open")
        return
      }

      // Code from a shared link takes priority, then strip it from the URL
      const url = new URL(window.location.href)
      const fromUrl = url.searchParams.get("code")
      if (fromUrl) {
        url.searchParams.delete("code")
        window.history.replaceState(null, "", url.toString())
      }

      const candidate = fromUrl || getAccessCode()
      if (candidate && (await verifyAccessCode(candidate))) {
        setAccessCode(candidate)
        setState("open")
      } else {
        setState("locked")
      }
    } catch {
      setState("offline")
    }
  }, [])

  useEffect(() => {
    check()
    const onInvalid = () => {
      setError("Erişim kodunuz artık geçerli değil. Lütfen yeni kodu girin.")
      setState("locked")
    }
    window.addEventListener(ACCESS_INVALID_EVENT, onInvalid)
    return () => window.removeEventListener(ACCESS_INVALID_EVENT, onInvalid)
  }, [check])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = code.trim()
    if (!trimmed) return
    setSubmitting(true)
    setError(null)
    try {
      if (await verifyAccessCode(trimmed)) {
        setAccessCode(trimmed)
        setState("open")
      } else {
        setError("Kod hatalı. Lütfen tekrar deneyin.")
      }
    } catch {
      setError("Sunucuya ulaşılamadı. Lütfen biraz sonra tekrar deneyin.")
    } finally {
      setSubmitting(false)
    }
  }

  if (state === "open") return <>{children}</>

  return (
    <div className="min-h-screen bg-[#151a30] text-white flex items-center justify-center px-4">
      <div className="w-full max-w-sm rounded-xl border border-white/10 bg-[#0a0e1a] p-8 shadow-xl">
        {state === "checking" ? (
          <div className="flex flex-col items-center gap-3 text-gray-400">
            <Loader2 className="h-6 w-6 animate-spin" />
            <span>Yükleniyor...</span>
          </div>
        ) : state === "offline" ? (
          <div className="flex flex-col items-center gap-4 text-center">
            <p className="text-gray-300">Sunucuya şu anda ulaşılamıyor.</p>
            <Button onClick={check} variant="outline" className="text-black">
              Tekrar dene
            </Button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="flex flex-col items-center gap-2 text-center">
              <div className="rounded-full bg-white/10 p-3">
                <KeyRound className="h-6 w-6" />
              </div>
              <h1 className="text-xl font-semibold">Erişim kodu gerekli</h1>
              <p className="text-sm text-gray-400">
                Bu demo yalnızca erişim koduna sahip kişilere açıktır.
              </p>
            </div>
            <Input
              type="password"
              autoFocus
              autoComplete="off"
              placeholder="Erişim kodu"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              className="bg-white/5 border-white/20 text-white placeholder:text-gray-500"
            />
            {error && <p className="text-sm text-red-400">{error}</p>}
            <Button type="submit" disabled={submitting || !code.trim()} className="bg-orange-600 text-white hover:bg-orange-700">
              {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : "Devam et"}
            </Button>
          </form>
        )}
      </div>
    </div>
  )
}
