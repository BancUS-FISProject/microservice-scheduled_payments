const http = require("http")

const server = http.createServer(async (req, res) => {
  if (req.method === "POST" && req.url === "/v1/transactions") {
    res.writeHead(201, { "Content-Type": "application/json" })
    return res.end(JSON.stringify({ status: "ok" }))
  }
  res.writeHead(404, { "Content-Type": "application/json" })
  res.end(JSON.stringify({ error: "not found" }))
})

server.listen(8000, () => console.log("transfers mock on :8000"))
