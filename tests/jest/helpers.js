import { spawn } from "child_process"
import path from "path"

export function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms))
}

export async function waitForHealthy(url, retries = 30) {
  for (let i = 0; i < retries; i++) {
    try {
      const res = await fetch(url)
      if (res.ok) return true
    } catch {}
    await sleep(500)
  }
  throw new Error(`Service not healthy at ${url}`)
}

export function startBackendInProcess(envOverrides = {}) {
  const srcPath = path.join(process.cwd(), "src")
  const prev = process.env.PYTHONPATH || ""
  const mergedPyPath = prev ? `${srcPath}${path.delimiter}${prev}` : srcPath

  const env = {
    ...process.env,
    PYTHONPATH: mergedPyPath,
    ...envOverrides,
  }

  const p = spawn(
    "hypercorn",
    ["scheduled_payments.app:app", "--bind", "0.0.0.0:8000"],
    { env, stdio: "inherit" }
  )

  return p
}
