# boardbox

Personal board game library CLI I wrote because BoardGameGeek is great for
community stuff but I wanted something grep-friendly on disk.

One JSON file (`library.json` by default), no cloud sync, no accounts.
Import a CSV export from BGG when I feel like it, then grep my collection
from the terminal.

## What it does

- Track owned games (base, expansions, promos) with edition notes
- Log play sessions with date, player count, venue, notes
- Wishlist + order ledger for Kickstarter/backorder tracking
- Campaign plans (e.g. "Gloomhaven saga", "Wingspan family night")
- Tags, ratings, favorites, seasonal filters
- Search across title, designer, publisher, mechanics
- Weekly play stats and simple text reports
- Import adapters: BGG collection CSV, Tabletop Library export, Ludopoly dump
- Tiny stdlib HTTP server to browse the shelf on LAN

## What it doesn't do

- No live BGG API lookups — I type titles myself
- No box art hosting — local PNG paths only
- No multi-user anything — one person's shelf

## Quick start

```bash
pip install .
boardbox init ~/games/library.json
boardbox add --title "Wingspan" --year 2019 --designer "Elizabeth Hargrave"
boardbox session game001 --date 2024-03-12 --players 3
boardbox list --tag engine-builder
boardbox stats --month
```

## Author

Marwan Helmy — marwanabdelaal25@gmail.com

MIT license. Side project, Sep 2024–present.
