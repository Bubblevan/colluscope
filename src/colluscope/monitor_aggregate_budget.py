"""Durable shared request/cost ledger for the bounded full-research Monitor run."""

from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import time
from typing import Any, Iterator


class AggregateBudgetError(RuntimeError):
    pass


PHASE_LIMITS = {
    "scripted_controls": (280, 1.00),
    "m4_trace_eval": (504, 1.50),
    "matched_worlds": (72, 0.50),
}
GLOBAL_REQUEST_LIMIT = 856
GLOBAL_COST_LIMIT_USD = 3.00


@contextmanager
def _file_lock(lock_path: Path) -> Iterator[None]:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as stream:
        if stream.seek(0, os.SEEK_END) == 0:
            stream.write(b"\0")
            stream.flush()
            os.fsync(stream.fileno())
        stream.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


class AggregateBudget:
    """Reserve a request slot before dispatch and never return it after failure."""

    def __init__(self, ledger_path: Path, execution_id: str):
        self.ledger_path = Path(ledger_path).resolve()
        self.lock_path = self.ledger_path.with_suffix(self.ledger_path.suffix + ".lock")
        self.execution_id = execution_id
        if not execution_id or any(ch in execution_id for ch in "\r\n"):
            raise AggregateBudgetError("invalid execution ID")

    def _read_unlocked(self) -> list[dict[str, Any]]:
        if not self.ledger_path.exists():
            return []
        rows = []
        for line_number, line in enumerate(self.ledger_path.read_text(encoding="utf-8").splitlines(), 1):
            if not line:
                raise AggregateBudgetError(f"blank aggregate ledger row {line_number}")
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise AggregateBudgetError(f"invalid aggregate ledger row {line_number}") from exc
            if not isinstance(row, dict):
                raise AggregateBudgetError(f"aggregate ledger row {line_number} is not an object")
            rows.append(row)
        self._validate_rows(rows)
        return rows

    def _validate_rows(self, rows: list[dict[str, Any]]) -> None:
        reservations: dict[str, dict[str, Any]] = {}
        terminals: set[str] = set()
        total_reserved = 0.0
        per_phase_count: dict[str, int] = {}
        per_phase_cost: dict[str, float] = {}
        for row in rows:
            if row.get("execution_id") != self.execution_id:
                raise AggregateBudgetError("aggregate ledger belongs to a different execution")
            event = row.get("event")
            request_id = row.get("request_id")
            if not isinstance(request_id, str) or not request_id:
                raise AggregateBudgetError("aggregate ledger row lacks a request ID")
            if event == "request_reserved":
                phase = row.get("phase_id")
                if phase not in PHASE_LIMITS or request_id in reservations:
                    raise AggregateBudgetError("unknown phase or duplicate aggregate request reservation")
                reserve = row.get("reserve_usd")
                body_sha256 = row.get("body_sha256")
                if (type(reserve) not in (int, float) or reserve < 0
                        or not isinstance(body_sha256, str) or len(body_sha256) != 64):
                    raise AggregateBudgetError("invalid aggregate request reservation")
                reservations[request_id] = row
                total_reserved += float(reserve)
                per_phase_count[phase] = per_phase_count.get(phase, 0) + 1
                per_phase_cost[phase] = per_phase_cost.get(phase, 0.0) + float(reserve)
            elif event == "request_terminal":
                if request_id not in reservations or request_id in terminals:
                    raise AggregateBudgetError("aggregate terminal lacks one unique prior reservation")
                if row.get("phase_id") != reservations[request_id].get("phase_id"):
                    raise AggregateBudgetError("aggregate terminal phase differs from reservation")
                actual_cost = row.get("actual_cost_usd")
                if actual_cost is not None and (
                        type(actual_cost) not in (int, float)
                        or actual_cost < 0
                        or actual_cost > float(reservations[request_id]["reserve_usd"]) + 1e-12):
                    raise AggregateBudgetError("aggregate terminal actual cost exceeds reservation")
                terminals.add(request_id)
            else:
                raise AggregateBudgetError("unknown aggregate ledger event")
        if len(reservations) > GLOBAL_REQUEST_LIMIT or total_reserved > GLOBAL_COST_LIMIT_USD + 1e-12:
            raise AggregateBudgetError("aggregate request or reserved-cost hard limit exceeded")
        for phase, (count_limit, cost_limit) in PHASE_LIMITS.items():
            if per_phase_count.get(phase, 0) > count_limit:
                raise AggregateBudgetError(f"aggregate phase request cap exceeded: {phase}")
            if per_phase_cost.get(phase, 0.0) > cost_limit + 1e-12:
                raise AggregateBudgetError(f"aggregate phase reserved-cost cap exceeded: {phase}")

    def _append_unlocked(self, row: dict[str, Any]) -> None:
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        encoded = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        with self.ledger_path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())

    def reserve(self, *, phase_id: str, request_id: str, body_sha256: str,
                reserve_usd: float, phase_request_cap: int, phase_cost_cap_usd: float) -> dict[str, Any]:
        if phase_id not in PHASE_LIMITS:
            raise AggregateBudgetError("phase ID is outside the approved allowlist")
        allowed_count, allowed_cost = PHASE_LIMITS[phase_id]
        if (not 1 <= phase_request_cap <= allowed_count
                or not 0 < phase_cost_cap_usd <= allowed_cost + 1e-12):
            raise AggregateBudgetError("configured phase cap exceeds the user-authorized phase limit")
        if not 0 <= reserve_usd <= phase_cost_cap_usd + 1e-12:
            raise AggregateBudgetError("single-request reservation exceeds the phase cost cap")
        with _file_lock(self.lock_path):
            rows = self._read_unlocked()
            reservations = {row["request_id"]: row for row in rows
                            if row.get("event") == "request_reserved"}
            if request_id in reservations:
                raise AggregateBudgetError("refusing to resend a request already reserved in the global ledger")
            phase_rows = [row for row in reservations.values() if row.get("phase_id") == phase_id]
            total_count = len(reservations)
            total_cost = sum(float(row["reserve_usd"]) for row in reservations.values())
            phase_cost = sum(float(row["reserve_usd"]) for row in phase_rows)
            if total_count >= GLOBAL_REQUEST_LIMIT:
                raise AggregateBudgetError("global request cap reached before dispatch")
            if len(phase_rows) >= phase_request_cap:
                raise AggregateBudgetError(f"phase request cap reached before dispatch: {phase_id}")
            if total_cost + reserve_usd > GLOBAL_COST_LIMIT_USD + 1e-12:
                raise AggregateBudgetError("global reserved-cost cap reached before dispatch")
            if phase_cost + reserve_usd > phase_cost_cap_usd + 1e-12:
                raise AggregateBudgetError(f"phase reserved-cost cap reached before dispatch: {phase_id}")
            row = {
                "event": "request_reserved", "execution_id": self.execution_id,
                "phase_id": phase_id, "request_id": request_id,
                "body_sha256": body_sha256, "reserve_usd": round(reserve_usd, 12),
                "at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            self._append_unlocked(row)
            return row

    def terminal(self, *, phase_id: str, request_id: str, status: str,
                 actual_cost_usd: float | None, http_status: int | None) -> None:
        with _file_lock(self.lock_path):
            rows = self._read_unlocked()
            reservations = {row["request_id"]: row for row in rows
                            if row.get("event") == "request_reserved"}
            terminals = {row["request_id"] for row in rows
                         if row.get("event") == "request_terminal"}
            reservation = reservations.get(request_id)
            if reservation is None or reservation.get("phase_id") != phase_id or request_id in terminals:
                raise AggregateBudgetError("terminal event lacks one unique matching reservation")
            if actual_cost_usd is not None and (
                    actual_cost_usd < 0
                    or actual_cost_usd > float(reservation["reserve_usd"]) + 1e-12):
                raise AggregateBudgetError("actual peak cost exceeds durable reservation")
            self._append_unlocked({
                "event": "request_terminal", "execution_id": self.execution_id,
                "phase_id": phase_id, "request_id": request_id,
                "status": status, "http_status": http_status,
                "actual_cost_usd": round(actual_cost_usd, 12) if actual_cost_usd is not None else None,
                "at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            })

    def reconcile_phase(self, *, phase_id: str,
                        local_attempts: list[dict[str, Any]],
                        local_progress: list[dict[str, Any]]) -> list[str]:
        """Close durable local attempts after a crash; return orphan reservations.

        An orphan reservation has no local `attempt_started`, so it is never
        eligible for dispatch on resume. Its slot remains consumed.
        """
        with _file_lock(self.lock_path):
            rows = self._read_unlocked()
            reservations = {row["request_id"]: row for row in rows
                            if row.get("event") == "request_reserved"
                            and row.get("phase_id") == phase_id}
            terminals = {row["request_id"] for row in rows
                         if row.get("event") == "request_terminal"
                         and row.get("phase_id") == phase_id}
            starts = {row["request_id"] for row in local_attempts
                      if row.get("event") == "attempt_started"}
            ends = {row["request_id"]: row for row in local_attempts
                    if row.get("event") == "attempt_terminal"}
            progress = {row["request_id"]: row for row in local_progress}
            unreserved_starts = starts - set(reservations)
            if unreserved_starts:
                raise AggregateBudgetError("local HTTP start has no prior global budget reservation")
            orphans = sorted(set(reservations) - starts)
            for request_id in sorted(set(reservations) & starts - terminals):
                end = ends.get(request_id)
                if end is None:
                    raise AggregateBudgetError("local started attempt lacks a terminal before budget reconciliation")
                row = progress.get(request_id, {})
                actual_cost = row.get("cost_upper_peak_usd")
                if type(actual_cost) not in (int, float):
                    actual_cost = None
                self._append_unlocked({
                    "event": "request_terminal", "execution_id": self.execution_id,
                    "phase_id": phase_id, "request_id": request_id,
                    "status": end.get("transport_status"),
                    "http_status": end.get("http_status"),
                    "actual_cost_usd": round(float(actual_cost), 12) if actual_cost is not None else None,
                    "reconciled_from_local_terminal": True,
                    "at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                })
            return orphans

    def rows(self) -> list[dict[str, Any]]:
        with _file_lock(self.lock_path):
            return self._read_unlocked()

    def summary(self) -> dict[str, Any]:
        rows = self.rows()
        reservations = [row for row in rows if row.get("event") == "request_reserved"]
        terminals = [row for row in rows if row.get("event") == "request_terminal"]
        by_phase = {}
        for phase in PHASE_LIMITS:
            phase_reservations = [row for row in reservations if row["phase_id"] == phase]
            phase_terminals = [row for row in terminals if row["phase_id"] == phase]
            by_phase[phase] = {
                "reserved_requests": len(phase_reservations),
                "terminal_requests": len(phase_terminals),
                "reserved_peak_cost_usd": round(sum(float(row["reserve_usd"])
                                                      for row in phase_reservations), 12),
                "reported_actual_cost_usd": round(sum(float(row["actual_cost_usd"] or 0.0)
                                                        for row in phase_terminals), 12),
            }
        return {
            "execution_id": self.execution_id,
            "reserved_requests": len(reservations),
            "terminal_requests": len(terminals),
            "reserved_peak_cost_usd": round(sum(float(row["reserve_usd"])
                                                  for row in reservations), 12),
            "reported_actual_cost_usd": round(sum(float(row.get("actual_cost_usd") or 0.0)
                                                    for row in terminals), 12),
            "global_request_cap": GLOBAL_REQUEST_LIMIT,
            "global_cost_cap_usd": GLOBAL_COST_LIMIT_USD,
            "per_phase": by_phase,
        }
