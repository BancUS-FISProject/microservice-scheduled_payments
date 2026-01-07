import { startBackendInProcess, waitForHealthy, sleep } from "./helpers.js"

const BASE = "http://localhost:8000/v1/scheduled-payments"

const target = process.env.JEST_TARGET || "inprocess"
let backendProc = null

beforeAll(async () => {
  if (target === "inprocess") {
    backendProc = startBackendInProcess({
      MONGO_CONNECTION_STRING: "mongodb://localhost:27017",
      MONGO_DATABASE_NAME: "scheduled_payments",
      TRANSFER_SERVICE_URL: "http://localhost:8002/v1/transactions",
      ACCOUNTS_SERVICE_URL: "http://localhost:8001/v1/account/{iban}",
      SUBSCRIPTION_BASIC: "1",
      SUBSCRIPTION_STUDENT: "10",
      SUBSCRIPTION_PRO: "999999999",
      LOG_LEVEL: "INFO",
      LOG_FILE: "log.txt",
      LOG_BACKUP_COUNT: "7",
      NTP_SERVER: "pool.ntp.org",
      NTP_REFRESH_SECONDS: "60",
      NTP_TIMEOUT_SECONDS: "3",
      SCHEDULER_INTERVAL_SECONDS: "60"
    })

    await waitForHealthy(`${BASE}/health`)
  } else {
    await waitForHealthy(`${BASE}/health`)
  }
}, 60_000)

afterAll(async () => {
  if (backendProc) {
    backendProc.kill("SIGTERM")
    await sleep(500)
  }
})

test("GET /health -> ok", async () => {
  const res = await fetch(`${BASE}/health`)
  expect(res.status).toBe(200)
  const data = await res.json()
  expect(data.status).toBe("ok")
})

test("POST crea pago para cuenta basico (1 permitido) y el 2º da 403", async () => {
  const accountId = "ES_BASIC_123"

  const payload = {
    accountId,
    description: "Pago prueba 1",
    beneficiary: { name: "Pepe", iban: "ESBENEF_1" },
    amount: { value: 10, currency: "EUR" },
    schedule: { frequency: "ONCE", executionDate: new Date(Date.now() + 3600_000).toISOString() }
  }

  const r1 = await fetch(`${BASE}/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  })
  expect([200, 201]).toContain(r1.status)

  const r2 = await fetch(`${BASE}/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...payload, id: crypto.randomUUID(), description: "Pago prueba 2" })
  })

  expect(r2.status).toBe(403)
  const err = await r2.json()
  expect(err.error).toMatch(/Límite/i)
})

test("POST con cuenta inexistente -> 404", async () => {
  const payload = {
    accountId: "NO_EXISTE",
    description: "Pago cuenta inexistente",
    beneficiary: { name: "Ana", iban: "ESBENEF_2" },
    amount: { value: 5, currency: "EUR" },
    schedule: { frequency: "ONCE", executionDate: new Date(Date.now() + 3600_000).toISOString() }
  }

  const res = await fetch(`${BASE}/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  })

  expect(res.status).toBe(404)
})

test("GET /accounts/{iban} devuelve array (aunque esté vacío)", async () => {
  const accountId = "ES_SIN_PAGOS_000"
  const res = await fetch(`${BASE}/accounts/${accountId}`)
  expect(res.status).toBe(200)
  const data = await res.json()
  expect(Array.isArray(data)).toBe(true)
})

test("GET /accounts/{iban}/upcoming valida limit", async () => {
  const accountId = "ES_PRO_777_PRO"
  const res = await fetch(`${BASE}/accounts/${accountId}/upcoming?limit=aaa`)
  expect(res.status).toBe(400)
})
