# Future Work & Roadmap

A living document for planned improvements, enhancements, and technical debt. Items are grouped by area and can be tagged with priority (P1 = high, P2 = medium, P3 = lower) as we go.

---

## Backend Improvements

### Performance & Architecture
- **ChromaDB client reuse** — Use a single `PersistentClient` instead of creating one per request (saves ~100–500 ms per request).
- **Async / non-blocking embedding** — Run embedding in a thread pool so it doesn't block the event loop under concurrency.
- **Dedicated warmup endpoint** — Add `GET /api/warmup` to preload embedding model, ChromaDB, and Ollama before first real request.
- **Lighter embedding model** — Consider `paraphrase-MiniLM-L3-v2` or `all-MiniLM-L6-v2` for faster embedding (2–5 s improvement on first call).
- **Streaming responses** — Stream Ollama tokens via Server-Sent Events (SSE) instead of waiting for the full reply; much faster time-to-first-token.
- **Response caching** — Extend caching beyond `canon_qa` to character chat, chatroom, and case story for repeated or similar prompts.
- **Persistent session memory** — Replace in-memory session storage with Redis or a DB for multi-process / multi-instance setups.

### Reliability & Observability
- **Health check enhancements** — Report status of Ollama, ChromaDB, and embedding model (e.g. `/health` returns component readiness).
- **Graceful degradation** — When backend is unreachable, return structured fallback instead of failing silently.
- **Structured logging** — Consistent request IDs, timing, and error context for debugging.
- **Rate limiting** — Protect against abuse (per-IP or per-session limits) on chat and case-story endpoints.

### Content & Data
- **Incremental indexing** — Support adding new canon sources without full re-index; delta updates for ChromaDB.
- **Context window handling** — Truncate or summarize long histories to fit model limits; avoid silent truncation issues.

---

## User Experience Improvements

### Loading & Feedback
- **Loading states & progress hints** — Show messages like “Retrieving passages…”, “Holmes is reviewing the case…”, “Synthesizing reply…”.
- **Connection / readiness status** — Indicate whether the backend is ready (e.g. “System ready” vs “Warming up…”).
- **Optimistic UI** — Add user messages to the UI right away and show “Generating reply…” while the backend responds.
- **Skeleton loaders** — Placeholder blocks for character replies instead of a blank area.
- **Frontend warmup on navigation** — Call `/health` or `/api/warmup` when the user lands or selects a character so models are warmed before they send the first message.
- **Typing / thinking indicator** — Subtle animation or text while a reply is being generated.
- **Error recovery UX** — Clear messages and simple retry when Ollama or ChromaDB fail.

### Interaction & Polish
- **Keyboard shortcuts** — e.g. Ctrl+Enter to send, Escape to cancel.
- **Message actions** — Regenerate reply, copy to clipboard, or export passage.
- **Export conversation** — Download chat or case journal as PDF or plain text.
- **Mobile responsiveness** — Ensure layouts and touch targets work well on phones.
- **Accessibility** — ARIA labels, focus management, screen reader support for chat/journal.

---

## DevOps & Deployment

- **Staging environment** — Dedicated preview URL for testing before production.
- **Environment parity** — Document and align env vars across local, staging, prod.
- **Build optimizations** — Tree-shaking, code splitting, and bundle analysis for frontend.
- **Monitoring** — Vercel Analytics, backend metrics (latency, errors, cold starts).

---

## Content & Features

- **More canon sources** — Expand the case-book corpus or add supplementary materials.
- **Conversation history** — Persist sessions; list and resume past consultations.
- **Search within conversation** — Find text across current chat or journal.
- **Character customization** — Optional tone or strictness controls per character.

---

## Security & Privacy

- **Input sanitization** — Validate and limit prompt length; guard against injection.
- **CORS configuration** — Explicit allowlist for frontend origins in production.
- **Optional authentication** — API key or user auth for private or paid deployments.

---

## Reference

- See `docs/OPTIMIZATION_RECOMMENDATIONS.md` for detailed performance notes.
- See `DEPLOYMENT.md` for deployment and env var setup.
