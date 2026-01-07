const http = require("http")

const server = http.createServer((req, res) => {
  if (req.method === "GET" && req.url.startsWith("/v1/account/")) {
    const iban = decodeURIComponent(req.url.split("/").pop() || "")

    if (iban === "NO_EXISTE") {
      res.writeHead(404, { "Content-Type": "application/json" })
      return res.end(JSON.stringify({ error: "Account not found" }))
    }

    let subscription = "basico"
    if (iban.includes("STUDENT")) subscription = "estudiante"
    if (iban.includes("PRO")) subscription = "pro"

    res.writeHead(200, { "Content-Type": "application/json" })
    return res.end(JSON.stringify({ iban, subscription }))
  }

  res.writeHead(404, { "Content-Type": "application/json" })
  res.end(JSON.stringify({ error: "not found" }))
})

server.listen(8000, () => console.log("accounts mock on :8000"))
