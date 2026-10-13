import unittest
from unittest.mock import AsyncMock

from vorm import Session
from vorm.dialects.mysql import MySQLDialect

from apps.service.project_center import _replace_contributors, list_registered_users
from apps.service.tag import count_tags, tag_suggestions


class RecordingDialect(MySQLDialect):
    def __init__(self, results):
        super().__init__(None)
        self.results = iter(results)
        self.queries = []

    async def fetch(self, sql, params):
        self.queries.append((sql, params))
        return next(self.results)


class TagContributorTests(unittest.IsolatedAsyncioTestCase):
    def test_tags_merge_case_whitespace_and_duplicates_per_item(self):
        self.assertEqual(count_tags([
            [" Python ", "python", "", None],
            '["PYTHON", "Vue"]',
            ["vue", "FastAPI"],
            "invalid json",
            None,
        ]), [
            {"tag": "Python", "count": 2},
            {"tag": "Vue", "count": 2},
            {"tag": "FastAPI", "count": 1},
        ])

    async def test_suggestions_match_existing_tags_and_prioritize_exact_then_prefix(self):
        dialect = RecordingDialect([
            [{"tags": '["JavaScript", "Java", "Custom Platform"]'}, {"tags": '["JavaScript"]'}],
            [{"tags": '["Java", "JavaScript", "Learning Java"]'}],
        ])
        self.assertEqual(await tag_suggestions(Session(dialect), " jAvA ", 2), [
            {"tag": "Java", "count": 2},
            {"tag": "JavaScript", "count": 3},
        ])
        post_sql, post_params = dialect.queries[0]
        project_sql, project_params = dialect.queries[1]
        self.assertIn("`status` = %s", post_sql)
        self.assertEqual(post_params, ["published"])
        self.assertIn("`is_deleted` = %s", project_sql)
        self.assertEqual(project_params, [False])
        self.assertNotIn("`content`", post_sql)
        self.assertNotIn("`summary`", project_sql)

    async def test_candidates_exclude_current_user_in_database_query_before_limit(self):
        dialect = RecordingDialect([[]])
        self.assertEqual(await list_registered_users(Session(dialect), "Alex", 20, exclude_user_id=7), [])
        sql, params = dialect.queries[0]
        self.assertIn("`id` != %s", sql)
        self.assertIn("LIMIT %s", sql)
        self.assertEqual(params, [7, "%Alex%", "%Alex%", 20])

    async def test_contributor_save_removes_creator_and_invalid_ids(self):
        dialect = RecordingDialect([
            [{"id": 8, "user_id": "account-8", "user_name": "other", "mobile": ""}],
            [{"id": 1, "project_id": 3, "user_id": 7}],
        ])
        session = Session(dialect)
        session.save = AsyncMock()
        session.delete = AsyncMock()
        await _replace_contributors(session, 3, [7, 8, 8, 999], creator_id=7)
        session.save.assert_awaited_once()
        self.assertEqual(session.save.call_args.args[0].user_id, 8)
        session.delete.assert_awaited_once()
        self.assertEqual(session.delete.call_args.args[0].user_id, 7)


if __name__ == "__main__":
    unittest.main()
