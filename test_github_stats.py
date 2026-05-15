import unittest

from github_stats import Stats


class LinesChangedTests(unittest.IsolatedAsyncioTestCase):
    async def test_lines_changed_case_insensitive_match(self) -> None:
        stats = Stats("TJIBA", "token", None)
        stats._repos = {"owner/repo"}
        stats._ignored_repos = set()

        async def fake_query_rest(path, params=None):
            self.assertEqual(path, "/repos/owner/repo/stats/contributors")
            self.assertIsNone(params)
            return [{
                "author": {"login": "tjiba"},
                "weeks": [{"a": 12, "d": 5}],
            }]

        stats.queries.query_rest = fake_query_rest

        self.assertEqual(await stats.lines_changed, (12, 5))

    async def test_lines_changed_falls_back_to_commit_stats(self) -> None:
        stats = Stats("Tjiba", "token", None)
        stats._repos = {"owner/repo"}
        stats._ignored_repos = set()

        async def fake_query_rest(path, params=None):
            if path == "/repos/owner/repo/stats/contributors":
                return []
            if path == "/repos/owner/repo/commits":
                if params["page"] == 1:
                    return [{"sha": "abc"}, {"sha": "def"}]
                return []
            if path == "/repos/owner/repo/commits/abc":
                return {"stats": {"additions": 7, "deletions": 3}}
            if path == "/repos/owner/repo/commits/def":
                return {"stats": {"additions": 11, "deletions": 2}}
            self.fail(f"Unexpected path: {path}")

        stats.queries.query_rest = fake_query_rest

        self.assertEqual(await stats.lines_changed, (18, 5))

    async def test_lines_changed_fallback_commit_limit(self) -> None:
        stats = Stats("Tjiba", "token", None)
        stats._repos = {"owner/repo"}
        stats._ignored_repos = set()
        stats._max_fallback_repos = 1
        stats._max_fallback_commits_per_repo = 3

        async def fake_query_rest(path, params=None):
            if path == "/repos/owner/repo/stats/contributors":
                return []
            if path == "/repos/owner/repo/commits":
                if params["page"] == 1:
                    return [{"sha": f"c{i}"} for i in range(100)]
                self.fail("Should not request next commit page when commit cap is reached")
            if path.startswith("/repos/owner/repo/commits/c"):
                return {"stats": {"additions": 1, "deletions": 0}}
            self.fail(f"Unexpected path: {path}")

        stats.queries.query_rest = fake_query_rest

        self.assertEqual(await stats.lines_changed, (3, 0))

    async def test_lines_changed_fallback_repo_limit(self) -> None:
        stats = Stats("Tjiba", "token", None)
        stats._repos = {"owner/repo1", "owner/repo2"}
        stats._ignored_repos = set()
        stats._max_fallback_repos = 1
        stats._max_fallback_commits_per_repo = 100
        commit_list_calls = 0

        async def fake_query_rest(path, params=None):
            nonlocal commit_list_calls
            if path.endswith("/stats/contributors"):
                return []
            if path.endswith("/commits"):
                if params["page"] == 1:
                    commit_list_calls += 1
                    return [{"sha": "one"}]
                return []
            if path.endswith("/commits/one"):
                return {"stats": {"additions": 2, "deletions": 1}}
            self.fail(f"Unexpected path: {path}")

        stats.queries.query_rest = fake_query_rest

        self.assertEqual(await stats.lines_changed, (2, 1))
        self.assertEqual(commit_list_calls, 1)


if __name__ == "__main__":
    unittest.main()
