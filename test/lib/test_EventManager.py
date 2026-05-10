from pathlib import Path
from collections.abc import Generator

import pytest
import sqlean as sqlite3
import sqlite_vec

from src.lib.Database import set_connection_for_testing
from src.lib.EventManager import EventManager


@pytest.fixture
def event_manager_connection(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[sqlite3.Connection, None, None]:
    db_path = str(tmp_path / "event_manager.db")
    monkeypatch.setattr("src.lib.Database.get_db_path", lambda: db_path)
    conn = sqlite3.connect(db_path)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    set_connection_for_testing(conn)
    try:
        yield conn
    finally:
        conn.close()


def test_historic_journal_replay_is_not_short_term_memory(event_manager_connection: sqlite3.Connection) -> None:
    manager = EventManager([])
    try:
        manager.add_historic_game_events([
            {
                "id": "Journal.2026-05-10T180356.01.log.000001",
                "event": "LoadGame",
                "timestamp": "2026-05-10T22:08:02Z",
                "Commander": "Dark",
            }
        ])

        manager.process()

        assert manager.get_short_term_memory() == []

        row = event_manager_connection.execute(
            "SELECT memorized_at, responded_at FROM events_v1"
        ).fetchone()
        assert row is not None
        assert row[0] is not None
        assert row[1] is not None
    finally:
        manager._timer_stop_event.set()
