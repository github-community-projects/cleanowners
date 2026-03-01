"""Write the results to a markdown file"""

import os


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
        if repo_and_users_to_remove:
            file.write("## Repositories and Users to Remove\n")
            for repo, users in repo_and_users_to_remove.items():
                file.write(f"{repo}\n")
                for user in users:
                    file.write(f"- {user}\n")
                file.write("\n")
        if repos_missing_codeowners:
            file.write("## Repositories Missing or Empty CODEOWNERS\n")
            for repo in repos_missing_codeowners:
                file.write(f"- {repo}\n")
            file.write("\n")


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
):
    """Write the results to the GitHub Actions step summary"""
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return

    with open(summary_path, "a", encoding="utf-8") as file:
        file.write(
            "# Cleanowners Report\n\n"
            "## Overall Stats\n"
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
        if repo_and_users_to_remove:
            file.write("## Repositories and Users to Remove\n")
            for repo, users in repo_and_users_to_remove.items():
                file.write(f"{repo}\n")
                for user in users:
                    file.write(f"- {user}\n")
                file.write("\n")
        if repos_missing_codeowners:
            file.write("## Repositories Missing or Empty CODEOWNERS\n")
            for repo in repos_missing_codeowners:
                file.write(f"- {repo}\n")
            file.write("\n")
        if pull_request_urls:
            file.write("## Pull Requests Created\n")
            for url in pull_request_urls:
                file.write(f"- {url}\n")
            file.write("\n")
        if error:
            file.write(f"## Error\n\n{error}\n")
