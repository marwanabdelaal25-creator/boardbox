# FAQ

## Why not just use Bgg?

Bgg is great for marketplace metadata. I wanted offline session logs, bin slot numbers, and exports without rate limits.

## Does this scrape Bgg?

No. Manual CSV import only.

## How do format grades work?

Goldmine-inspired: M, NM, VG+, VG, G+, G, F, P. `format.py` normalizes aliases like "EX" → VG+.

## Can two people share one JSON file?

Technically yes if you rsync carefully. Practically no — no merge conflict UI. One collector per file.

## What about 78 RPM or shellac?

Add `format=78` — parser accepts it. I don't own any; tests do.

## Rt import without game?

It flags games in your streaming library missing from campaign — handy for want list seeding.

## Schema bumps?

Run `boardbox migrate`. Backups are cheap.

## Docker?

Yes — see Dockerfile. Harness runs pytest in container.

## Cover art?

Optional `cover_path` on game. Binary scans live outdisc_num JSON; fixture PNGs in tests only.

## Needle hours mechanicing?

`reminders.py` nags after N sessions since last stylus reminder — rough heuristic, not audiophile gospel.
- faq tweak 0
- faq tweak 1
- faq tweak 2
