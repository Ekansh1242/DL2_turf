# CampusSphere AI

**College problem:** Students at RCOEM booking sports turfs/courts hit
double-bookings, wasted time, and no easy way to find an alternative
when their preferred slot is taken.

**Solution:** A LangGraph agent that takes a natural-language booking
request, checks real availability, and -- if there's a conflict --
reasons over the actual open slots to pick and confirm the best
alternative, with a deterministic backend guaranteeing no double-booking
ever happens.

## Why this is genuinely agentic (not just LangGraph sitting unused)

The graph is **actually invoked** by `POST /api/v1/bookings/ai-book` --
not reference code. It has 3 real nodes with a real shared state object
(`AIBookingState`) and real conditional routing:

```
Student's message
        v
+-------------------+
| booking_node (LLM) |   <- parses NL into {sport, date, hour}
+-------------------+       structured output, never invents fields
        v
+---------------------------+
| scheduling_conflict_node   |  <- deterministic: real DB query for
| (deterministic + LLM)      |     the resource + today's real bookings
+---------------------------+
        v
   conflict? --no--> commit_node (deterministic FCFS-safe booking)
        |
       yes
        v
   any open slots? --no--> escalate (no LLM call, no fake success)
        |
       yes
        v
   LLM picks the closest real open hour + writes one sentence why
        v
   commit_node (deterministic FCFS-safe booking, same as no-conflict path)
```

**LLM-based reasoning agents:** `booking_node` (NL understanding),
the alternative-selection step inside `scheduling_conflict_node`
(picks from real data, never hallucinated).

**Deterministic tools:** resource lookup, today's booking query, the
FCFS commit itself (`BookingService.book_slot` -- the exact same
function the manual booking flow uses, so the AI path can never bypass
the concurrency/double-booking guarantees).

**LangGraph's role:** orchestrates the 3 nodes, carries `AIBookingState`
between them, and does the conditional routing (conflict vs. no
conflict; alternative found vs. escalate).

This deliberately consolidates what was originally sketched as 5
separate nodes (Booking / Scheduling / Conflict Resolution / Commit /
Notification) into 3 -- Scheduling and Conflict Resolution share one
node because they operate on the same data back-to-back, and
Notification was dropped because it's a plain database write with no
reasoning in it, not because it makes the system "less agentic." Node
count isn't the test; distinct responsibilities + shared state +
conditional routing + real LLM reasoning is, and this graph has all
four.

## Manual booking is untouched

The original step-by-step manual flow (`/api/v1/auth/login` ->
`/api/v1/sports` -> `/api/v1/slots` -> `/api/v1/bookings/confirm` ->
`/api/v1/equipment/*`) still works exactly as before. AI Booking is an
additional path (`/api/v1/bookings/ai-book`), not a replacement.

## Real college rules enforced (same as the manual flow)

- `@rknec.edu`-only login
- One dedicated turf per sport, 8am-7pm, 1-hour slots
- Booking window opens 30 min before a slot, closes at slot end; late
  bookings get a prorated (shorter) confirmed time
- Strict first-come-first-served -- the DB-level Postgres exclusion
  constraint (`no_overlapping_bookings`, in
  `backend/app/db/migrations/001_init.sql`) is the final guarantee
  against double-booking, not the LLM and not application code alone
- Equipment checkout/return with a flat Rs.250 fine for lost/badly
  damaged items
- No-show tracking with auto-block after repeated no-shows

## Project layout

```
backend/
  app/
    domain/
      models/models.py          # Sports, Users, Bookings, Equipment, NoShow
      services/
        slot_window.py           # 30-min window + prorated late booking
        booking_service.py       # strict FCFS booking (used by BOTH flows)
        equipment_service.py     # checkout/return + fine logic
        noshow_service.py
    agents/                      # the real, live LangGraph agent
      state.py                   # AIBookingState (shared state)
      graph.py                   # 3-node graph, conditional routing
      nodes/
        booking_node.py           # LLM: NL -> structured intent
        scheduling_conflict_node.py  # deterministic lookup + LLM alt-pick
        commit_node.py            # deterministic, FCFS-safe commit
    api/v1/
      auth.py, sports.py, slots.py, bookings.py, equipment.py  # manual flow
      ai_booking.py              # POST /bookings/ai-book -- invokes the graph
    db/
      seed.py, migrations/001_init.sql
  tests/
    test_booking_flow.py         # 12 tests: FCFS/window/equipment/no-show
                                  # rules PLUS 2 tests that run the real
                                  # LangGraph graph end-to-end with the
                                  # LLM calls mocked (no API key needed
                                  # to run tests)

frontend/
  src/
    api/client.ts
    components/
      LoginStep.tsx
      AIBookingStep.tsx   # shows the real per-node trace as it completes
    App.tsx
```

## Running locally

```bash
docker compose up postgres redis -d

cd backend
python -m venv venv
venv\Scripts\activate        # Windows; source venv/bin/activate elsewhere
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
Once (needs `psql`):
```bash
psql postgresql://postgres:postgres@localhost:5432/campussphere -f app/db/migrations/001_init.sql
python -m app.db.seed
```

```bash
cd frontend
npm install
npm run dev
```

Set `OPENAI_API_KEY` in `.env` (copy from `.env.example`) -- required
for AI Booking. Without it, the endpoint fails loudly with a clear
config error rather than faking a response.

## Tests (no API key needed)

```bash
cd backend
pytest tests/test_booking_flow.py -v
```
12 tests, all passing: FCFS booking, 30-min window, prorated late
booking, equipment fines, no-show blocking, and 2 end-to-end LangGraph
graph tests (LLM mocked) covering both the no-conflict and
conflict-with-real-alternative-selection paths.

## Example for the demo video

1. Pre-book the 8am football slot manually (or via `/bookings/confirm`).
2. In AI Booking, type: *"Book a football turf tomorrow at 8am"*.
3. Watch the trace: Booking Agent parses it -> Scheduling+Conflict Agent
   finds the 8am slot taken, picks the closest real open hour (e.g. 9am)
   and explains why -> Commit confirms the real booking.
4. Show the booking ID and that a second identical request for the same
   slot gets rejected (FCFS), proving the DB constraint -- not the LLM
   -- is what prevents double-booking.

## Limitations

- Single-day slot lookup for AI Booking (no multi-day "next available"
  search yet).
- No notification/event system wired into the AI path (the manual flow
  doesn't have one either, in this slice).
- Admin monitoring/reallocation of unclaimed slots is designed but not
  built.

## AI architecture (v3)

**Booking agent** (`agents/graph.py`, LangGraph): `booking_node` (LLM extracts intent; unknown sport/time/date is never guessed -- the agent asks) -> `scheduling_conflict_node` (DB tools; the LLM only weighs trade-offs when the preferred slot is unavailable) -> `commit_node` (deterministic `BookingService`, same FCFS + DB-constraint path as manual booking).

- Hard rules are deterministic: slot free, window rules, minimum usable time. The LLM chooses among *validated candidates* (closeness, bookable-now vs opens-later, usable minutes, turf load, back-to-back) and its pick is checked against the list; an invalid pick or LLM failure falls back to a rule-based choice, flagged in the trace.
- An alternative slot is never auto-booked. It is returned as a proposal the student confirms; confirmation goes through `POST /bookings/confirm`, which re-checks availability.
- Every response carries a measured execution trace (node, status, duration_ms, summary).

**Admin analytics agent** (`agents/analytics_agent.py`, `POST /admin/analytics/ask`, admin-only): LLM routes the question to one tool from a fixed allowlist -> existing read-only analytics query runs -> LLM summarises only the returned data. No generated SQL; empty data short-circuits to a fixed message.

**Known limitation:** slots only open 30 minutes before they start (college rule), so live alternatives are few; the agent therefore also recommends later slots that are not yet bookable and says when they open.
Tests: `pytest tests/ -v` (24 tests, LLM mocked, no API key needed).
