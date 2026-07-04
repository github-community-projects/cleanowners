"""A GitHub Action to suggest removal of non-organization members from CODEOWNERS files."""

import base64
import re
import uuid

import auth
import env
from github import GithubException, UnknownObjectException
from markdown_writer import write_step_summary, write_to_markdown


def get_org(github_connection, organization):
    """Get the organization object"""
    try:
        return github_connection.get_organization(organization)
    except UnknownObjectException:
        print(f"Organization {organization} not found")
        return None


def remove_username_from_content(content, username, changed_lines):
    """Remove a @username from CODEOWNERS content using line-scoped regex.

    Args:
        content: The current CODEOWNERS file content as bytes.
        username: The GitHub username to remove (without @).
        changed_lines: A set[int] tracking which line indices were modified.

    Returns:
        The updated content with the username removed.
    """
    pattern = re.escape(f"@{username}".encode("ASCII"))
    lines = content.split(b"\n")
    for i, line in enumerate(lines):
        new_line = re.sub(pattern + rb"(?=\s|$)", b"", line)
        if new_line != line:
            lines[i] = new_line
            changed_lines.add(i)
    return b"\n".join(lines)


def cleanup_whitespace(content, changed_lines):
    """Normalize whitespace only on lines where usernames were removed.

    Args:
        content: The CODEOWNERS file content as bytes.
        changed_lines: A set[int] of line indices to clean up.

    Returns:
        The content with extra whitespace removed on affected lines.
    """
    lines = content.split(b"\n")
    for i in changed_lines:
        lines[i] = re.sub(rb"[ \t]{2,}", b" ", lines[i])
        lines[i] = re.sub(rb"[ \t]+(?=\r?$)", b"", lines[i])
    return b"\n".join(lines)


def main():  # pragma: no cover
    """Run the main program"""

    # Get the environment variables
    (
        organization,
        repository_list,
        gh_app_id,
        gh_app_installation_id,
        gh_app_private_key_bytes,
        gh_app_enterprise_only,
        token,
        ghe,
        exempt_repositories_list,
        dry_run,
        title,
        body,
        commit_message,
        issue_report,
        enable_github_actions_step_summary,
    ) = env.get_env_vars()

    # Auth to GitHub.com or GHE
    github_connection = auth.auth_to_github(
        token,
        gh_app_id,
        gh_app_installation_id,
        gh_app_private_key_bytes,
        ghe,
        gh_app_enterprise_only,
    )

    pull_count = 0
    eligble_for_pr_count = 0
    no_codeowners_count = 0
    codeowners_count = 0
    users_count = 0

    if organization and not repository_list:
        gh_org = get_org(github_connection, organization)
        if not gh_org:
            raise ValueError(f"""Organization {organization} is not an organization and
            REPOSITORY environment variable was not set.
            Please set valid ORGANIZATION or set REPOSITORY environment
            variable
            """)

    # Get the repositories from the organization or list of repositories
    repos = get_repos_iterator(organization, repository_list, github_connection)

    repo_and_users_to_remove = {}
    repos_missing_codeowners = []
    pull_request_urls = []
    error_message = None
    try:
        for repo in repos:
            # Check if the repository is in the exempt_repositories_list
            if repo.full_name in exempt_repositories_list:
                print(
                    f"Skipping {repo.full_name} as it is in the exempt_repositories_list"
                )
                continue

            # Check to see if repository is archived
            if repo.archived:
                print(f"Skipping {repo.full_name} as it is archived")
                continue

            # Check to see if repository has a CODEOWNERS file
            file_changed = False
            codeowners_file_contents, codeowners_filepath = get_codeowners_file(repo)
            has_codeowners = codeowners_file_contents is not None
            codeowners_size = (
                getattr(codeowners_file_contents, "size", None)
                if has_codeowners
                else None
            )
            is_empty_codeowners = has_codeowners and codeowners_size == 0

            if not has_codeowners or is_empty_codeowners:
                repo_name = repo.full_name
                no_codeowners_count += 1
                repos_missing_codeowners.append(repo_name)

                if not has_codeowners:
                    print(f"{repo_name} does not have a CODEOWNERS file")
                else:
                    print(f"{repo_name} has an empty CODEOWNERS file")

                if dry_run:
                    continue

                suggested_codeowners = build_default_codeowners(repo)
                target_path = codeowners_filepath or ".github/CODEOWNERS"
                eligble_for_pr_count += 1
                try:
                    pull = commit_changes(
                        title,
                        body,
                        repo,
                        suggested_codeowners,
                        commit_message,
                        target_path,
                        create_new=not has_codeowners,
                    )
                    pull_count += 1
                    pull_request_urls.append(pull.html_url)
                    print(f"\tCreated pull request {pull.html_url}")
                except GithubException as e:
                    print(
                        f"\tFailed to create pull request"
                        f" (status {e.status}): {e.data}."
                        f" Check write permissions."
                    )
                continue

            codeowners_count += 1

            if codeowners_file_contents.encoding == "none":
                blob = repo.get_git_blob(codeowners_file_contents.sha)
                codeowners_decoded = base64.b64decode(blob.content)
            else:
                codeowners_decoded = codeowners_file_contents.decoded_content

            # Extract the usernames from the CODEOWNERS file
            usernames = get_usernames_from_codeowners(codeowners_decoded)

            usernames_to_remove = []
            codeowners_file_contents_new = codeowners_decoded
            changed_lines: set[int] = set()
            for username in usernames:
                org = organization if organization else repo.owner.login
                gh_org = get_org(github_connection, org)
                if not gh_org:
                    print(f"Owner {org} of repo {repo} is not an organization.")
                    break

                # Check to see if the username is a member of the organization
                try:
                    member = github_connection.get_user(username)
                    is_member = gh_org.has_in_members(member)
                except UnknownObjectException:
                    is_member = False
                if not is_member:
                    print(
                        f"\t{username} is not a member of {org}. Suggest removing them from {repo.full_name}"
                    )
                    users_count += 1
                    usernames_to_remove.append(username)
                    if not dry_run:
                        # Remove that username from the codeowners_file_contents
                        file_changed = True
                        codeowners_file_contents_new = remove_username_from_content(
                            codeowners_file_contents_new, username, changed_lines
                        )

            # Store the repo and users to remove for reporting later
            if usernames_to_remove:
                repo_and_users_to_remove[repo] = usernames_to_remove

            # Clean up extra whitespace only on lines where usernames were removed
            if file_changed:
                codeowners_file_contents_new = cleanup_whitespace(
                    codeowners_file_contents_new, changed_lines
                )

            # Update the CODEOWNERS file if usernames were removed
            if file_changed:
                eligble_for_pr_count += 1
                new_usernames = get_usernames_from_codeowners(
                    codeowners_file_contents_new
                )
                if len(new_usernames) == 0:
                    print(
                        f"\twarning: All usernames removed from CODEOWNERS in {repo.full_name}."
                    )
                try:
                    pull = commit_changes(
                        title,
                        body,
                        repo,
                        codeowners_file_contents_new,
                        commit_message,
                        codeowners_filepath,
                    )
                    pull_count += 1
                    pull_request_urls.append(pull.html_url)
                    print(f"\tCreated pull request {pull.html_url}")
                except GithubException as e:
                    print(
                        f"\tFailed to create pull request"
                        f" (status {e.status}): {e.data}."
                        f" Check write permissions."
                    )
                    continue
    except Exception as e:  # pylint: disable=broad-exception-caught
        error_message = str(e)
        print(f"Error: {error_message}")
    finally:
        # Report the statistics from this run
        print_stats(
            pull_count=pull_count,
            eligble_for_pr_count=eligble_for_pr_count,
            no_codeowners_count=no_codeowners_count,
            codeowners_count=codeowners_count,
            users_count=users_count,
        )

        write_step_summary(
            pull_count=pull_count,
            eligble_for_pr_count=eligble_for_pr_count,
            no_codeowners_count=no_codeowners_count,
            codeowners_count=codeowners_count,
            users_count=users_count,
            repo_and_users_to_remove=repo_and_users_to_remove,
            repos_missing_codeowners=repos_missing_codeowners,
            error=error_message,
            pull_request_urls=pull_request_urls,
            enable_github_actions_step_summary=enable_github_actions_step_summary,
        )

        if issue_report:
            write_to_markdown(
                users_count,
                pull_count,
                no_codeowners_count,
                codeowners_count,
                repo_and_users_to_remove,
                repos_missing_codeowners,
            )

    if error_message:
        raise SystemExit(1)


def get_codeowners_file(repo):
    """
    Get the CODEOWNERS file from the repository and return
    the file contents and file path or None if it doesn't exist
    """
    codeowners_file_contents = None
    for path in (".github/CODEOWNERS", "CODEOWNERS", "docs/CODEOWNERS"):
        try:
            codeowners_file_contents = repo.get_contents(path)
            if codeowners_file_contents:
                return codeowners_file_contents, path
        except UnknownObjectException:
            continue
    return None, None


def print_stats(
    pull_count, eligble_for_pr_count, no_codeowners_count, codeowners_count, users_count
):
    """Print the statistics from this run to the terminal output"""
    print(f"Found {users_count} users to remove")
    print(f"Created {pull_count} pull requests successfully")
    print(f"Found {no_codeowners_count} repositories missing or empty CODEOWNERS files")
    print(f"Processed {codeowners_count} repositories with a CODEOWNERS file")
    if eligble_for_pr_count == 0:
        print("No pull requests were needed")
    else:
        print(
            f"{round((pull_count / eligble_for_pr_count) * 100, 2)}% of eligible repositories had pull requests created"
        )
    if codeowners_count + no_codeowners_count == 0:
        print("No repositories were processed")
    else:
        print(
            f"{round((codeowners_count / (codeowners_count + no_codeowners_count)) * 100, 2)}% of repositories had CODEOWNERS files"
        )


def get_repos_iterator(organization, repository_list, github_connection):
    """Get the repositories from the organization or list of repositories"""
    repos = []
    if organization and not repository_list:
        repos = github_connection.get_organization(organization).get_repos()
    else:
        for full_repo_path in repository_list:
            repos.append(github_connection.get_repo(full_repo_path))

    return repos


def get_usernames_from_codeowners(codeowners_file_contents, ignore_teams=True):
    """Extract the usernames from the CODEOWNERS file"""
    usernames = []
    for line in codeowners_file_contents.splitlines():
        if line:
            line = line.decode() if isinstance(line, bytes) else line
            # skip comments
            if line.lstrip().startswith("#"):
                continue
            # skip empty lines
            if not line.strip():
                continue
            # Identify handles
            if "@" in line:
                handles = line.split("@")[1:]
                for handle in handles:
                    handle = handle.split()[0]
                    # Identify team handles by the presence of a slash.
                    # Ignore teams because non-org members cannot be in a team.
                    if ignore_teams and "/" not in handle:
                        usernames.append(handle)
                    elif not ignore_teams:
                        usernames.append(handle)
    return usernames


def build_default_codeowners(repo):
    """Build a placeholder CODEOWNERS file for repositories without one."""
    owner_login = repo.owner.login
    owner_type = getattr(repo.owner, "type", "")
    if owner_type == "Organization":
        owner_handle = f"{owner_login}/REPLACE_WITH_TEAM"
    else:
        owner_handle = owner_login

    contents = (
        "# CODEOWNERS\n"
        "# Replace the placeholder with the appropriate owner(s) for this repository.\n"
        f"* @{owner_handle}\n"
    )
    return contents.encode("ASCII")


def commit_changes(
    title,
    body,
    repo,
    codeowners_file_contents_new,
    commit_message,
    codeowners_filepath,
    create_new=False,
):
    """Commit the changes to the repo and open a pull request and return the pull request object"""
    default_branch = repo.default_branch
    default_branch_commit = repo.get_git_ref(f"heads/{default_branch}").object.sha
    front_matter = "refs/heads/"
    branch_name = f"codeowners-{str(uuid.uuid4())}"
    repo.create_git_ref(front_matter + branch_name, default_branch_commit)
    if create_new:
        repo.create_file(
            codeowners_filepath,
            commit_message,
            codeowners_file_contents_new,
            branch=branch_name,
        )
    else:
        existing_file = repo.get_contents(codeowners_filepath, ref=branch_name)
        repo.update_file(
            codeowners_filepath,
            commit_message,
            codeowners_file_contents_new,
            existing_file.sha,
            branch=branch_name,
        )

    pull = repo.create_pull(
        title=title, body=body, head=branch_name, base=repo.default_branch
    )
    return pull


if __name__ == "__main__":  # pragma: no cover
    main()
