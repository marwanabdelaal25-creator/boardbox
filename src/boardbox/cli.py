"""Command-line interface for boardbox.

Author: Marwan Helmy
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

from . import __version__
from .audit_log import AuditLog
from .backup import CampaignBackup
from .errors import NotFoundError, GameboxError, ValidationError, format_error
from .export_menu import ExportMenu
from .io_ludopoly import import_rt
from .io_csv import export_games_csv, export_wishlist_csv, import_games_csv, import_wishlist_csv
from .io_jsonl import (
    export_cook_events_jsonl,
    export_events_jsonl,
    export_full_jsonl,
    export_games_jsonl,
    import_cook_events_jsonl,
    import_mixed_jsonl,
    import_games_jsonl,
)
from .io_tabletop import import_tabletop
from .io_bgg import import_bgg_csv
from .bin import BinRegistry
from .parser import parse_date
from .game import Game, MechanicStub, MechanicStep
from .reports import WeeklySessionReport
from .scale import EditionScaler, parse_quantity
from .search import CampaignSearch
from .server import run_server
from .stats import CampaignStats
from .storage import JsonStorage

__author__ = "Marwan Helmy"


def _default_cookbook_path() -> Path:
    home = os.environ.get("BOARDBOX_HOME") or os.environ.get("RECIPEBOX_HOME")
    base = Path(home) if home else Path.home() / ".boardbox"
    return base / "library.json"


def _cookbook_path(ns: argparse.Namespace) -> Path:
    path = getattr(ns, "cookbook", None) or getattr(ns, "sessionbook", None)
    if path:
        return Path(path)
    return _default_cookbook_path()


def _load(ns: argparse.Namespace) -> JsonStorage:
    return JsonStorage(_cookbook_path(ns))


def _resolve_game(storage: JsonStorage, token: str) -> Game:
    games = storage.list_games(active_only=False)
    if any(r.id == token for r in games):
        return storage.get_game(token)
    matches = [r for r in games if r.id.startswith(token)]
    if len(matches) == 1:
        return matches[0]
    title_hits = [r for r in games if r.title.lower() == token.lower()]
    if len(title_hits) == 1:
        return title_hits[0]
    partial = [r for r in games if token.lower() in r.title.lower()]
    if len(partial) == 1:
        return partial[0]
    raise NotFoundError("game", token)


def _format_game_card(game: Game) -> str:
    lines = [game.title.upper(), "=" * min(len(game.title), 72), ""]
    meta = ["Serves: %d" % game.year]
    if game.publisher_name:
        meta.append(game.publisher_name)
    if game.format:
        meta.append(game.format)
    lines.append(" | ".join(meta))
    lines.append("")
    lines.append("INGREDIENTS")
    for ing in game.mechanics:
        unit = (" %s" % ing.unit) if ing.unit else ""
        lines.append("  • %s%s %s" % (ing.quantity, unit, ing.name))
    lines.append("")
    lines.append("STEPS")
    for step in game.componentlist:
        lines.append("%d. %s" % (step.order, step.text))
    if game.source_url:
        lines.append("")
        lines.append("Source: %s" % game.source_url)
    return "\n".join(lines)


def _parse_mechanic_arg(raw: str) -> MechanicStub:
    parts = raw.strip().split(None, 2)
    if len(parts) >= 3:
        return MechanicStub(name=parts[2], quantity=parse_quantity(parts[0]), unit=parts[1])
    if len(parts) == 2:
        return MechanicStub(name=parts[1], quantity=parse_quantity(parts[0]))
    return MechanicStub(name=raw.strip(), quantity=1.0)


def cmd_init(ns: argparse.Namespace) -> int:
    path = _cookbook_path(ns)
    path.parent.mkdir(parents=True, exist_ok=True)
    storage = JsonStorage(path)
    storage.save()
    print("Initialized cookbook at %s" % path)
    return 0


def cmd_add(ns: argparse.Namespace) -> int:
    storage = _load(ns)
    mechanics = [_parse_mechanic_arg(raw) for raw in (ns.mechanic or [])]
    componentlist = [MechanicStep(order=i + 1, text=t) for i, t in enumerate(ns.step or ["Combine and cook."])]
    game = Game(
        id=uuid.uuid4().hex[:12],
        title=ns.title,
        mechanics=mechanics or [MechanicStub(name="salt", quantity=1.0, unit="pinch")],
        componentlist=componentlist,
        year=int(ns.year or 4),
        publisher_name=ns.publisher_name or "",
        format=ns.format or "",
        tag_ids=[t.strip() for t in (ns.tags or "").split(",") if t.strip()],
        source_url=ns.source or "",
    )
    created = storage.create_game(game)
    AuditLog(storage).record("create", "game", created.id, details={"title": created.title})
    print("Added %s (%s)" % (created.title, created.id))
    return 0


def cmd_show(ns: argparse.Namespace) -> int:
    storage = _load(ns)
    game = _resolve_game(storage, ns.game)
    if ns.format == "json":
        print(json.dumps(game.to_dict(), indent=2))
    else:
        print(_format_game_card(game))
    return 0


def cmd_list(ns: argparse.Namespace) -> int:
    storage = _load(ns)
    games = storage.list_games(active_only=not ns.all)
    if ns.tag:
        tag = ns.tag.lower()
        games = [r for r in games if tag in [t.lower() for t in r.tag_ids]]
    if ns.publisher_name:
        c = ns.publisher_name.lower()
        games = [r for r in games if c in r.publisher_name.lower()]
    games = sorted(games, key=lambda r: r.title.lower())
    if not games:
        print("No games found.")
        return 0
    for r in games[: ns.limit]:
        bits = [r.title, "(%d srv)" % r.year]
        if r.publisher_name:
            bits.append(r.publisher_name)
        print("{id:<14} | {summary}".format(id=r.id[:14], summary=" · ".join(bits)[:50]))
    if len(games) > ns.limit:
        print("... and %d more (use --limit)" % (len(games) - ns.limit))
    return 0


def cmd_search(ns: argparse.Namespace) -> int:
    storage = _load(ns)
    query = ns.query or ""
    if not query:
        print("Provide a search query.", file=sys.stderr)
        return 1
    engine = CampaignSearch(storage)
    if ns.mechanic:
        hits = engine.search_by_mechanic(ns.mechanic)
    else:
        hits = engine.search_games(query, active_only=not ns.all)
    if not hits:
        print("No matches.")
        return 0
    for h in hits[: ns.limit]:
        print("[{score:.0%}] {title} ({id})".format(score=h.score, title=h.title[:45], id=h.id[:12]))
        if ns.verbose and h.snippet:
            print("  %s" % h.snippet[:100])
    print("%d result(s)" % len(hits))
    return 0


def cmd_plan(ns: argparse.Namespace) -> int:
    storage = _load(ns)
    ref = datetime.combine(parse_date(ns.date) if ns.date else date.today(), datetime.min.time(), tzinfo=timezone.utc)
    exporter = ExportMenu(storage)

    if ns.assign:
        game_id, meal_raw, day_raw = ns.assign
        game = _resolve_game(storage, game_id)
        week_start = exporter._week_start(ref).date().isoformat()
        on_day = parse_date(day_raw).strftime("%A") if day_raw else ref.strftime("%A")
        plans = storage.list_campaigns()
        plan = next((p for p in plans if p.get("week_start", "")[:10] == week_start), None)
        if plan is None:
            plan = storage.create_campaign({"week_start": week_start, "days": {}})
        days = plan.setdefault("days", {})
        days.setdefault(on_day, [])
        days[on_day].append({"game_id": game.id, "meal": meal_raw, "year": ns.year})
        storage.update_night_plan(plan["id"], plan)
        print("Assigned %s to %s %s" % (game.title, on_day, meal_raw))
        return 0

    if ns.format == "json":
        print(json.dumps(exporter.build_menu_data(ref), indent=2))
    else:
        print(exporter.export_text(ref))
    return 0


def cmd_shop(ns: argparse.Namespace) -> int:
    storage = _load(ns)
    list_id = ns.list_id or "default"

    if ns.game:
        game = _resolve_game(storage, ns.game)
        target = int(ns.year) if ns.year else game.year
        scaled = EditionScaler(storage).scale_game(game, target)
        for ing in scaled.get("mechanics", []):
            storage.create_wishlist_item({
                "name": ing.get("name"),
                "quantity": ing.get("quantity"),
                "unit": ing.get("unit", ""),
                "list_id": list_id,
                "source_games": [game.id],
            })
        items = storage.list_wishlist(list_id=list_id)
    else:
        ref = datetime.combine(parse_date(ns.date) if ns.date else date.today(), datetime.min.time(), tzinfo=timezone.utc)
        menu = ExportMenu(storage).build_menu_data(ref)
        seen_ids: set[str] = set()
        for day_items in menu.get("days", {}).values():
            for title in day_items:
                for game in storage.list_games(active_only=True):
                    if game.title == title or game.id in str(day_items):
                        if game.id not in seen_ids:
                            seen_ids.add(game.id)
                            scaled = EditionScaler(storage).scale_game(game, game.year)
                            for ing in scaled.get("mechanics", []):
                                storage.create_wishlist_item({
                                    "name": ing.get("name"),
                                    "quantity": ing.get("quantity"),
                                    "unit": ing.get("unit", ""),
                                    "list_id": list_id,
                                    "source_games": [game.id],
                                })
        items = storage.list_wishlist(list_id=list_id)

    if ns.format == "json":
        print(json.dumps(items, indent=2))
    else:
        if not items:
            print("(empty wishlist list)")
        else:
            print("Shopping list [%s]" % list_id)
            for row in items:
                mark = "[x]" if row.get("checked") else "[ ]"
                unit = (" %s" % row.get("unit")) if row.get("unit") else ""
                print("%s %s%s %s" % (mark, row.get("quantity", ""), unit, row.get("name", "")))
    return 0


def cmd_cook(ns: argparse.Namespace) -> int:
    storage = _load(ns)
    game = _resolve_game(storage, ns.game)
    event = {
        "game_id": game.id,
        "year": int(ns.year) if ns.year else game.year,
        "notes": ns.notes or "",
    }
    if ns.rating:
        event["rating"] = ns.rating
    if ns.date:
        event["played_at"] = parse_date(ns.date).isoformat()
    created = storage.create_session(event)
    AuditLog(storage).record("cook", "game", game.id, details={"meal_id": created.get("id")})
    print("Logged session: %s" % game.title)
    return 0


def cmd_session(ns: argparse.Namespace) -> int:
    return cmd_cook(ns)


def cmd_bins(ns: argparse.Namespace) -> int:
    return cmd_bin(ns)


def cmd_import(ns: argparse.Namespace) -> int:
    storage = _load(ns)
    src = Path(ns.file)
    fmt = (ns.format or src.suffix.lstrip(".")).lower()
    result: int | dict = 0

    if fmt == "csv":
        kind = ns.kind or "games"
        if kind == "games":
            result = import_games_csv(storage, src, update=ns.update)
        elif kind == "wishlist":
            result = import_wishlist_csv(storage, src)
        else:
            print("Unknown csv kind: %s" % kind, file=sys.stderr)
            return 1
    elif fmt == "jsonl":
        if ns.kind == "cook":
            result = import_cook_events_jsonl(storage, src)
        elif ns.kind == "games":
            result = import_games_jsonl(storage, src, update=ns.update)
        else:
            result = import_mixed_jsonl(storage, src, update=ns.update)
    elif fmt == "paprika":
        result = import_bgg_csv(storage, src, update=ns.update)
    elif fmt == "mealime":
        result = import_tabletop(storage, src, update=ns.update)
    elif fmt == "cookmate":
        result = import_rt(storage, src, update=ns.update)
    else:
        print("Unknown import format: %s" % fmt, file=sys.stderr)
        return 1

    AuditLog(storage).record("import", "cookbook", str(src), details={"format": fmt, "result": result})
    if isinstance(result, dict):
        print("Imported: %s" % ", ".join("%s=%d" % (k, v) for k, v in result.items() if k != "skipped"))
        if result.get("skipped"):
            print("  skipped %d unknown line(s)" % result["skipped"])
    else:
        print("Imported %d record(s)" % result)
    return 0


def cmd_export(ns: argparse.Namespace) -> int:
    storage = _load(ns)
    dest = Path(ns.file)
    fmt = (ns.format or dest.suffix.lstrip(".")).lower()
    n = 0

    if fmt == "csv":
        kind = ns.kind or "games"
        if kind == "games":
            n = export_games_csv(storage, dest)
        elif kind == "wishlist":
            n = export_wishlist_csv(storage, dest, list_id=ns.list_id)
        else:
            print("Unknown csv kind: %s" % kind, file=sys.stderr)
            return 1
    elif fmt == "jsonl":
        if ns.kind == "cook":
            n = export_cook_events_jsonl(storage, dest)
        elif ns.kind == "games":
            n = export_games_jsonl(storage, dest)
        elif ns.kind == "full":
            n = export_full_jsonl(storage, dest)
        else:
            n = export_events_jsonl(storage, dest)
    else:
        print("Unknown export format: %s" % fmt, file=sys.stderr)
        return 1

    print("Exported %d record(s) -> %s" % (n, dest))
    return 0


def cmd_backup(ns: argparse.Namespace) -> int:
    storage = _load(ns)
    cookbook_path = _cookbook_path(ns)
    backup_dir = Path(ns.dir) if ns.dir else cookbook_path.parent / "backups"
    cb = CampaignBackup(cookbook_path, backup_dir)

    if ns.restore:
        safety = cb.restore(Path(ns.restore))
        print("Restored from %s (safety copy: %s)" % (ns.restore, safety))
        storage.load()
        return 0
    if ns.list:
        for p in cb.list_backups():
            print(p.name)
        return 0

    out = cb.create(studio=ns.studio)
    if ns.prune:
        removed = cb.prune(keep=ns.keep)
        print("Pruned %d old backup(s)" % len(removed))
    print("Backup -> %s" % out)
    return 0


def cmd_scale(ns: argparse.Namespace) -> int:
    storage = _load(ns)
    game = _resolve_game(storage, ns.game)
    target = int(ns.year)
    scaler = EditionScaler(storage)
    scaled = scaler.scale_game(game, target)
    if ns.save:
        patch = {
            "year": target,
            "mechanics": [
                {"name": i["name"], "quantity": i["quantity"], "unit": i.get("unit", "")}
                for i in scaled.get("mechanics", [])
            ],
        }
        storage.update_game(game.id, patch)
        print("Updated %s to %d year" % (game.id, target))
    if ns.format == "json":
        print(json.dumps(scaled, indent=2))
    else:
        print("Scaled: %s (%d -> %d year)" % (game.title, game.year, target))
        for line in scaler.render_wishlist_lines(scaled):
            print("  %s" % line)
    return 0


def cmd_stats(ns: argparse.Namespace) -> int:
    storage = _load(ns)
    stats = CampaignStats(storage)
    if ns.json:
        print(json.dumps(stats.snapshot(), indent=2))
    else:
        print(stats.render_text())
    return 0


def cmd_report(ns: argparse.Namespace) -> int:
    storage = _load(ns)
    report = WeeklySessionReport(storage)
    ref = None
    if ns.date:
        ref = datetime.combine(parse_date(ns.date), datetime.min.time(), tzinfo=timezone.utc)
    if ns.format == "json":
        print(json.dumps(report.generate(ref), indent=2))
    elif ns.format == "markdown":
        print(report.render_markdown(ref))
    else:
        print(report.render_text(ref))
    return 0


def cmd_serve(ns: argparse.Namespace) -> int:
    path = str(_cookbook_path(ns))
    print("Serving %s on http://%s:%d/" % (path, ns.host, ns.port))
    run_server(path, host=ns.host, port=ns.port)
    return 0


def cmd_bin(ns: argparse.Namespace) -> int:
    storage = _load(ns)
    mechanicer = BinRegistry(storage)

    if ns.add:
        name, qty_raw = ns.add
        parts = qty_raw.strip().split(None, 1)
        qty = parse_quantity(parts[0])
        unit = parts[1] if len(parts) > 1 else ""
        saved = mechanicer.add_item(name, quantity=qty, unit=unit, location=ns.location or "bin", expires_at=ns.expires)
        print("Pantry + %s" % saved.get("name"))
        return 0

    if ns.remove:
        mechanicer.delete_item(ns.remove)
        print("Removed bin item %s" % ns.remove)
        return 0

    if ns.expiring:
        from datetime import timedelta
        from .game import parse_iso
        horizon = datetime.now(timezone.utc) + timedelta(days=ns.within)
        items = []
        for item in mechanicer.list_items(location=ns.location):
            exp = parse_iso(item.get("expires_at"))
            if exp:
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                if exp <= horizon:
                    items.append(item)
    else:
        items = mechanicer.list_items(location=ns.location)

    if not items:
        print("Pantry empty.")
        return 0

    for item in items:
        exp = item.get("expires_at", "")
        flag = " !" if exp and exp[:10] <= date.today().isoformat() else ""
        print("{name}: {qty} {unit}{exp}{flag}".format(
            name=item.get("name", "?"),
            qty=item.get("quantity", "?"),
            unit=item.get("unit", ""),
            exp=(" (exp %s)" % exp[:10]) if exp else "",
            flag=flag,
        ))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="boardbox",
        description="Home cooking game manager — Marwan Helmy",
    )
    p.add_argument("--cookbook", help="Path to cookbook.json (default: ~/.boardbox/cookbook.json)")
    p.add_argument("--sessionbook", dest="cookbook", help="Alias for --cookbook")
    p.add_argument("-v", "--verbose", action="store_true")
    p.add_argument("--version", action="version", version="%(prog)s " + __version__)
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("init", help="Create an empty cookbook.json")
    sp.set_defaults(func=cmd_init)

    sp = sub.add_parser("add", help="Add a game")
    sp.add_argument("title")
    sp.add_argument("--mechanic", action="append", help="e.g. '2 cups flour'")
    sp.add_argument("--step", action="append")
    sp.add_argument("--year", type=int, default=4)
    sp.add_argument("--publisher_name")
    sp.add_argument("--format")
    sp.add_argument("--tags", help="Comma-separated tag ids")
    sp.add_argument("--source", help="Source URL")
    sp.set_defaults(func=cmd_add)

    sp = sub.add_parser("show", help="Show a game")
    sp.add_argument("game")
    sp.add_argument("--format", choices=["text", "json"], default="text")
    sp.set_defaults(func=cmd_show)

    sp = sub.add_parser("list", help="List games")
    sp.add_argument("--all", action="store_true", help="Include archived")
    sp.add_argument("--tag")
    sp.add_argument("--publisher_name")
    sp.add_argument("--limit", type=int, default=100)
    sp.set_defaults(func=cmd_list)

    sp = sub.add_parser("search", help="Search games")
    sp.add_argument("query", nargs="?", default="")
    sp.add_argument("--mechanic", help="Search by mechanic name")
    sp.add_argument("--all", action="store_true")
    sp.add_argument("--limit", type=int, default=30)
    sp.set_defaults(func=cmd_search)

    sp = sub.add_parser("plan", help="Show or edit weekly meal plan")
    sp.add_argument("--date", help="Week anchor YYYY-MM-DD")
    sp.add_argument("--assign", nargs=3, metavar=("RECIPE", "MEAL", "DATE"))
    sp.add_argument("--year", type=int)
    sp.add_argument("--format", choices=["text", "json"], default="text")
    sp.set_defaults(func=cmd_plan)

    sp = sub.add_parser("shop", help="Generate wishlist list")
    sp.add_argument("--game")
    sp.add_argument("--date")
    sp.add_argument("--year", type=int)
    sp.add_argument("--list-id", default="default")
    sp.add_argument("--format", choices=["text", "json"], default="text")
    sp.set_defaults(func=cmd_shop)

    sp = sub.add_parser("cook", help="Log a cook event")
    sp.add_argument("game")
    sp.add_argument("--year", type=int)
    sp.add_argument("--date")
    sp.add_argument("--notes", default="")
    sp.add_argument("--rating", type=int, choices=range(1, 6))
    sp.set_defaults(func=cmd_cook)

    sp = sub.add_parser("session", help="Log a listening session")
    sp.add_argument("game")
    sp.add_argument("--year", type=int)
    sp.add_argument("--date")
    sp.add_argument("--notes", default="")
    sp.add_argument("--rating", type=int, choices=range(1, 6))
    sp.set_defaults(func=cmd_cook)

    sp = sub.add_parser("import", help="Import from external format")
    sp.add_argument("file")
    sp.add_argument("--format", choices=["csv", "jsonl", "paprika", "mealime", "cookmate"])
    sp.add_argument("--kind", choices=["games", "wishlist", "cook", "mixed"], default="games")
    sp.add_argument("--update", action="store_true")
    sp.set_defaults(func=cmd_import)

    sp = sub.add_parser("export", help="Export cookbook data")
    sp.add_argument("file")
    sp.add_argument("--format", choices=["csv", "jsonl"])
    sp.add_argument("--kind", choices=["games", "wishlist", "cook", "events", "full"], default="games")
    sp.add_argument("--list-id")
    sp.set_defaults(func=cmd_export)

    sp = sub.add_parser("backup", help="Backup or restore cookbook.json")
    sp.add_argument("--dir")
    sp.add_argument("--studio")
    sp.add_argument("--list", action="store_true")
    sp.add_argument("--restore", metavar="FILE")
    sp.add_argument("--prune", action="store_true")
    sp.add_argument("--keep", type=int, default=10)
    sp.set_defaults(func=cmd_backup)

    sp = sub.add_parser("scale", help="Scale game year")
    sp.add_argument("game")
    sp.add_argument("year", type=int)
    sp.add_argument("--save", action="store_true")
    sp.add_argument("--format", choices=["text", "json"], default="text")
    sp.set_defaults(func=cmd_scale)

    sp = sub.add_parser("stats", help="Cookbook statistics")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_stats)

    sp = sub.add_parser("report", help="Weekly cooking report")
    sp.add_argument("--date")
    sp.add_argument("--format", choices=["text", "json", "markdown"], default="text")
    sp.set_defaults(func=cmd_report)

    sp = sub.add_parser("serve", help="Read-only HTTP dashboard")
    sp.add_argument("--host", default="127.0.0.1")
    sp.add_argument("--port", type=int, default=8766)
    sp.set_defaults(func=cmd_serve)

    sp = sub.add_parser("bin", help="Pantry inventory")
    sp.add_argument("--add", nargs=2, metavar=("NAME", "QTY"))
    sp.add_argument("--remove", metavar="ID")
    sp.add_argument("--location")
    sp.add_argument("--expires")
    sp.add_argument("--expiring", action="store_true")
    sp.add_argument("--within", type=int, default=7)
    sp.set_defaults(func=cmd_bin)

    sp = sub.add_parser("bins", help="Pantry inventory (alias)")
    sp.add_argument("--add", nargs=2, metavar=("NAME", "QTY"))
    sp.add_argument("--remove", metavar="ID")
    sp.add_argument("--location")
    sp.add_argument("--expires")
    sp.add_argument("--expiring", action="store_true")
    sp.add_argument("--within", type=int, default=7)
    sp.set_defaults(func=cmd_bin)

    return p


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    parser = build_parser()
    ns = parser.parse_args(argv)
    try:
        return ns.func(ns)
    except GameboxError as exc:
        print("error: %s" % format_error(exc), file=sys.stderr)
        mapping = {"NOT_FOUND": 3, "VALIDATION_ERROR": 2, "IMPORT_ERROR": 2, "EXPORT_ERROR": 2, "STORAGE_ERROR": 5}
        return mapping.get(getattr(exc, "code", ""), 1)
    except KeyboardInterrupt:
        return 130
    except ValueError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())


_default_library_path = _default_cookbook_path
_library_path = _cookbook_path
