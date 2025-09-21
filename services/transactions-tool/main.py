from fastapi import FastAPI
import httpx, os
from typing import List, Dict

app = FastAPI(title="transactions-tool")

TX_API = os.getenv("TX_API_URL", "http://transactionhistory.boa.svc.cluster.local:8080")
BAL_API = os.getenv("BAL_API_URL", "http://balancereader.boa.svc.cluster.local:8080")
TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "10"))

async def get_json(client: httpx.AsyncClient, url: str):
    try:
        r = await client.get(url, timeout=TIMEOUT)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

async def discover_accounts(client: httpx.AsyncClient, uid: str) -> List[str]:
    # Try common Balance Reader shapes; return accountIds (e.g., "test user-checking")
    candidates = [
        f"{BAL_API}/balances/{uid}",
        f"{BAL_API}/balance/{uid}",
        f"{BAL_API}/api/balance/{uid}",
    ]
    for url in candidates:
        data = await get_json(client, url)
        if not data:
            continue
        ids: List[str] = []
        if isinstance(data, dict):
            if "accounts" in data and isinstance(data["accounts"], list):
                for a in data["accounts"]:
                    aid = (a.get("accountId") or a.get("id") or a.get("name"))
                    if aid:
                        ids.append(str(aid))
            if not ids:
                for key in ("accountId", "id", "name"):
                    if key in data and isinstance(data[key], (str, int)):
                        ids.append(str(data[key]))
        if ids:
            return ids
    return []

async def fetch_transactions(client: httpx.AsyncClient, account_id: str) -> List[Dict]:
    candidates = [
        f"{TX_API}/transactions?accountId={account_id}",
        f"{TX_API}/api/transactions?accountId={account_id}",
        f"{TX_API}/transactions/{account_id}",
        f"{TX_API}/api/transactions/{account_id}",
    ]
    for url in candidates:
        data = await get_json(client, url)
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and isinstance(data.get("transactions"), list):
            return data["transactions"]
    return []

@app.get("/healthz")
async def healthz():
    return {"ok": True}

@app.get("/v1/users/{uid}/transactions")
async def list_tx(uid: str):
    async with httpx.AsyncClient() as c:
        accounts = await discover_accounts(c, uid)
        all_txs: List[Dict] = []
        for aid in accounts:
            all_txs.extend(await fetch_transactions(c, aid))
    return all_txs  # empty list if nothing found

@app.get("/v1/users/{uid}/balance")
async def balance(uid: str):
    async with httpx.AsyncClient() as c:
        accounts = await discover_accounts(c, uid)
    return {"accounts": accounts}
