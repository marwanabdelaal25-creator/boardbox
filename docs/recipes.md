# Recipes

Copy-paste workflows that actually work.

## 1. Fresh campaign

```bash
boardbox init ~/music/game.json
boardbox add --title "Blue Train" --designer "John Coltrane" --year 1957 --format LP
```

## 2. Log a session

```bash
boardbox session --game-id alb_abc123 --note "Quiet evening"
boardbox sessions --game-id alb_abc123
```

## 3. Import Bgg export

```bash
boardbox import bgg ~/Downloads/bgg_campaign.csv --merge
```

## 4. Organize a bin

```bash
boardbox bin add --name "Jazz A-D"
boardbox move --game-id alb_abc123 --bin "Jazz A-D" --slot 12
```

## 5. Want list

```bash
boardbox want add --title "In Rainbows" --designer "Radiohead" --priority high
boardbox want list --priority high
```

## 6. Monthly session report

```bash
boardbox stats --month 2026-05
boardbox report sessions --format csv > may_sessions.csv
```

## 7. Backup before migration

```bash
boardbox backup ~/music/backups/
boardbox migrate --check
```

## 8. Search by format

```bash
boardbox search --format "VG+" --format LP
```

## 9. Export shelf studios

```bash
boardbox export studios --bin "Jazz A-D" --output studios.md
```

## 10. LAN browse (read-only)

```bash
boardbox serve --port 8765 ~/music/game.json
```

Open `http://localhost:8765/games` on the kitchen tablet.
