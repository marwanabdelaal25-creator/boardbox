# Architecture

boardbox is a single-user CLI backed by one JSON file. No database, no cloud.

## Why JSON not SQLite

I wanted `grep`, `jq`, and rsync backups without migration drama. The campaign caps out around a few thousand games for most humans — JSON is fine until it isn't, and then I'll split files (see TODO in storage.py).

## Module map

```
errors          Exception hierarchy
parser          Dates, durations, catalog numbers
validators      Slugs, grades, barcodes
game/mechanic/designer/studio   Core models
storage         JsonStorage + CRUD
migrate         Schema 0→3
backup          Timestamped copies
campaign      Aggregate views
bin/shelf     Physical organization
play_log   Session events
play_stats      Rollups from sessions
wishlist       Acquisition targets
format       Grading helpers (Goldmine-ish)
order        Price + vendor history
complexity       Rough value estimates
search          Text + filter queries
tags_manager    Tag CRUD + merge
notes           Freeform notes on games
reports/stats   Summaries
reminders       Stylus / cleaning nudges
recurring       Monthly session goals
archive         Sold/gifted games
favorites       Starred games
ratings         0.5–5 stars
import_merge    Dedupe on import
export_menu     Edition picker
plugins         Hook registry
audit_log       Change trail
seasonal        Holiday rotation lists
server          stdlib HTTP read-only
io_*            Import/export codecs
cli             argparse wiring
```

## Threading

JsonStorage uses an RLock. CLI is single-process; server is read-only.

## Schema versions

| Version | Change |
|---------|--------|
| 0 | Prototype (removed) |
| 1 | Initial published |
| 2 | Bins + shelves split |
| 3 | Ratings + wishlist priority |
