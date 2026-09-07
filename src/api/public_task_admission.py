"""Tenant-local admission and lifecycle state for server-owned task IDs.

Admission is committed before worker dispatch. The ``video_tasks.task_id``
UNIQUE constraint is the physical collision authority; UUID collisions are
retried internally and never exposed as a client duplicate contract.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Callable

from sqlalchemy import Engine, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from .models import VideoTask
from .task_identity import PUBLIC_TASK_ID_GENERATION_COLLISION, new_task_id


PUBLIC_TASK_ADMISSION_STATE_INVALID = "PUBLIC_TASK_ADMISSION_STATE_INVALID"
PUBLIC_TASK_ROLLOUT_METADATA_INVALID = "PUBLIC_TASK_ROLLOUT_METADATA_INVALID"
PUBLIC_TASK_RESERVATION_CONFLICT_MODES = frozenset({"OFF", "ENFORCE"})
PUBLIC_TASK_PLANNING_POLICIES = frozenset(
    {"legacy", "exact_main_visual", "exact_main_visual_balanced"}
)
PUBLIC_TASK_RESERVATION_MODE_SOURCES = frozenset(
    {
        "DEFAULT_OFF",
        "EXPLICIT_OFF",
        "EXPLICIT_ENFORCE",
        "ROLLOUT_CANARY",
    }
)
_SERVER_ID_CLAIM_ATTEMPTS = 4
# Frozen persisted/config domain: [A-Za-z0-9._-]{1,64}.
_SAFE_ROLLOUT_GENERATION = re.compile(r"[A-Za-z0-9._-]{1,64}")


class PublicTaskAdmissionError(RuntimeError):
    """Base error for public task admission and lifecycle state."""


class PublicTaskAdmissionStateError(PublicTaskAdmissionError):
    """An admitted task row is missing or has an invalid lifecycle state."""

    def __init__(self) -> None:
        super().__init__(PUBLIC_TASK_ADMISSION_STATE_INVALID)


@dataclass(frozen=True)
class PublicTaskReservationModeDecision:
    reservation_conflict_mode: str
    reservation_mode_source: str
    rollout_generation: str | None = None
    rollout_bucket: int | None = None
    rollout_canary_basis_points: int | None = None


@dataclass(frozen=True)
class PublicTaskAdmission:
    task_id: str
    video_task_id: int
    planning_policy: str
    reservation_conflict_mode: str
    reservation_mode_source: str
    rollout_generation: str | None
    rollout_bucket: int | None
    rollout_canary_basis_points: int | None


def _session_factory(bind: Engine) -> Callable[[], Session]:
    return sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=bind,
        expire_on_commit=False,
    )


def _is_video_task_id_unique_violation(exc: IntegrityError) -> bool:
    """Recognize only SQLite's exact server task-ID unique violation."""
    return (
        isinstance(exc.orig, sqlite3.IntegrityError)
        and str(exc.orig) == "UNIQUE constraint failed: video_tasks.task_id"
    )


def _validate_rollout_metadata(
    planning_policy: str,
    decision: PublicTaskReservationModeDecision,
) -> None:
    """Reject metadata that cannot describe a validated public submission."""
    reservation_conflict_mode = decision.reservation_conflict_mode
    reservation_mode_source = decision.reservation_mode_source
    if (
        reservation_conflict_mode not in PUBLIC_TASK_RESERVATION_CONFLICT_MODES
        or planning_policy not in PUBLIC_TASK_PLANNING_POLICIES
        or reservation_mode_source not in PUBLIC_TASK_RESERVATION_MODE_SOURCES
        or (
            reservation_conflict_mode == "ENFORCE"
            and planning_policy == "legacy"
        )
    ):
        raise PublicTaskAdmissionError(PUBLIC_TASK_ROLLOUT_METADATA_INVALID)

    rollout_values = (
        decision.rollout_generation,
        decision.rollout_bucket,
        decision.rollout_canary_basis_points,
    )
    if reservation_mode_source == "ROLLOUT_CANARY":
        if (
            reservation_conflict_mode != "ENFORCE"
            or not isinstance(decision.rollout_generation, str)
            or _SAFE_ROLLOUT_GENERATION.fullmatch(
                decision.rollout_generation
            ) is None
            or isinstance(decision.rollout_bucket, bool)
            or not isinstance(decision.rollout_bucket, int)
            or not 0 <= decision.rollout_bucket < 10000
            or isinstance(decision.rollout_canary_basis_points, bool)
            or not isinstance(decision.rollout_canary_basis_points, int)
            or not 0 < decision.rollout_canary_basis_points <= 10000
            or decision.rollout_bucket
            >= decision.rollout_canary_basis_points
        ):
            raise PublicTaskAdmissionError(PUBLIC_TASK_ROLLOUT_METADATA_INVALID)
        return

    if any(value is not None for value in rollout_values):
        raise PublicTaskAdmissionError(PUBLIC_TASK_ROLLOUT_METADATA_INVALID)
    if (
        reservation_mode_source == "EXPLICIT_ENFORCE"
        and reservation_conflict_mode != "ENFORCE"
    ) or (
        reservation_mode_source in {"DEFAULT_OFF", "EXPLICIT_OFF"}
        and reservation_conflict_mode != "OFF"
    ):
        raise PublicTaskAdmissionError(PUBLIC_TASK_ROLLOUT_METADATA_INVALID)


def _claim_one(
    bind: Engine,
    *,
    task_id: str,
    prompt: str,
    batch_size: int,
    planning_policy: str,
    decision: PublicTaskReservationModeDecision,
) -> int:
    SessionLocal = _session_factory(bind)
    with SessionLocal() as session:
        task = VideoTask(
            task_id=task_id,
            prompt=prompt,
            batch_size=batch_size,
            status="queued",
            reservation_conflict_mode=decision.reservation_conflict_mode,
            planning_policy=planning_policy,
            reservation_mode_source=decision.reservation_mode_source,
            rollout_generation=decision.rollout_generation,
            rollout_bucket=decision.rollout_bucket,
            rollout_canary_basis_points=(
                decision.rollout_canary_basis_points
            ),
        )
        session.add(task)
        try:
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            if _is_video_task_id_unique_violation(exc):
                return 0
            raise
        return int(task.id)


def admit_public_task(
    bind: Engine,
    *,
    prompt: str | None,
    batch_size: int,
    reservation_conflict_mode: str = "OFF",
    planning_policy: str = "legacy",
    reservation_mode_source: str | None = None,
    rollout_generation: str | None = None,
    rollout_bucket: int | None = None,
    rollout_canary_basis_points: int | None = None,
    reservation_mode_resolver: (
        Callable[[str], PublicTaskReservationModeDecision] | None
    ) = None,
    task_id_factory: Callable[[], str] | None = None,
) -> PublicTaskAdmission:
    """Generate and durably admit one public task before worker dispatch."""
    default_decision = PublicTaskReservationModeDecision(
        reservation_conflict_mode=reservation_conflict_mode,
        reservation_mode_source=(
            reservation_mode_source
            or (
                "EXPLICIT_ENFORCE"
                if reservation_conflict_mode == "ENFORCE"
                else "DEFAULT_OFF"
            )
        ),
        rollout_generation=rollout_generation,
        rollout_bucket=rollout_bucket,
        rollout_canary_basis_points=rollout_canary_basis_points,
    )
    _validate_rollout_metadata(planning_policy, default_decision)
    generator = task_id_factory or new_task_id
    for _ in range(_SERVER_ID_CLAIM_ATTEMPTS):
        task_id = generator()
        decision = default_decision
        if reservation_mode_resolver is not None:
            try:
                resolved = reservation_mode_resolver(task_id)
                if not isinstance(
                    resolved,
                    PublicTaskReservationModeDecision,
                ):
                    raise PublicTaskAdmissionError(
                        PUBLIC_TASK_ROLLOUT_METADATA_INVALID
                    )
                _validate_rollout_metadata(planning_policy, resolved)
                decision = resolved
            except Exception:
                # A resolver is optional Default-ON control. Its failure must
                # not break admission of the already-validated OFF fallback.
                decision = default_decision
        video_task_id = _claim_one(
            bind,
            task_id=task_id,
            prompt=prompt or "",
            batch_size=batch_size,
            planning_policy=planning_policy,
            decision=decision,
        )
        if video_task_id:
            return PublicTaskAdmission(
                task_id=task_id,
                video_task_id=video_task_id,
                planning_policy=planning_policy,
                reservation_conflict_mode=decision.reservation_conflict_mode,
                reservation_mode_source=decision.reservation_mode_source,
                rollout_generation=decision.rollout_generation,
                rollout_bucket=decision.rollout_bucket,
                rollout_canary_basis_points=(
                    decision.rollout_canary_basis_points
                ),
            )

    raise PublicTaskAdmissionError(PUBLIC_TASK_ID_GENERATION_COLLISION)


def transition_public_task_status(
    bind: Engine,
    *,
    task_id: str,
    target_status: str,
) -> None:
    """Commit one truthful lifecycle transition in a short tenant session."""
    allowed_sources = {
        "processing": {"queued"},
        "completed": {"processing"},
        "failed": {"queued", "processing"},
    }
    if target_status not in allowed_sources:
        raise PublicTaskAdmissionStateError()

    SessionLocal = _session_factory(bind)
    with SessionLocal() as session:
        result = session.execute(
            update(VideoTask)
            .where(
                VideoTask.task_id == task_id,
                VideoTask.status.in_(allowed_sources[target_status]),
            )
            .values(
                status=target_status,
                finished_at=(
                    datetime.now(timezone.utc)
                    if target_status in {"completed", "failed"}
                    else None
                ),
            )
        )
        if result.rowcount != 1:
            session.rollback()
            raise PublicTaskAdmissionStateError()
        session.commit()
