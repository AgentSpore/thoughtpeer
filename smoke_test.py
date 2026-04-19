"""Smoke test — register, login, hit every endpoint."""

import asyncio
import io
import json
import secrets
import sys

import httpx

BASE = "http://localhost:8000"


async def main():
    async with httpx.AsyncClient(base_url=BASE, timeout=15) as c:
        ok = 0
        fail = 0
        headers: dict[str, str] = {}

        async def check(name: str, method: str, path: str, **kwargs):
            nonlocal ok, fail
            expected = kwargs.pop("expected", [200, 201])
            kwargs.setdefault("headers", {}).update(headers)
            try:
                r = await getattr(c, method)(path, **kwargs)
                if r.status_code in expected:
                    print(f"  OK  {name} ({r.status_code})")
                    ok += 1
                    try:
                        return r.json() if r.content else None
                    except Exception:
                        return None
                else:
                    print(f"  FAIL {name} — {r.status_code}: {r.text[:200]}")
                    fail += 1
            except Exception as e:
                print(f"  FAIL {name} — {e}")
                fail += 1
            return None

        print("=== ThoughtPeer Smoke Test (v0.3.0-peer-focus) ===\n")

        # Health (no auth)
        await check("GET /health", "get", "/health")

        # Auth: register a fresh user each run
        suffix = secrets.token_hex(4)
        email = f"smoke+{suffix}@thoughtpeer.test"
        username = f"smoke_{suffix}"
        reg = await check("POST /auth/register", "post", "/auth/register", json={
            "email": email, "username": username,
            "password": "SmokeTestPassw0rd!", "display_name": "Smoke",
        })
        token = (reg or {}).get("access_token")
        if not token:
            print("  FAIL no access_token — aborting auth-dependent tests")
            sys.exit(1)
        headers["Authorization"] = f"Bearer {token}"

        await check("GET /auth/me", "get", "/auth/me")

        # Create entry
        entry = await check("POST /entries", "post", "/entries", json={
            "text": "I've been feeling stressed about work deadlines and my boss is not helpful",
            "mood": "bad",
            "tags": ["work", "stress"]
        })
        eid = entry["id"] if entry else 1

        await check("GET /entries", "get", "/entries")
        await check(f"GET /entries/{eid}", "get", f"/entries/{eid}")
        await check(f"PATCH /entries/{eid}", "patch", f"/entries/{eid}", json={"mood": "neutral"})

        # Analyze (server fallback if no LLM)
        await check(f"POST /entries/{eid}/analyze", "post", f"/entries/{eid}/analyze",
                    expected=[200, 201, 500, 503])

        # Submit insight manually
        await check(f"POST /insights/{eid}", "post", f"/insights/{eid}", json={
            "problems": ["deadline pressure", "unsupportive manager"],
            "emotions": ["stress", "frustration"],
            "category": "work",
            "severity": 7,
            "keywords": ["deadline", "boss", "stress", "work"]
        })
        await check(f"GET /insights/{eid}", "get", f"/insights/{eid}")
        await check("GET /insights/patterns/summary", "get", "/insights/patterns/summary")
        await check("GET /insights/timeline", "get", "/insights/timeline")
        await check("GET /insights/timeline/mood (legacy)", "get", "/insights/timeline/mood")

        # Share to peer pool
        shared = await check("POST /peers/share", "post", "/peers/share", json={
            "category": "work",
            "tags": ["stress", "deadlines"],
            "keywords": ["deadline", "boss", "pressure"],
            "severity": 7,
            "mood": "bad",
            "is_resolved": False
        })

        # Resolve with share_to_pool=true
        await check(f"POST /entries/{eid}/resolve (+share)", "post", f"/entries/{eid}/resolve",
                    json={
                        "resolution_text": "Time-boxing + honest chat with boss helped",
                        "share_to_pool": True,
                    })

        # Share a second resolved peer to increase pool
        await check("POST /peers/share (resolved)", "post", "/peers/share", json={
            "category": "work",
            "tags": ["stress", "deadlines"],
            "keywords": ["deadline", "boss", "timeboxing"],
            "severity": 3,
            "mood": "good",
            "is_resolved": True,
            "resolution_text": "Time-boxing + honest conversation with boss helped a lot"
        })

        # Peer search
        matches = await check("POST /peers/similar", "post", "/peers/similar", json={
            "text": "stressed about work deadlines",
            "keywords": ["deadline", "boss"],
        })
        if matches and isinstance(matches, list):
            assert all("similarity_score" in m for m in matches), "missing similarity_score"
            assert len(matches) <= 5, "cap violated"

        await check("POST /peers/solutions", "post", "/peers/solutions", json={
            "text": "work stress deadline"
        })

        # New endpoint — resolved-similar for an entry
        await check(f"GET /peers/resolved-similar/{eid}", "get", f"/peers/resolved-similar/{eid}")

        await check("GET /peers/stats", "get", "/peers/stats")

        # Unshare (delete peer)
        if shared and shared.get("id"):
            await check(f"DELETE /peers/share/{shared['id']}",
                        "delete", f"/peers/share/{shared['id']}", expected=[204])

        # Export
        dump = await check("GET /entries/export", "get", "/entries/export")
        assert dump and "signature" in dump and "entries" in dump, "export missing fields"

        # Import (round-trip)
        buf = io.BytesIO(json.dumps(dump).encode())
        r = await c.post("/entries/import", headers=headers,
                         files={"file": ("export.json", buf, "application/json")})
        if r.status_code == 200:
            print(f"  OK  POST /entries/import ({r.status_code}) → {r.json()}")
            ok += 1
        else:
            print(f"  FAIL POST /entries/import — {r.status_code}: {r.text[:200]}")
            fail += 1

        # Analytics
        await check("GET /analytics/overview", "get", "/analytics/overview")

        # Delete
        await check(f"DELETE /entries/{eid}", "delete", f"/entries/{eid}", expected=[204])

        print(f"\n{'='*40}")
        print(f"Passed: {ok} | Failed: {fail}")
        sys.exit(1 if fail else 0)


if __name__ == "__main__":
    asyncio.run(main())
