"""Test the functions in the cleanowners module."""

import unittest
import uuid
from io import StringIO
from unittest.mock import MagicMock, patch

from cleanowners import (
    build_default_codeowners,
    cleanup_whitespace,
    commit_changes,
    get_codeowners_file,
    get_org,
    get_repos_iterator,
    get_usernames_from_codeowners,
    print_stats,
    remove_username_from_content,
)
from github import GithubException


class TestCommitChanges(unittest.TestCase):
    """Test the commit_changes function in cleanowners.py"""

    @patch("uuid.uuid4")
    def test_commit_changes(self, mock_uuid):
        """Test the commit_changes function."""
        mock_uuid.return_value = uuid.UUID("12345678123456781234567812345678")
        mock_repo = MagicMock()
        mock_repo.default_branch = "main"
        mock_repo.get_git_ref.return_value.object.sha = "abc123"
        mock_repo.create_git_ref.return_value = True
        mock_existing_file = MagicMock()
        mock_existing_file.sha = "existing_sha"
        mock_repo.get_contents.return_value = mock_existing_file
        mock_repo.update_file.return_value = True
        mock_repo.create_pull.return_value = "MockPullRequest"

        title = "Test Title"
        body = "Test Body"
        dependabot_file = "testing!"
        branch_name = "codeowners-12345678-1234-5678-1234-567812345678"
        commit_message = "Test commit message"
        result = commit_changes(
            title,
            body,
            mock_repo,
            dependabot_file,
            commit_message,
            "CODEOWNERS",
        )

        mock_repo.create_git_ref.assert_called_once_with(
            f"refs/heads/{branch_name}", "abc123"
        )
        mock_repo.get_contents.assert_called_once_with("CODEOWNERS", ref=branch_name)
        mock_repo.update_file.assert_called_once_with(
            "CODEOWNERS",
            commit_message,
            dependabot_file,
            "existing_sha",
            branch=branch_name,
        )
        mock_repo.create_pull.assert_called_once_with(
            title=title,
            body=body,
            head=branch_name,
            base="main",
        )

        self.assertEqual(result, "MockPullRequest")

    @patch("uuid.uuid4")
    def test_commit_changes_create_new_file(self, mock_uuid):
        """Test the commit_changes function when creating a new file."""
        mock_uuid.return_value = uuid.UUID("12345678123456781234567812345678")
        mock_repo = MagicMock()
        mock_repo.default_branch = "main"
        mock_repo.get_git_ref.return_value.object.sha = "abc123"
        mock_repo.create_git_ref.return_value = True
        mock_repo.create_file.return_value = True
        mock_repo.create_pull.return_value = "MockPullRequest"

        result = commit_changes(
            "Test Title",
            "Test Body",
            mock_repo,
            b"new content",
            "Test commit message",
            "CODEOWNERS",
            create_new=True,
        )

        branch_name = "codeowners-12345678-1234-5678-1234-567812345678"
        mock_repo.create_git_ref.assert_called_once_with(
            f"refs/heads/{branch_name}", "abc123"
        )
        mock_repo.create_file.assert_called_once_with(
            "CODEOWNERS",
            "Test commit message",
            b"new content",
            branch=branch_name,
        )
        mock_repo.get_contents.assert_not_called()
        self.assertEqual(result, "MockPullRequest")


class TestGetUsernamesFromCodeowners(unittest.TestCase):
    """Test the get_usernames_from_codeowners function in cleanowners.py"""

    def test_get_usernames_from_codeowners_ignore_teams(self):
        """Test the get_usernames_from_codeowners function."""
        codeowners_file_contents = """
        # Comment
        @user1
        @user2
        @org/team
        # Another comment
        @user3 @user4
        """.encode("ASCII")
        expected_usernames = ["user1", "user2", "user3", "user4"]

        result = get_usernames_from_codeowners(codeowners_file_contents)

        self.assertEqual(result, expected_usernames)

    def test_get_usernames_from_codeowners_with_teams(self):
        """Test the get_usernames_from_codeowners function."""
        codeowners_file_contents = """
        # Comment
        @user1
        @user2
        @org/team
        # Another comment
        @user3 @user4
        """.encode("ASCII")
        expected_usernames = ["user1", "user2", "org/team", "user3", "user4"]

        result = get_usernames_from_codeowners(codeowners_file_contents, False)

        self.assertEqual(result, expected_usernames)

    def test_get_usernames_from_codeowners_with_raw_bytes(self):
        """Test that get_usernames_from_codeowners works with raw bytes (large file path).

        Regression test for https://github.com/github-community-projects/cleanowners/issues/378
        When a CODEOWNERS file is large, blob().decode_content() returns raw bytes
        instead of a Contents object with a .decoded attribute.
        """
        codeowners_file_contents = b"* @user1 @user2\ndocs/* @user3\n"
        expected_usernames = ["user1", "user2", "user3"]

        result = get_usernames_from_codeowners(codeowners_file_contents)

        self.assertEqual(result, expected_usernames)

    def test_multiple_username_removals_are_cumulative(self):
        """Test that removing multiple usernames preserves all removals.

        Regression test for https://github.com/github-community-projects/cleanowners/issues/380
        The removal loop must accumulate changes rather than replacing from the
        original content each time, otherwise only the last removal survives.
        """
        codeowners_decoded = b"* @alice @bob @charlie\ndocs/* @alice\n"
        usernames_to_remove = ["alice", "bob"]

        codeowners_file_contents_new = codeowners_decoded
        changed_lines: set[int] = set()
        for username in usernames_to_remove:
            codeowners_file_contents_new = remove_username_from_content(
                codeowners_file_contents_new, username, changed_lines
            )
        codeowners_file_contents_new = cleanup_whitespace(
            codeowners_file_contents_new, changed_lines
        )

        remaining = get_usernames_from_codeowners(codeowners_file_contents_new)
        self.assertEqual(remaining, ["charlie"])
        self.assertNotIn(b"@alice", codeowners_file_contents_new)
        self.assertNotIn(b"@bob", codeowners_file_contents_new)

    def test_username_removal_does_not_corrupt_similar_names(self):
        """Test that removing @bob does not corrupt @bobsmith.

        The removal must use word-boundary matching so that @bob only matches
        the exact handle, not as a prefix of @bobsmith.
        """
        codeowners_decoded = b"* @bobsmith @bob @charlie\n"
        usernames_to_remove = ["bob"]

        codeowners_file_contents_new = codeowners_decoded
        changed_lines: set[int] = set()
        for username in usernames_to_remove:
            codeowners_file_contents_new = remove_username_from_content(
                codeowners_file_contents_new, username, changed_lines
            )
        codeowners_file_contents_new = cleanup_whitespace(
            codeowners_file_contents_new, changed_lines
        )

        remaining = get_usernames_from_codeowners(codeowners_file_contents_new)
        self.assertEqual(remaining, ["bobsmith", "charlie"])
        self.assertIn(b"@bobsmith", codeowners_file_contents_new)
        self.assertNotIn(b"@bob ", codeowners_file_contents_new)

    def test_username_removal_cleans_up_whitespace(self):
        """Test that removing usernames does not leave extra whitespace.

        After removing a username from between two others, the resulting
        double space should be collapsed to a single space, and trailing
        whitespace should be stripped.
        """
        codeowners_decoded = b"* @alice @bob @charlie\n"
        usernames_to_remove = ["bob"]

        codeowners_file_contents_new = codeowners_decoded
        changed_lines: set[int] = set()
        for username in usernames_to_remove:
            codeowners_file_contents_new = remove_username_from_content(
                codeowners_file_contents_new, username, changed_lines
            )
        codeowners_file_contents_new = cleanup_whitespace(
            codeowners_file_contents_new, changed_lines
        )

        self.assertEqual(codeowners_file_contents_new, b"* @alice @charlie\n")

    def test_username_removal_handles_crlf_line_endings(self):
        """Test that whitespace cleanup works with CRLF line endings.

        Windows-style line endings use \\r\\n. The trailing whitespace
        cleanup must strip spaces before \\r without consuming the \\r itself.
        """
        codeowners_decoded = b"* @alice @bob @charlie\r\n"
        usernames_to_remove = ["bob"]

        codeowners_file_contents_new = codeowners_decoded
        changed_lines: set[int] = set()
        for username in usernames_to_remove:
            codeowners_file_contents_new = remove_username_from_content(
                codeowners_file_contents_new, username, changed_lines
            )
        codeowners_file_contents_new = cleanup_whitespace(
            codeowners_file_contents_new, changed_lines
        )

        self.assertEqual(codeowners_file_contents_new, b"* @alice @charlie\r\n")

    def test_whitespace_cleanup_scoped_to_changed_lines(self):
        """Test that whitespace cleanup only affects lines where usernames were removed.

        Lines with intentional alignment spacing should not be modified
        if no username was removed from them.
        """
        codeowners_decoded = b"src/**    @alice @bob @charlie\ndocs/**   @dave\n"
        usernames_to_remove = ["bob"]

        codeowners_file_contents_new = codeowners_decoded
        changed_lines: set[int] = set()
        for username in usernames_to_remove:
            codeowners_file_contents_new = remove_username_from_content(
                codeowners_file_contents_new, username, changed_lines
            )
        codeowners_file_contents_new = cleanup_whitespace(
            codeowners_file_contents_new, changed_lines
        )

        # src line should be normalized (removal happened there)
        self.assertIn(b"src/** @alice @charlie", codeowners_file_contents_new)
        # docs line should be untouched (no removal happened there)
        self.assertIn(b"docs/**   @dave", codeowners_file_contents_new)


class TestGetOrganization(unittest.TestCase):
    """Test the get_org function in cleanowners.py"""

    def test_get_organization_succeeds(self):
        """Test the organization is valid."""
        organization = "my_organization"
        github_connection = MagicMock()

        mock_organization = MagicMock()
        github_connection.get_organization.return_value = mock_organization

        result = get_org(github_connection, organization)

        github_connection.get_organization.assert_called_once_with(organization)
        self.assertEqual(result, mock_organization)

    def test_get_organization_fails(self):
        """Test the organization is not valid."""
        organization = "my_organization"
        github_connection = MagicMock()

        github_connection.get_organization.side_effect = GithubException(
            404, {"message": "Not Found"}, None
        )
        result = get_org(github_connection, organization)

        github_connection.get_organization.assert_called_once_with(organization)
        self.assertIsNone(result)


class TestGetReposIterator(unittest.TestCase):
    """Test the get_repos_iterator function in evergreen.py"""

    def test_get_repos_iterator_with_organization(self):
        """Test the get_repos_iterator function with an organization"""
        organization = "my_organization"
        repository_list = []
        github_connection = MagicMock()

        mock_organization = MagicMock()
        mock_repositories = MagicMock()
        mock_organization.get_repos.return_value = mock_repositories
        github_connection.get_organization.return_value = mock_organization

        result = get_repos_iterator(organization, repository_list, github_connection)

        github_connection.get_organization.assert_called_once_with(organization)
        mock_organization.get_repos.assert_called_once()
        self.assertEqual(result, mock_repositories)

    def test_get_repos_iterator_with_repository_list(self):
        """Test the get_repos_iterator function with a repository list"""
        organization = None
        repository_list = ["org/repo1", "org2/repo2"]
        github_connection = MagicMock()

        mock_repository = MagicMock()
        mock_repository_list = [mock_repository, mock_repository]
        github_connection.get_repo.side_effect = mock_repository_list

        result = get_repos_iterator(organization, repository_list, github_connection)

        expected_calls = [
            unittest.mock.call("org/repo1"),
            unittest.mock.call("org2/repo2"),
        ]
        github_connection.get_repo.assert_has_calls(expected_calls)

        self.assertEqual(result, mock_repository_list)


class TestPrintStats(unittest.TestCase):
    """Test the print_stats function in cleanowners.py"""

    @patch("sys.stdout", new_callable=StringIO)
    def test_print_stats_all_counts(self, mock_stdout):
        """Test the print_stats function with all counts."""
        print_stats(5, 10, 2, 3, 4)
        expected_output = (
            "Found 4 users to remove\n"
            "Created 5 pull requests successfully\n"
            "Found 2 repositories missing or empty CODEOWNERS files\n"
            "Processed 3 repositories with a CODEOWNERS file\n"
            "50.0% of eligible repositories had pull requests created\n"
            "60.0% of repositories had CODEOWNERS files\n"
        )
        self.assertEqual(mock_stdout.getvalue(), expected_output)

    @patch("sys.stdout", new_callable=StringIO)
    def test_print_stats_no_pull_requests_needed(self, mock_stdout):
        """Test the print_stats function with no pull requests needed."""
        print_stats(0, 0, 2, 3, 4)
        expected_output = (
            "Found 4 users to remove\n"
            "Created 0 pull requests successfully\n"
            "Found 2 repositories missing or empty CODEOWNERS files\n"
            "Processed 3 repositories with a CODEOWNERS file\n"
            "No pull requests were needed\n"
            "60.0% of repositories had CODEOWNERS files\n"
        )
        self.assertEqual(mock_stdout.getvalue(), expected_output)

    @patch("sys.stdout", new_callable=StringIO)
    def test_print_stats_no_repositories_processed(self, mock_stdout):
        """Test the print_stats function with no repositories processed."""
        print_stats(0, 0, 0, 0, 0)
        expected_output = (
            "Found 0 users to remove\n"
            "Created 0 pull requests successfully\n"
            "Found 0 repositories missing or empty CODEOWNERS files\n"
            "Processed 0 repositories with a CODEOWNERS file\n"
            "No pull requests were needed\n"
            "No repositories were processed\n"
        )
        self.assertEqual(mock_stdout.getvalue(), expected_output)


class TestGetCodeownersFile(unittest.TestCase):
    """Test the get_codeowners_file function in cleanowners.py"""

    def setUp(self):
        self.repo = MagicMock()

    def test_codeowners_in_github_folder(self):
        """Test that a CODEOWNERS file in the .github folder is considered valid."""
        self.repo.get_contents.side_effect = lambda path: (
            MagicMock(size=1) if path == ".github/CODEOWNERS" else None
        )
        contents, path = get_codeowners_file(self.repo)
        self.assertIsNotNone(contents)
        self.assertEqual(path, ".github/CODEOWNERS")

    def test_codeowners_in_root(self):
        """Test that a CODEOWNERS file in the root is considered valid."""
        self.repo.get_contents.side_effect = lambda path: (
            MagicMock(size=1) if path == "CODEOWNERS" else None
        )
        contents, path = get_codeowners_file(self.repo)
        self.assertIsNotNone(contents)
        self.assertEqual(path, "CODEOWNERS")

    def test_codeowners_in_docs_folder(self):
        """Test that a CODEOWNERS file in a docs folder is considered valid."""
        self.repo.get_contents.side_effect = lambda path: (
            MagicMock(size=1) if path == "docs/CODEOWNERS" else None
        )
        contents, path = get_codeowners_file(self.repo)
        self.assertIsNotNone(contents)
        self.assertEqual(path, "docs/CODEOWNERS")

    def test_codeowners_not_found(self):
        """Test that a missing CODEOWNERS file is not considered valid because it doesn't exist."""
        self.repo.get_contents.side_effect = lambda path: None
        contents, path = get_codeowners_file(self.repo)
        self.assertIsNone(contents)
        self.assertIsNone(path)

    def test_codeowners_empty_file(self):
        """Test that an empty CODEOWNERS file is returned for further handling."""
        self.repo.get_contents.side_effect = lambda path: MagicMock(size=0)
        contents, path = get_codeowners_file(self.repo)
        self.assertIsNotNone(contents)
        self.assertEqual(path, ".github/CODEOWNERS")

    def test_codeowners_not_found_then_found(self):
        """Test that a later path is used when earlier ones are not found."""
        not_found = GithubException(404, {"message": "Not Found"}, None)
        self.repo.get_contents.side_effect = [not_found, MagicMock(size=1)]
        contents, path = get_codeowners_file(self.repo)
        self.assertIsNotNone(contents)
        self.assertEqual(path, "CODEOWNERS")


class TestBuildDefaultCodeowners(unittest.TestCase):
    """Test the build_default_codeowners function in cleanowners.py"""

    def test_build_default_codeowners_for_org(self):
        """Test placeholder uses org team handle."""
        repo = MagicMock()
        repo.owner.login = "my-org"
        repo.owner.type = "Organization"

        result = build_default_codeowners(repo)

        self.assertIn(b"@my-org/REPLACE_WITH_TEAM", result)

    def test_build_default_codeowners_for_user(self):
        """Test placeholder uses user handle."""
        repo = MagicMock()
        repo.owner.login = "my-user"
        repo.owner.type = "User"

        result = build_default_codeowners(repo)

        self.assertIn(b"@my-user", result)
