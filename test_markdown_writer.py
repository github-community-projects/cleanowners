"""Unit tests for the write_to_markdown and write_step_summary functions in markdown_writer.py"""

import os
import unittest
from unittest.mock import call, mock_open, patch

from markdown_writer import write_step_summary, write_to_markdown


class TestWriteToMarkdown(unittest.TestCase):
    """Test the write_to_markdown function"""

    def test_write_with_all_counts_and_no_users_to_remove(self):
        """Test that the function writes the correct markdown when there are no users to remove"""
        mock_file = mock_open()
        with patch("builtins.open", mock_file):
            write_to_markdown(0, 0, 2, 3, {}, [])
            mock_file().write.assert_called_once_with(
                "# Cleanowners Report\n\n"
                "## Overall Stats\n"
                "0 Users to Remove\n"
                "0 Pull Requests created\n"
                "2 Repositories missing or empty CODEOWNERS files\n"
                "3 Repositories with CODEOWNERS file\n"
            )

    def test_write_with_repos_and_users_with_users_to_remove(self):
        """Test that the function writes the correct markdown when there are users to remove"""
        mock_file = mock_open()
        repo_users = {"repo1": ["user1", "user2"], "repo2": ["user3"]}
        with patch("builtins.open", mock_file):
            write_to_markdown(1, 2, 3, 4, repo_users, [])
            calls = [
                call(
                    "# Cleanowners Report\n\n"
                    "## Overall Stats\n"
                    "1 Users to Remove\n"
                    "2 Pull Requests created\n"
                    "3 Repositories missing or empty CODEOWNERS files\n"
                    "4 Repositories with CODEOWNERS file\n"
                ),
                call("## Repositories and Users to Remove\n"),
                call("repo1\n"),
                call("- user1\n"),
                call("- user2\n"),
                call("\n"),
                call("repo2\n"),
                call("- user3\n"),
                call("\n"),
            ]
            mock_file().write.assert_has_calls(calls, any_order=False)

    def test_write_with_repos_missing_codeowners(self):
        """Test that the function writes the correct markdown when there are repos missing CODEOWNERS"""
        mock_file = mock_open()
        repos_missing_codeowners = ["repo1", "repo2"]
        with patch("builtins.open", mock_file):
            write_to_markdown(0, 0, 2, 0, {}, repos_missing_codeowners)
            calls = [
                call(
                    "# Cleanowners Report\n\n"
                    "## Overall Stats\n"
                    "0 Users to Remove\n"
                    "0 Pull Requests created\n"
                    "2 Repositories missing or empty CODEOWNERS files\n"
                    "0 Repositories with CODEOWNERS file\n"
                ),
                call("## Repositories Missing or Empty CODEOWNERS\n"),
                call("- repo1\n"),
                call("- repo2\n"),
                call("\n"),
            ]
            mock_file().write.assert_has_calls(calls, any_order=False)

    def test_write_with_empty_inputs(self):
        """Test that the function writes the correct markdown when all inputs are 0"""
        mock_file = mock_open()
        with patch("builtins.open", mock_file):
            write_to_markdown(0, 0, 0, 0, {}, [])
            mock_file().write.assert_called_once_with(
                "# Cleanowners Report\n\n"
                "## Overall Stats\n"
                "0 Users to Remove\n"
                "0 Pull Requests created\n"
                "0 Repositories missing or empty CODEOWNERS files\n"
                "0 Repositories with CODEOWNERS file\n"
            )


class TestWriteStepSummary(unittest.TestCase):
    """Test the write_step_summary function"""

    @patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": "/tmp/test_summary.md"})
    def test_writes_basic_stats(self):
        """Test that basic stats are written correctly"""
        mock_file = mock_open()
        with patch("builtins.open", mock_file):
            write_step_summary(
                pull_count=0,
                eligble_for_pr_count=0,
                no_codeowners_count=2,
                codeowners_count=3,
                users_count=0,
                repo_and_users_to_remove={},
                repos_missing_codeowners=[],
            )
            mock_file.assert_called_once_with(
                "/tmp/test_summary.md", "a", encoding="utf-8"
            )
            written = "".join(c.args[0] for c in mock_file().write.call_args_list)
            self.assertIn("# Cleanowners Report", written)
            self.assertIn("Found 0 users to remove", written)
            self.assertIn("Created 0 pull requests successfully", written)
            self.assertIn(
                "Found 2 repositories missing or empty CODEOWNERS files", written
            )
            self.assertIn("Processed 3 repositories with a CODEOWNERS file", written)
            self.assertIn("No pull requests were needed", written)
            self.assertIn("60.0% of repositories had CODEOWNERS files", written)

    @patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": "/tmp/test_summary.md"})
    def test_writes_pr_percentage(self):
        """Test that PR percentage is calculated correctly"""
        mock_file = mock_open()
        with patch("builtins.open", mock_file):
            write_step_summary(
                pull_count=5,
                eligble_for_pr_count=10,
                no_codeowners_count=2,
                codeowners_count=3,
                users_count=4,
                repo_and_users_to_remove={},
                repos_missing_codeowners=[],
            )
            written = "".join(c.args[0] for c in mock_file().write.call_args_list)
            self.assertIn(
                "50.0% of eligible repositories had pull requests created", written
            )

    @patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": "/tmp/test_summary.md"})
    def test_writes_no_repositories_processed(self):
        """Test output when no repositories were processed"""
        mock_file = mock_open()
        with patch("builtins.open", mock_file):
            write_step_summary(
                pull_count=0,
                eligble_for_pr_count=0,
                no_codeowners_count=0,
                codeowners_count=0,
                users_count=0,
                repo_and_users_to_remove={},
                repos_missing_codeowners=[],
            )
            written = "".join(c.args[0] for c in mock_file().write.call_args_list)
            self.assertIn("No pull requests were needed", written)
            self.assertIn("No repositories were processed", written)

    @patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": "/tmp/test_summary.md"})
    def test_writes_users_to_remove(self):
        """Test that users to remove section is included"""
        mock_file = mock_open()
        repo_users = {"org/repo1": ["user1", "user2"], "org/repo2": ["user3"]}
        with patch("builtins.open", mock_file):
            write_step_summary(
                pull_count=2,
                eligble_for_pr_count=2,
                no_codeowners_count=0,
                codeowners_count=2,
                users_count=3,
                repo_and_users_to_remove=repo_users,
                repos_missing_codeowners=[],
            )
            written = "".join(c.args[0] for c in mock_file().write.call_args_list)
            self.assertIn("## Repositories and Users to Remove", written)
            self.assertIn("org/repo1", written)
            self.assertIn("- user1", written)
            self.assertIn("- user2", written)
            self.assertIn("org/repo2", written)
            self.assertIn("- user3", written)

    @patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": "/tmp/test_summary.md"})
    def test_writes_repos_missing_codeowners(self):
        """Test that repos missing CODEOWNERS section is included"""
        mock_file = mock_open()
        with patch("builtins.open", mock_file):
            write_step_summary(
                pull_count=0,
                eligble_for_pr_count=0,
                no_codeowners_count=2,
                codeowners_count=3,
                users_count=0,
                repo_and_users_to_remove={},
                repos_missing_codeowners=["org/repo1", "org/repo2"],
            )
            written = "".join(c.args[0] for c in mock_file().write.call_args_list)
            self.assertIn("## Repositories Missing or Empty CODEOWNERS", written)
            self.assertIn("- org/repo1", written)
            self.assertIn("- org/repo2", written)

    @patch.dict(os.environ, {}, clear=False)
    def test_noop_when_env_var_not_set(self):
        """Test that nothing happens when GITHUB_STEP_SUMMARY is not set"""
        # Remove the env var if it exists
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GITHUB_STEP_SUMMARY", None)
            mock_file = mock_open()
            with patch("builtins.open", mock_file):
                write_step_summary(
                    pull_count=0,
                    eligble_for_pr_count=0,
                    no_codeowners_count=0,
                    codeowners_count=0,
                    users_count=0,
                    repo_and_users_to_remove={},
                    repos_missing_codeowners=[],
                )
                mock_file.assert_not_called()

    @patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": "/tmp/test_summary.md"})
    def test_writes_error_when_provided(self):
        """Test that an error section is included when an error occurred"""
        mock_file = mock_open()
        with patch("builtins.open", mock_file):
            write_step_summary(
                pull_count=1,
                eligble_for_pr_count=2,
                no_codeowners_count=0,
                codeowners_count=3,
                users_count=0,
                repo_and_users_to_remove={},
                repos_missing_codeowners=[],
                error="API rate limit exceeded",
            )
            written = "".join(c.args[0] for c in mock_file().write.call_args_list)
            self.assertIn("## Error", written)
            self.assertIn("API rate limit exceeded", written)
            # Stats should still be present (partial results)
            self.assertIn("Processed 3 repositories with a CODEOWNERS file", written)

    @patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": "/tmp/test_summary.md"})
    def test_no_error_section_when_none(self):
        """Test that no error section appears when error is None"""
        mock_file = mock_open()
        with patch("builtins.open", mock_file):
            write_step_summary(
                pull_count=0,
                eligble_for_pr_count=0,
                no_codeowners_count=0,
                codeowners_count=3,
                users_count=0,
                repo_and_users_to_remove={},
                repos_missing_codeowners=[],
                error=None,
            )
            written = "".join(c.args[0] for c in mock_file().write.call_args_list)
            self.assertNotIn("## Error", written)

    @patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": "/tmp/test_summary.md"})
    def test_writes_pull_request_urls(self):
        """Test that PR URLs are included as clickable links"""
        mock_file = mock_open()
        with patch("builtins.open", mock_file):
            write_step_summary(
                pull_count=2,
                eligble_for_pr_count=2,
                no_codeowners_count=0,
                codeowners_count=2,
                users_count=1,
                repo_and_users_to_remove={},
                repos_missing_codeowners=[],
                pull_request_urls=[
                    "https://github.com/org/repo1/pull/42",
                    "https://github.com/org/repo2/pull/99",
                ],
            )
            written = "".join(c.args[0] for c in mock_file().write.call_args_list)
            self.assertIn("## Pull Requests Created", written)
            self.assertIn("https://github.com/org/repo1/pull/42", written)
            self.assertIn("https://github.com/org/repo2/pull/99", written)

    @patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": "/tmp/test_summary.md"})
    def test_no_pull_requests_section_when_empty(self):
        """Test that no PR section appears when no PRs were created"""
        mock_file = mock_open()
        with patch("builtins.open", mock_file):
            write_step_summary(
                pull_count=0,
                eligble_for_pr_count=0,
                no_codeowners_count=0,
                codeowners_count=3,
                users_count=0,
                repo_and_users_to_remove={},
                repos_missing_codeowners=[],
                pull_request_urls=[],
            )
            written = "".join(c.args[0] for c in mock_file().write.call_args_list)
            self.assertNotIn("## Pull Requests Created", written)


if __name__ == "__main__":
    unittest.main()
