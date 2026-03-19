"""Smoke test — hit every endpoint and verify basic responses."""

import asyncio
import sys

import httpx

BASE = "http://localhost:8000"


async def main():
    async with httpx.AsyncClient(base_url=BASE, timeout=10) as c:
        ok = 0
        fail = 0

        async def check(name: str, method: str, path: str, **kwargs):
            nonlocal ok, fail
            expected = kwargs.pop("expected", [200, 201])
            try:
                r = await getattr(c, method)(path, **kwargs)
                if r.status_code in expected:
                    print(f"  OK  {name} ({r.status_code})")
                    ok += 1
                    return r.json() if r.content else None
                else:
                    print(f"  FAIL {name} — {r.status_code}: {r.text[:200]}")
                    fail += 1
            except Exception as e:
                print(f"  FAIL {name} — {e}")
                fail += 1
            return None

        print("=== ThoughtPeer Smoke Test ===\n")

        # Health
        await check("GET /health", "get", "/health")

        # Create entry
        entry = await check("POST /entries", "post", "/entries", json={
            "text": "I've been feeling stressed about work deadlines and my boss is not helpful",
            "mood": "bad",
            "tags": ["work", "stress"]
        })
        eid = entry["id"] if entry else 1

        # List
        await check("GET /entries", "get", "/entries")

        # Get
        await check(f"GET /entries/{eid}", "get", f"/entries/{eid}")

        # Update
        await check(f"PATCH /entries/{eid}", "patch", f"/entries/{eid}", json={"mood": "neutral"})

        # Analyze (server fallback)
        insight = await check(f"POST /entries/{eid}/analyze", "post", f"/entries/{eid}/analyze")

        # Get insight
        await check(f"GET /insights/{eid}", "get", f"/insights/{eid}")

        # Submit insight (from local LLM)
        await check(f"POST /insights/{eid}", "post", f"/insights/{eid}", json={
            "problems": ["deadline pressure", "unsupportive manager"],
            "emotions": ["stress", "frustration"],
            "category": "work",
            "severity": 7,
            "keywords": ["deadline", "boss", "stress", "work"]
        })

        # Patterns
        await check("GET /insights/patterns", "get", "/insights/patterns/summary")

        # Timeline
        await check("GET /insights/timeline", "get", "/insights/timeline/mood")

        # Share to peer pool
        await check("POST /peers/share", "post", "/peers/share", json={
            "category": "work",
            "tags": ["stress", "deadlines"],
            "keywords": ["deadline", "boss", "pressure"],
            "severity": 7,
            "mood": "bad",
            "is_resolved": False
        })

        # Resolve entry
        await check(f"POST /entries/{eid}/resolve", "post", f"/entries/{eid}/resolve", json={
            "resolution_text": "Started time-boxing tasks and had an honest conversation with my boss"
        })

        # Share resolved
        await check("POST /peers/share (resolved)", "post", "/peers/share", json={
            "category": "work",
            "tags": ["stress", "deadlines"],
            "keywords": ["deadline", "boss", "timeboxing"],
            "severity": 3,
            "mood": "good",
            "is_resolved": True,
            "resolution_text": "Time-boxing + honest conversation with boss helped a lot"
        })

        # Search similar
        await check("POST /peers/similar", "post", "/peers/similar", json={
            "text": "stressed about work deadlines"
        })

        # Search solutions
        await check("POST /peers/solutions", "post", "/peers/solutions", json={
            "text": "work stress deadline"
        })

        # Pool stats
        await check("GET /peers/stats", "get", "/peers/stats")

        # Analytics
        await check("GET /analytics/overview", "get", "/analytics/overview")

        # Delete
        await check(f"DELETE /entries/{eid}", "delete", f"/entries/{eid}", expected=[204])

        print(f"\n{'='*40}")
        print(f"Passed: {ok} | Failed: {fail}")
        sys.exit(1 if fail else 0)


if __name__ == "__main__":
    asyncio.run(main())
