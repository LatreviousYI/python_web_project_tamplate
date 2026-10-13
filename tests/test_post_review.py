import asyncio
import sqlite3
import unittest
from unittest.mock import patch

from vorm import Session
from vorm.dialects.mysql import MySQLDialect

from apps.service import post as post_service


class SQLiteReviewDialect(MySQLDialect):
    """Execute the generated MySQL queries against an isolated local database."""

    def __init__(self, connection):
        super().__init__(None)
        self.connection = connection

    async def fetch(self, sql, params):
        return [dict(row) for row in self.connection.execute(sql.replace("%s", "?"), params)]

    async def execute(self, sql, params):
        return self.connection.execute(sql.replace("%s", "?"), params).rowcount

    async def execute_insert(self, sql, params):
        return self.connection.execute(sql.replace("%s", "?"), params).lastrowid


class PostReviewTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        self.addCleanup(self.connection.close)
        self.connection.executescript("""
            CREATE TABLE osc_post (
                id INTEGER PRIMARY KEY, user_id INTEGER, project_id INTEGER,
                type TEXT, title TEXT, summary TEXT, content TEXT, status TEXT,
                tags TEXT DEFAULT '[]', view_count INTEGER DEFAULT 0,
                like_count INTEGER DEFAULT 0, reply_count INTEGER DEFAULT 0,
                published_at TEXT, created_at TEXT, updated_at TEXT
            );
            CREATE TABLE osc_notification (
                id INTEGER PRIMARY KEY, recipient_id INTEGER, actor_id INTEGER,
                type TEXT, post_id INTEGER, reply_id INTEGER, content TEXT,
                is_read INTEGER, read_at TEXT, created_at TEXT, updated_at TEXT
            );
            INSERT INTO osc_post (id, user_id, type, title, content, status, created_at, updated_at)
            VALUES (1, 7, 'article', 'Edited article', 'Updated content', 'pending',
                    '2026-10-13 10:00:00', '2026-10-13 10:00:00');
        """)

    def session(self):
        return Session(SQLiteReviewDialect(self.connection))

    def notifications(self):
        return self.connection.execute("SELECT * FROM osc_notification").fetchall()

    async def test_concurrent_approvals_send_one_notification(self):
        await self.assert_concurrent_review({"pass": True}, "published", "approve")

    async def test_concurrent_rejections_send_one_notification(self):
        await self.assert_concurrent_review({"pass": False, "reason": "Rejected"}, "draft", "reject")

    async def assert_concurrent_review(self, result, status, notification_type):
        both_reviewing = asyncio.Event()
        started = 0

        async def verify(content):
            nonlocal started
            started += 1
            if started == 2:
                both_reviewing.set()
            await asyncio.wait_for(both_reviewing.wait(), timeout=2)
            return result

        with patch.object(post_service.betteryeah_utils, "verfiy_content", side_effect=verify):
            counts = await asyncio.gather(
                post_service.review_pending_posts(self.session()),
                post_service.review_pending_posts(self.session()),
            )
        self.assertEqual(sorted(counts), [0, 1])
        row = self.connection.execute("SELECT status FROM osc_post WHERE id = 1").fetchone()
        self.assertEqual(row["status"], status)
        notifications = self.notifications()
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]["type"], notification_type)
        self.assertEqual(notifications[0]["recipient_id"], 7)

    async def test_completed_review_cannot_publish_or_reject_again(self):
        post = await post_service.publish_post(self.session(), 1)
        published_at = post.published_at
        self.assertIsNone(await post_service.publish_post(self.session(), 1))
        self.assertIsNone(await post_service.reject_post(self.session(), 1))
        row = self.connection.execute("SELECT status, published_at FROM osc_post WHERE id = 1").fetchone()
        self.assertEqual(row["status"], "published")
        self.assertEqual(row["published_at"], str(published_at))

    async def test_withdrawn_or_deleted_post_during_review_is_skipped(self):
        for sql in ("UPDATE osc_post SET status = 'draft' WHERE id = 1", "DELETE FROM osc_post WHERE id = 1"):
            with self.subTest(sql=sql):
                self.connection.execute("UPDATE osc_post SET status = 'pending' WHERE id = 1")

                async def verify(content):
                    self.connection.execute(sql)
                    return {"pass": True}

                with patch.object(post_service.betteryeah_utils, "verfiy_content", side_effect=verify):
                    self.assertEqual(await post_service.review_pending_posts(self.session()), 0)
                self.assertEqual(len(self.notifications()), 0)

    async def test_new_submission_gets_its_own_notification(self):
        with patch.object(post_service.betteryeah_utils, "verfiy_content", return_value={"pass": True}):
            self.assertEqual(await post_service.review_pending_posts(self.session()), 1)
            self.connection.execute("UPDATE osc_post SET status = 'pending', content = 'Another edit' WHERE id = 1")
            self.assertEqual(await post_service.review_pending_posts(self.session()), 1)
        self.assertEqual(len(self.notifications()), 2)

    async def test_invalid_review_or_exception_keeps_post_pending(self):
        for result in (None, {}, RuntimeError("Review unavailable")):
            with self.subTest(result=result):
                kwargs = {"side_effect": result} if isinstance(result, Exception) else {"return_value": result}
                with patch.object(post_service.betteryeah_utils, "verfiy_content", **kwargs):
                    self.assertEqual(await post_service.review_pending_posts(self.session()), 0)
                row = self.connection.execute("SELECT status FROM osc_post WHERE id = 1").fetchone()
                self.assertEqual(row["status"], "pending")
                self.assertEqual(len(self.notifications()), 0)

    async def test_notification_failure_does_not_repeat_review(self):
        with (
            patch.object(post_service.betteryeah_utils, "verfiy_content", return_value={"pass": True}),
            patch.object(post_service.notification_service, "create_notification", side_effect=RuntimeError("Write failed")),
        ):
            self.assertEqual(await post_service.review_pending_posts(self.session()), 1)
            self.assertEqual(await post_service.review_pending_posts(self.session()), 0)


if __name__ == "__main__":
    unittest.main()
