"""Write the results to a markdown file"""

import os


def _write_repos_and_users_to_remove(file, repo_and_users_to_remove, header_suffix=""):
    """Write the repos and users to remove section to a file handle"""
    if repo_and_users_to_remove:
        file.write(f"## Repositories and Users to Remove{header_suffix}\n")
        for repo, users in repo_and_users_to_remove.items():
            file.write(f"{repo}\n")
            for user in users:
                file.write(f"- {user}\n")
            file.write("\n")


def _write_repos_missing_codeowners(file, repos_missing_codeowners, header_suffix=""):
    """Write the repos missing CODEOWNERS section to a file handle"""
    if repos_missing_codeowners:
        file.write(f"## Repositories Missing or Empty CODEOWNERS{header_suffix}\n")
        for repo in repos_missing_codeowners:
            file.write(f"- {repo}\n")
        file.write("\n")


def write_to_markdown(
    users_count,
    pull_count,
    no_codeowners_count,
    codeowners_count,
    repo_and_users_to_remove,
    repos_missing_codeowners,
):
    """Write the results to a markdown file"""
    with open("report.md", "w", encoding="utf-8") as file:
        file.write(
            "# Cleanowners Report\n\n"
            "## Overall Stats\n"
            f"{users_count} Users to Remove\n"
            f"{pull_count} Pull Requests created\n"
            f"{no_codeowners_count} Repositories missing or empty CODEOWNERS files\n"
            f"{codeowners_count} Repositories with CODEOWNERS file\n"
        )
        _write_repos_and_users_to_remove(file, repo_and_users_to_remove)
        _write_repos_missing_codeowners(file, repos_missing_codeowners)


def write_step_summary(
    pull_count,
    eligble_for_pr_count,
    no_codeowners_count,
    codeowners_count,
    users_count,
    repo_and_users_to_remove,
    repos_missing_codeowners,
    error=None,
    pull_request_urls=None,
    enable_github_actions_step_summary=False,
):
    """Write the results to the GitHub Actions step summary"""
    if not enable_github_actions_step_summary:
        return
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        print("GITHUB_STEP_SUMMARY not set, skipping step summary")
        return

    with open(summary_path, "a", encoding="utf-8") as file:
        all_clean = no_codeowners_count == 0 and users_count == 0
        stats_emoji = " :white_check_mark:" if all_clean else " :warning:"
        file.write(
            "# Cleanowners Report\n\n"
            f"## Overall Stats{stats_emoji}\n"
            f"- Found {users_count} users to remove\n"
            f"- Created {pull_count} pull requests successfully\n"
            f"- Found {no_codeowners_count} repositories missing or empty CODEOWNERS files\n"
            f"- Processed {codeowners_count} repositories with a CODEOWNERS file\n"
        )
        if eligble_for_pr_count == 0:
            file.write("- No pull requests were needed\n")
        else:
            file.write(
                f"- {round((pull_count / eligble_for_pr_count) * 100, 2)}% of eligible repositories had pull requests created\n"
            )
        if codeowners_count + no_codeowners_count == 0:
            file.write("- No repositories were processed\n")
        else:
            file.write(
                f"- {round((codeowners_count / (codeowners_count + no_codeowners_count)) * 100, 2)}% of repositories had CODEOWNERS files\n"
            )
        file.write("\n")
        warning_suffix = " :warning:" if not error else ""
        _write_repos_and_users_to_remove(file, repo_and_users_to_remove, warning_suffix)
        _write_repos_missing_codeowners(file, repos_missing_codeowners, warning_suffix)
        if pull_request_urls:
            file.write("## Pull Requests Created :link:\n")
            file.write("".join(f"- {url}\n" for url in pull_request_urls))
            file.write("\n")
        if error:
            file.write(f"## Error :x:\n\n{error}\n")
