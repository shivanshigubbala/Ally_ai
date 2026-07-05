"""
Unit tests for backend.neurology.db.pgvector_tracker.sync_go_user_id

Tests the idempotency of sync_go_user_id: first call creates Go user and writes go_user_id,
second call returns the cached value without calling create_user again.

Mocks database operations and appointment_client.create_user to avoid real Postgres dependency.

Run inside Docker:
  docker compose -f docker-compose.checks.yml up --build --abort-on-container-exit --exit-code-from backend-checks
"""
import unittest
from unittest.mock import patch, MagicMock, call

from backend.neurology.db.pgvector_tracker import _ensure_schema_compatibility, sync_go_user_id


class TestSyncGoUserId(unittest.TestCase):
    """Test sync_go_user_id function."""

    @patch('backend.neurology.db.pgvector_tracker._conn')
    def test_ensure_schema_compatibility_migrates_integer_ids(self, mock_conn):
        """Existing integer-based user/session ids should be migrated to text."""
        mock_db_conn = MagicMock()
        mock_conn.return_value.__enter__ = MagicMock(return_value=mock_db_conn)
        mock_conn.return_value.__exit__ = MagicMock(return_value=None)

        mock_cursor = MagicMock()
        mock_db_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.side_effect = [(True,), ("integer",), (True,), ("integer",), (False,)]

        _ensure_schema_compatibility(mock_db_conn)

        executed_sql = [call_args[0][0] for call_args in mock_cursor.execute.call_args_list]
        self.assertIn("ALTER TABLE users ALTER COLUMN id TYPE TEXT USING id::text", executed_sql)
        self.assertIn("ALTER TABLE sessions DROP CONSTRAINT IF EXISTS sessions_user_id_fkey", executed_sql)
        self.assertIn("ALTER TABLE sessions ALTER COLUMN user_id TYPE TEXT USING user_id::text", executed_sql)

    @patch('backend.neurology.db.pgvector_tracker._conn')
    @patch('backend.neurology.db.pgvector_tracker.create_user')
    def test_sync_go_user_id_first_call_creates_user(self, mock_create_user, mock_conn):
        """
        Test first call to sync_go_user_id: creates Go user, writes go_user_id to DB.
        """
        # Setup mocks
        mock_create_user.return_value = 123  # Go service returns user_id 123

        # Mock cursor and connection context manager
        mock_cursor = MagicMock()
        mock_db_conn = MagicMock()
        mock_conn.return_value.__enter__ = MagicMock(return_value=mock_db_conn)
        mock_conn.return_value.__exit__ = MagicMock(return_value=None)

        # Mock the SELECT FOR UPDATE query: returns (None, "John Doe") initially
        mock_cursor.fetchone.return_value = (None, "John Doe")
        mock_db_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_db_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)

        # Call the function
        result = sync_go_user_id("john_doe")

        # Verify result
        self.assertEqual(result, 123)

        # Verify create_user was called with the name
        mock_create_user.assert_called_once_with("John Doe")

        # Verify UPDATE was executed to write go_user_id
        sql_calls = [call_args[0][0] if call_args and call_args[0] else "" for call_args in mock_cursor.execute.call_args_list]
        update_calls = [sql for sql in sql_calls if str(sql).strip().upper().startswith("UPDATE")]
        self.assertEqual(len(update_calls), 1)

    @patch('backend.neurology.db.pgvector_tracker._conn')
    @patch('backend.neurology.db.pgvector_tracker.create_user')
    def test_sync_go_user_id_cached_value_not_called_again(self, mock_create_user, mock_conn):
        """
        Test second call to sync_go_user_id: returns cached go_user_id, does NOT call create_user.
        """
        # Setup mocks
        mock_cursor = MagicMock()
        mock_db_conn = MagicMock()
        mock_conn.return_value.__enter__ = MagicMock(return_value=mock_db_conn)
        mock_conn.return_value.__exit__ = MagicMock(return_value=None)

        # Mock the SELECT FOR UPDATE query: returns (456, "John Doe") — go_user_id already set
        mock_cursor.fetchone.return_value = (456, "John Doe")
        mock_db_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_db_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)

        # Call the function
        result = sync_go_user_id("john_doe")

        # Verify result
        self.assertEqual(result, 456)

        # Verify create_user was NOT called
        mock_create_user.assert_not_called()

        # Verify UPDATE was NOT executed (only SELECT)
        sql_calls = [call_args[0][0] if call_args and call_args[0] else "" for call_args in mock_cursor.execute.call_args_list]
        update_calls = [sql for sql in sql_calls if str(sql).strip().upper().startswith("UPDATE")]
        self.assertEqual(len(update_calls), 0)

    @patch('backend.neurology.db.pgvector_tracker._conn')
    @patch('backend.neurology.db.pgvector_tracker.create_user')
    def test_sync_go_user_id_failure_does_not_write_go_user_id(self, mock_create_user, mock_conn):
        """
        Test failure case: create_user raises exception, go_user_id is NOT written.
        Exception bubbles up.
        """
        # Setup mocks
        mock_create_user.side_effect = Exception("Go service down")

        mock_cursor = MagicMock()
        mock_db_conn = MagicMock()
        mock_conn.return_value.__enter__ = MagicMock(return_value=mock_db_conn)
        mock_conn.return_value.__exit__ = MagicMock(return_value=None)

        # Mock the SELECT FOR UPDATE query: go_user_id is null
        mock_cursor.fetchone.return_value = (None, "John Doe")
        mock_db_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_db_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)

        # Call the function and expect exception
        with self.assertRaises(Exception) as context:
            sync_go_user_id("john_doe")

        self.assertIn("Go service down", str(context.exception))

        # Verify UPDATE was NOT executed (failure before commit)
        sql_calls = [call_args[0][0] if call_args and call_args[0] else "" for call_args in mock_cursor.execute.call_args_list]
        update_calls = [sql for sql in sql_calls if str(sql).strip().upper().startswith("UPDATE")]
        self.assertEqual(len(update_calls), 0)

    @patch('backend.neurology.db.pgvector_tracker._conn')
    @patch('backend.neurology.db.pgvector_tracker.create_user')
    def test_sync_go_user_id_row_lock_acquired(self, mock_create_user, mock_conn):
        """
        Test that row lock is acquired via FOR UPDATE.
        """
        # Setup mocks
        mock_create_user.return_value = 789
        mock_cursor = MagicMock()
        mock_db_conn = MagicMock()
        mock_conn.return_value.__enter__ = MagicMock(return_value=mock_db_conn)
        mock_conn.return_value.__exit__ = MagicMock(return_value=None)

        mock_cursor.fetchone.return_value = (None, "Jane Doe")
        mock_db_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_db_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)

        # Call the function
        sync_go_user_id("jane_doe")

        # Verify SELECT FOR UPDATE was executed
        sql_calls = [call_args[0][0] if call_args and call_args[0] else "" for call_args in mock_cursor.execute.call_args_list]
        select_calls = [sql for sql in sql_calls if "FOR UPDATE" in str(sql).upper()]
        self.assertEqual(len(select_calls), 1)


if __name__ == "__main__":
    unittest.main()
