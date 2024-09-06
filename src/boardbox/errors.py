"""Custom exceptions for boardbox — keep messages human-readable."""

from __future__ import annotations

from typing import Any

__author__ = "Marwan Helmy"


class BoardboxError(Exception):
    """Base error for all boardbox failures."""

    def __init__(self, message: str, code: str = "BOARDBOX_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class StorageError(BoardboxError):
    """Raised when JSON persistence read/write fails."""

    def __init__(self, message: str, path: str | None = None):
        self.path = path
        detail = message if path is None else "%s (%s)" % (message, path)
        super().__init__(detail, code="STORAGE_ERROR")


class ValidationError(BoardboxError):
    """Input failed schema or business validation."""

    def __init__(self, message: str, field: str | None = None, value: Any = None):
        self.field = field
        self.value = value
        detail = f"{field}: {message}" if field else message
        super().__init__(detail, code="VALIDATION_ERROR")


class NotFoundError(BoardboxError):
    """Entity lookup returned nothing."""

    def __init__(self, entity: str, identifier: str):
        super().__init__("no {0} matching '{1}'".format(entity, identifier), code="NOT_FOUND")
        self.entity = entity
        self.identifier = identifier


class ImportPipelineError(BoardboxError):
    """External import pipeline failed."""

    def __init__(self, source: str, message: str):
        super().__init__("[{source}] {message}".format(source=source, message=message), code="IMPORT_ERROR")
        self.source = source


class ExportError(BoardboxError):
    """Export pipeline failed."""

    def __init__(self, target: str, message: str):
        super().__init__(f"export to {target} failed — {message}", code="EXPORT_ERROR")
        self.target = target


class MigrationError(BoardboxError):
    """Schema migration could not complete."""

    def __init__(self, from_ver: int, to_ver: int, reason: str):
        super().__init__(
            "migration %d -> %d: %s" % (from_ver, to_ver, reason),
            code="MIGRATION_ERROR",
        )
        self.from_ver = from_ver
        self.to_ver = to_ver


class PluginError(BoardboxError):
    """Plugin load or hook execution failed."""

    pass


class ConflictError(BoardboxError):
    """Optimistic concurrency or duplicate key."""

    def __init__(self, message: str, key: str | None = None):
        self.key = key
        super().__init__(message, code="CONFLICT")


class ParseError(BoardboxError):
    """Unparseable user or file input."""

    def __init__(self, message: str, *, raw: str | None = None):
        self.raw = raw
        detail = message if raw is None else "%s (raw=%r)" % (message, raw)
        super().__init__(detail, code="PARSE_ERROR")


class ConversionError(BoardboxError):
    """Unit conversion failed."""

    def __init__(self, from_unit: str, to_unit: str, *, reason: str = ""):
        self.from_unit = from_unit
        self.to_unit = to_unit
        msg = "cannot convert %s to %s" % (from_unit, to_unit)
        if reason:
            msg = "%s — %s" % (msg, reason)
        super().__init__(msg, code="CONVERSION_ERROR")


class DuplicateError(BoardboxError):
    """Duplicate entity key."""

    def __init__(self, entity: str, identifier: str):
        self.entity = entity
        self.identifier = identifier
        super().__init__(
            "duplicate %s: %s" % (entity, identifier),
            code="DUPLICATE_ERROR",
        )


class CampaignError(BoardboxError):
    """Session plan slot or date constraint violated."""

    def __init__(
        self,
        message: str,
        *,
        day: str | None = None,
        meal_type: str | None = None,
    ):
        self.day = day
        self.meal_type = meal_type
        super().__init__(message, code="MEAL_PLAN_ERROR")


class WishlistError(BoardboxError):
    """Shopping list merge or build failed."""

    def __init__(self, message: str):
        super().__init__(message, code="WANT_LIST_ERROR")


def is_not_found(exc: BaseException) -> bool:
    return isinstance(exc, NotFoundError)


def format_error(exc: BoardboxError) -> str:
    return "%s: %s" % (exc.code, exc.message)


def import_pipeline_error(source: str, line_no: int, msg: str) -> ImportPipelineError:
    return ImportPipelineError(source, "line %d: %s" % (line_no, msg))


GameboxError = BoardboxError
RecipeboxError = BoardboxError
SessionLogError = CampaignError
NightPlanError = CampaignError
ShoppingListError = WishlistError
WishlistListError = WishlistError
