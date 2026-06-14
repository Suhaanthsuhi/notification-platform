# Architecture

notifty is a fully event-driven, distributed notification system built on Redis
Streams and horizontally scalable workers. Domain events from upstream services
become timely, personalized, multi-language push notifications.

## Pipeline

```
Producers
  -> notif_events_raw        (Redis Stream)
     -> Context Enricher      (validate + idempotency + load profile/preferences)
        -> notif_events_enriched
           -> Decision Engine (opt-in + throttle + template render)
              -> notif_delivery_tasks
                 -> Delivery Worker (resolve tokens + FCM send)
                    -> FCM / APNs

  notif_events_dlq           <- failures from every stage
```

Each stage is an independent, stateless process. Stages communicate only through
Redis Streams, so any stage can be scaled or redeployed independently.

## Guarantees

- **At-least-once delivery** — consumer groups (`XREADGROUP`) + explicit `XACK`.
- **Idempotent processing** — `SETNX` keys per stage prevent duplicate sends.
- **Crash recovery** — `XPENDING` + `XCLAIM` reclaim messages from dead workers.
- **Failure isolation** — every stage routes bad messages to a dead-letter queue.
- **Bounded memory** — streams are trimmed by age (MINID) and size (MAXLEN).

## Stage responsibilities

### Producers (Stage 0)
Upstream services and the engagement scheduler emit **facts only** into
`notif_events_raw`. They never select templates, apply preferences, or deliver.

### Context Enricher (Stage 1)
Validates the event against its Pydantic contract, enforces idempotency, runs the
registered context loaders (profile, preferences, …) concurrently, and publishes
an enriched event. Validation/loader failures go to the DLQ; crashes are recovered
via `XPENDING`/`XCLAIM`.

### Decision Engine (Stage 2)
Resolves the recipient (user / topic / broadcast), checks opt-in, applies the
per-user rate limit, renders a localized template into a delivery task, and
publishes it.

### Delivery Worker (Stage 3)
Pure transport. Resolves device tokens (Redis-cached, DB fallback), sends via FCM
(multicast / topic / broadcast), and deactivates tokens FCM reports as invalid.

## Engagement (campaign engine)

A scheduler runs on a fixed cadence, resolves each campaign's user **segment**,
and emits synthetic events into the same raw stream — so campaign notifications
get the exact same reliability guarantees as transactional ones. Two extra guards
(per-campaign cooldown + a daily per-user cap) prevent notification flooding.

## Extension points

| To add… | Do this | No change to |
|---|---|---|
| A notification type | `EventType` + `@register_event_model` + `@register_template` + translations | workers |
| Enrichment data | implement `BaseContextLoader` + `@register_loader` | enricher worker |
| A campaign | implement `BaseCampaign` + `@register_campaign` | scheduler |
| An audience | implement `BaseSegment` + `@register_segment` | campaigns |

The startup contract validator fails fast if any event is missing a schema,
template, or translation — so the registries can't drift out of sync.
