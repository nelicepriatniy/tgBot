from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite

BRANCHES = ("sleep", "longevity", "sport")
BOLT_LEVELS = {
    "critical": "критично",
    "below": "ниже нормы",
    "normal": "норма",
    "good": "хорошо",
}


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def bolt_level_from_seconds(seconds: float) -> str:
    if seconds < 10:
        return "critical"
    if seconds < 20:
        return "below"
    if seconds < 30:
        return "normal"
    return "good"


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._db: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self.path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute("PRAGMA foreign_keys = ON")
        await self._create_tables()

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None

    @property
    def db(self) -> aiosqlite.Connection:
        if self._db is None:
            raise RuntimeError("Database is not connected")
        return self._db

    async def _create_tables(self) -> None:
        await self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                branch TEXT,
                subscribed INTEGER DEFAULT 0,
                lead_magnet_sent INTEGER DEFAULT 0,
                test_answers TEXT,
                bolt_seconds REAL,
                bolt_level TEXT,
                promo_code TEXT,
                promo_issued_at TEXT,
                offer_clicked INTEGER DEFAULT 0,
                drip_day INTEGER DEFAULT 0,
                drip_active INTEGER DEFAULT 0,
                drip_started_at TEXT,
                unsubscribed INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS funnel_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                branch TEXT,
                event TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        await self.db.commit()

    async def upsert_user(
        self,
        telegram_id: int,
        username: str | None = None,
        branch: str | None = None,
    ) -> dict[str, Any]:
        existing = await self.get_user(telegram_id)
        now = utcnow()
        if existing is None:
            await self.db.execute(
                """
                INSERT INTO users (
                    telegram_id, username, branch, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (telegram_id, username, branch, now, now),
            )
            await self.db.commit()
            if branch:
                await self.log_event(telegram_id, branch, "start")
            return await self.get_user(telegram_id)  # type: ignore[return-value]

        fields: list[str] = ["updated_at = ?"]
        values: list[Any] = [now]
        if username is not None:
            fields.append("username = ?")
            values.append(username)
        # Branch is sticky for lifecycle unless user had none
        if branch and not existing["branch"]:
            fields.append("branch = ?")
            values.append(branch)
            await self.log_event(telegram_id, branch, "start")
        elif not existing["branch"] and not branch:
            pass
        elif branch and existing["branch"] and not existing.get("test_answers"):
            # Allow branch change only before test completion
            if existing["branch"] != branch:
                fields.append("branch = ?")
                values.append(branch)
                await self.log_event(telegram_id, branch, "start")

        values.append(telegram_id)
        await self.db.execute(
            f"UPDATE users SET {', '.join(fields)} WHERE telegram_id = ?",
            values,
        )
        await self.db.commit()
        return await self.get_user(telegram_id)  # type: ignore[return-value]

    async def get_user(self, telegram_id: int) -> dict[str, Any] | None:
        async with self.db.execute(
            "SELECT * FROM users WHERE telegram_id = ?",
            (telegram_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def update_user(self, telegram_id: int, **fields: Any) -> None:
        if not fields:
            return
        fields["updated_at"] = utcnow()
        columns = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [telegram_id]
        await self.db.execute(
            f"UPDATE users SET {columns} WHERE telegram_id = ?",
            values,
        )
        await self.db.commit()

    async def set_branch(self, telegram_id: int, branch: str) -> None:
        user = await self.get_user(telegram_id)
        if user and user.get("branch") == branch:
            return
        await self.update_user(telegram_id, branch=branch)
        await self.log_event(telegram_id, branch, "start")

    async def mark_subscribed(self, telegram_id: int, branch: str | None) -> None:
        await self.update_user(telegram_id, subscribed=1)
        await self.log_event(telegram_id, branch, "subscribed")

    async def mark_lead_magnet(self, telegram_id: int, branch: str | None) -> None:
        await self.update_user(telegram_id, lead_magnet_sent=1)
        await self.log_event(telegram_id, branch, "lead_magnet")

    async def save_test_result(
        self,
        telegram_id: int,
        answers: dict[str, Any],
        bolt_seconds: float,
        branch: str | None,
        promo_code: str,
    ) -> str:
        level = bolt_level_from_seconds(bolt_seconds)
        now = utcnow()
        await self.update_user(
            telegram_id,
            test_answers=json.dumps(answers, ensure_ascii=False),
            bolt_seconds=bolt_seconds,
            bolt_level=level,
            promo_code=promo_code,
            promo_issued_at=now,
            drip_active=1,
            drip_day=0,
            drip_started_at=now,
        )
        await self.log_event(telegram_id, branch, "test_completed")
        return level

    async def mark_offer_click(self, telegram_id: int, branch: str | None) -> None:
        await self.update_user(telegram_id, offer_clicked=1)
        await self.log_event(telegram_id, branch, "offer_click")

    async def unsubscribe(self, telegram_id: int, branch: str | None) -> None:
        await self.update_user(telegram_id, unsubscribed=1, drip_active=0)
        await self.log_event(telegram_id, branch, "unsubscribed")

    async def log_event(
        self,
        telegram_id: int,
        branch: str | None,
        event: str,
    ) -> None:
        await self.db.execute(
            """
            INSERT INTO funnel_events (telegram_id, branch, event, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (telegram_id, branch, event, utcnow()),
        )
        await self.db.commit()

    async def users_for_drip(self, day: int) -> list[dict[str, Any]]:
        """Users who should receive drip letter for given day (1,2,3,5,7)."""
        async with self.db.execute(
            """
            SELECT * FROM users
            WHERE drip_active = 1
              AND unsubscribed = 0
              AND drip_started_at IS NOT NULL
              AND drip_day < ?
              AND test_answers IS NOT NULL
            """,
            (day,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def set_drip_day(self, telegram_id: int, day: int) -> None:
        await self.update_user(telegram_id, drip_day=day)
        if day >= 7:
            await self.update_user(telegram_id, drip_active=0)

    async def users_by_branch(self, branch: str | None = None) -> list[dict[str, Any]]:
        if branch:
            query = "SELECT * FROM users WHERE unsubscribed = 0 AND branch = ?"
            params: tuple[Any, ...] = (branch,)
        else:
            query = "SELECT * FROM users WHERE unsubscribed = 0"
            params = ()
        async with self.db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def funnel_stats(self) -> dict[str, Any]:
        events = ("start", "subscribed", "test_completed", "offer_click", "unsubscribed")
        result: dict[str, Any] = {"total": {}, "by_branch": {}}
        for event in events:
            async with self.db.execute(
                """
                SELECT COUNT(DISTINCT telegram_id) AS cnt
                FROM funnel_events WHERE event = ?
                """,
                (event,),
            ) as cursor:
                row = await cursor.fetchone()
                result["total"][event] = row["cnt"] if row else 0

            by_branch: dict[str, int] = {}
            async with self.db.execute(
                """
                SELECT branch, COUNT(DISTINCT telegram_id) AS cnt
                FROM funnel_events
                WHERE event = ? AND branch IS NOT NULL
                GROUP BY branch
                """,
                (event,),
            ) as cursor:
                rows = await cursor.fetchall()
                for r in rows:
                    by_branch[r["branch"]] = r["cnt"]
            result["by_branch"][event] = by_branch
        return result
