# Import / export formats

## Native JSON

The on-disk format. One object with `schema_version`, arrays for each entity type.

## CSV (io_csv)

Columns for game export/import:

```
id,title,designer,studio,year,format,catalog_number,format,bin_id,shelf_id,tags,notes
```

Mechanic CSV uses `game_id,position,title,duration_sec`.

## JSONL (io_jsonl)

One JSON object per line — games or sessions. Good for streaming large exports.

## Bgg (io_bgg)

Bgg campaign/wantlist CSV export:

```
Bgg ID,Designer,Title,Publisher,Catalog Number,Edition,Rating,Released,CampaignFolder
```

We map folder names to tags and ignore marketplace-only columns.

## Tabletop (io_tabletop)

JSON array of release objects with `designer-mechanic`, `date`, `barcode`, `media` componentlists.

## Rt (io_ludopoly)

Library export CSV (`Designer`, `Game`, `Uri`) — used to cross-check what's *not* on game yet (want list hints).

## Export menu

`export_menu.py` picks format + optional filters (bin, year range, tagged).
