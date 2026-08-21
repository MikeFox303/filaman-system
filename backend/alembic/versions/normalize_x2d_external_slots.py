"""normalize legacy X2D external slot identifiers

Revision ID: normalize_x2d_external_slots
Revises: add_spool_event_source_key

The Bambuddy plugin historically exposed Bambu virtual trays 254/255 as
slot indexes ``255-254`` / ``255-255``.  FilaMan persisted those as slot_no
1254/1255.  Newer plugin builds correctly expose canonical indexes
``255-0`` / ``255-1`` (slot_no 1000/1001).  Because slot updates are upserts,
old rows can survive an upgrade and appear as duplicate External Tray cards.

This data migration is intentionally scoped to printers using the ``bambuddy``
driver.  It preserves the legacy slot row when no canonical row exists, and
when both exist it merges an unassigned canonical row with the legacy
assignment, reparents slot history, then removes the stale row.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "normalize_x2d_external_slots"
down_revision: Union[str, Sequence[str], None] = "add_spool_event_source_key"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


printers = sa.table(
    "printers",
    sa.column("id", sa.Integer),
    sa.column("driver_key", sa.String),
)
slots = sa.table(
    "printer_slots",
    sa.column("id", sa.Integer),
    sa.column("printer_id", sa.Integer),
    sa.column("slot_no", sa.Integer),
    sa.column("name", sa.String),
    sa.column("custom_fields", sa.JSON),
)
assignments = sa.table(
    "printer_slot_assignments",
    sa.column("slot_id", sa.Integer),
    sa.column("spool_id", sa.Integer),
    sa.column("present", sa.Boolean),
    sa.column("rfid_uid", sa.String),
    sa.column("external_id", sa.String),
    sa.column("inserted_at", sa.DateTime(timezone=True)),
    sa.column("updated_at", sa.DateTime(timezone=True)),
    sa.column("meta", sa.JSON),
)
slot_events = sa.table(
    "printer_slot_events",
    sa.column("slot_id", sa.Integer),
)


_PAIRS = (
    (1254, 1000, "255-0"),
    (1255, 1001, "255-1"),
)


def _canonical_fields(raw: object, slot_index: str) -> dict:
    fields = dict(raw) if isinstance(raw, dict) else {}
    fields["slot_index"] = slot_index
    return fields


def _merge_meta(old: object, new: object) -> dict | None:
    old_meta = dict(old) if isinstance(old, dict) else {}
    new_meta = dict(new) if isinstance(new, dict) else {}
    if not old_meta and not new_meta:
        return None
    # Current canonical data wins on conflicts; legacy data only fills gaps.
    return {**old_meta, **new_meta}


def _migrate_connection(conn) -> None:
    printer_ids = conn.execute(
        sa.select(printers.c.id).where(printers.c.driver_key == "bambuddy")
    ).scalars().all()

    for printer_id in printer_ids:
        for legacy_no, canonical_no, canonical_index in _PAIRS:
            legacy = conn.execute(
                sa.select(slots).where(
                    slots.c.printer_id == printer_id,
                    slots.c.slot_no == legacy_no,
                )
            ).mappings().first()
            if legacy is None:
                continue

            canonical = conn.execute(
                sa.select(slots).where(
                    slots.c.printer_id == printer_id,
                    slots.c.slot_no == canonical_no,
                )
            ).mappings().first()

            if canonical is None:
                # Keep the same slot id so its assignment and history remain attached.
                conn.execute(
                    sa.update(slots)
                    .where(slots.c.id == legacy["id"])
                    .values(
                        slot_no=canonical_no,
                        custom_fields=_canonical_fields(
                            legacy.get("custom_fields"), canonical_index
                        ),
                    )
                )
                continue

            legacy_assignment = conn.execute(
                sa.select(assignments).where(
                    assignments.c.slot_id == legacy["id"]
                )
            ).mappings().first()
            canonical_assignment = conn.execute(
                sa.select(assignments).where(
                    assignments.c.slot_id == canonical["id"]
                )
            ).mappings().first()

            if legacy_assignment is not None and canonical_assignment is None:
                # Reparent the assignment directly; slot_id is its primary key.
                conn.execute(
                    sa.update(assignments)
                    .where(assignments.c.slot_id == legacy["id"])
                    .values(slot_id=canonical["id"])
                )
            elif legacy_assignment is not None and canonical_assignment is not None:
                # A newly created canonical slot is commonly empty while the legacy
                # row still owns the user's spool.  Preserve that ownership.  If both
                # rows own different spools, canonical/current state wins.
                updates: dict[str, object] = {}
                if (
                    canonical_assignment.get("spool_id") is None
                    and legacy_assignment.get("spool_id") is not None
                ):
                    updates["spool_id"] = legacy_assignment.get("spool_id")
                    updates["present"] = bool(legacy_assignment.get("present"))
                    for key in ("rfid_uid", "external_id", "inserted_at"):
                        if canonical_assignment.get(key) is None:
                            updates[key] = legacy_assignment.get(key)
                elif (
                    not canonical_assignment.get("present")
                    and legacy_assignment.get("present")
                    and canonical_assignment.get("spool_id")
                    == legacy_assignment.get("spool_id")
                ):
                    updates["present"] = True

                merged_meta = _merge_meta(
                    legacy_assignment.get("meta"), canonical_assignment.get("meta")
                )
                if merged_meta != canonical_assignment.get("meta"):
                    updates["meta"] = merged_meta

                if updates:
                    conn.execute(
                        sa.update(assignments)
                        .where(assignments.c.slot_id == canonical["id"])
                        .values(**updates)
                    )
                conn.execute(
                    sa.delete(assignments).where(
                        assignments.c.slot_id == legacy["id"]
                    )
                )

            # Preserve audit/history events by pointing them at the canonical slot.
            conn.execute(
                sa.update(slot_events)
                .where(slot_events.c.slot_id == legacy["id"])
                .values(slot_id=canonical["id"])
            )

            canonical_name = canonical.get("name") or legacy.get("name")
            conn.execute(
                sa.update(slots)
                .where(slots.c.id == canonical["id"])
                .values(
                    name=canonical_name,
                    custom_fields=_canonical_fields(
                        canonical.get("custom_fields"), canonical_index
                    ),
                )
            )
            conn.execute(sa.delete(slots).where(slots.c.id == legacy["id"]))


def upgrade() -> None:
    _migrate_connection(op.get_bind())


def downgrade() -> None:
    # This migration only collapses duplicate representations of the same physical
    # X2D external tray. Re-introducing the invalid 1254/1255 rows would recreate
    # the bug, so downgrade is intentionally a no-op.
    pass
