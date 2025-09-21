from fastapi import FastAPI
import httpx, os, statistics as stats
from datetime import datetime

app = FastAPI(title="copilot-v0")
TX_TOOL = os.getenv("TX_TOOL_URL", "http://transactions-tool.agents.svc.cluster.local:8080")

@app.get("/healthz")
def healthz():
    return {"ok": True}

def detect_subs(rows):
    subs, bym = [], {}
    for r in rows:
        m = (r.get("merchant") or r.get("description") or "?").strip()
        bym.setdefault(m, []).append(r)
    for m, txs in bym.items():
        amts = { round(float(t.get("amount", 0)), 2) for t in txs if t.get("amount") is not None }
        if len(amts) == 1 and len(txs) >= 3:
            dates = [t.get("timestamp") for t in txs if t.get("timestamp")]
            try:
                dates = sorted(datetime.fromisoformat(d) for d in dates)
            except Exception:
                continue
            if len(dates) >= 3:
                gaps = [(dates[i] - dates[i-1]).days for i in range(1, len(dates))]
                if gaps and 25 <= stats.median(gaps) <= 35:
                    subs.append({"merchant": m, "amount": list(amts)[0], "confidence": 0.75})
    return subs

@app.get("/v0/users/{uid}/opportunities")
async def opportunities(uid: str):
    async with httpx.AsyncClient(timeout=5) as c:
        r = await c.get(f"{TX_TOOL}/v1/users/{uid}/transactions")
        r.raise_for_status()
        txs = r.json()
    cards = []
    for s in detect_subs(txs):
        eab = round(s["amount"] * 12, 2)
        cards.append({
            "type": "subscription_candidate",
            "title": f"Possible subscription: {s['merchant']}",
            "message": f"Recurring £{s['amount']:.2f}/mo. Potential saving ~£{eab}/yr.",
            "confidence": s["confidence"],
            "actions": ["Keep", "Cancel", "Defer"]
        })
    return {"cards": cards}
