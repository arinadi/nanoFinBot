# 10 - Bulk queue: many photos confirmed one by one

## Behavior

> "System queues multiple photos and presents their drafts one by one."

## Depends on

07, 08.3

## Requirements

- When a message contains multiple photos, each photo becomes its own draft in a queue.
- Drafts are presented one at a time with Save/Edit/Cancel; after each decision the next
  draft is shown until the queue is empty.
- The queue order is stable (photo order in the message).

## Data and API

- Reuses `photo_to_draft` (07) and the capture handlers (08).
- All drafts are persisted (status=draft) so a restart resumes the queue.

## Technical notes

- Implement the queue as persisted drafts + a "next pending" pointer per user; the
  natural completion signal is "no more drafts for this user".
- On restart, re-present the oldest pending draft (risk chain 4).

## Acceptance checks

- [ ] Sending 3 photos produces 3 drafts shown one after another in order
      Command: `python -m pytest tests/test_bulk.py::test_queue_order -q`
- [ ] After the last draft is decided, the bot reports the queue is empty
      Command: `python -m pytest tests/test_bulk.py::test_queue_done -q`

## Out of scope for this nanotask

- The per-draft Save/Edit/Cancel handlers themselves — 08.
