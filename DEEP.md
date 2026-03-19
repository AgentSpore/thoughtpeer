# ThoughtPeer — Architecture & Decisions

## Architecture

```
Client (phone/web)          Server (FastAPI)
┌──────────────┐           ┌──────────────────────┐
│ Local LLM    │──insights→│ POST /insights/{id}  │
│ Journal DB   │           │                      │
│ UI           │──share──→ │ POST /peers/share    │
│              │←─matches──│ POST /peers/similar  │
└──────────────┘           │ POST /peers/solutions│
                           │                      │
                           │ SQLite (peer_pool)   │
                           └──────────────────────┘
```

### Layered Architecture
- **api/** — FastAPI routers, request/response handling
- **services/** — Business logic, orchestration
- **repositories/** — Data access, SQL queries
- **schemas/** — Pydantic models for validation
- **core/** — Config, database, dependencies

### Key Decisions

1. **Local LLM first**: Analysis runs on-device. Server provides fallback keyword extraction for web demo only.
2. **Jaccard similarity**: Simple, explainable, no external dependencies. Upgrade path: vector embeddings when local models support them.
3. **Anonymous hashing**: SHA256(category + tags + timestamp)[:16]. No reversible user data in peer pool.
4. **aiosqlite**: Single-file DB, perfect for MVP. Upgrade path: PostgreSQL when scaling.
5. **No auth**: Privacy-by-design. Local user = "local". Peer pool is fully anonymous.

### Edge Cases
- Empty peer pool → return empty results, no error
- Duplicate shares → allowed (different hashes due to timestamp)
- Entry without insight → analyze endpoint creates one; peer search still works via text keywords
- Very long entries → truncated to 10000 chars at schema level
- Concurrent writes → WAL mode handles this for SQLite

### Data Flow
1. User writes entry → saved locally
2. Local LLM analyzes → insight saved via POST /insights/{id}
3. User shares → anonymized data sent to POST /peers/share
4. Other user searches → POST /peers/similar returns matches
5. If match is resolved → resolution_text shown as solution

## Changelog
- v0.1.0: Initial MVP — entries CRUD, server-side fallback analysis, peer matching, web UI
