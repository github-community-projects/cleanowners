# Cleanowners action

[![CodeQL](https://github.com/github-community-projects/cleanowners/actions/workflows/github-code-scanning/codeql/badge.svg)](https://github.com/github-community-projects/cleanowners/actions/workflows/github-code-scanning/codeql) [![Lint Code Base](https://github.com/github-community-projects/cleanowners/actions/workflows/super-linter.yaml/badge.svg)](https://github.com/github-community-projects/cleanowners/actions/workflows/super-linter.yaml) [![Python package](https://github.com/github-community-projects/cleanowners/actions/workflows/python-ci.yml/badge.svg)](https://github.com/github-community-projects/cleanowners/actions/workflows/python-ci.yml) [![Docker Image CI](https://github.com/github-community-projects/cleanowners/actions/workflows/docker-ci.yml/badge.svg)](https://github.com/github-community-projects/cleanowners/actions/workflows/docker-ci.yml)[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/github-community-projects/cleanowners/badge)](https://scorecard.dev/viewer/?uri=github.com/github-community-projects/cleanowners)

Cleanowners is a GitHub Action that is designed to help keep `CODEOWNERS` files current by removing users that are no longer a part of the organization. This is helpful for companies that are looking to remove outdated information in the `CODEOWNERS` file. This action can be paired with other `CODEOWNERS` related actions to suggest new owners or lint `CODEOWNERS` files to ensure accuracy.

If a repository is missing a `CODEOWNERS` file (or it is empty), the action will open a pull request that adds a placeholder `CODEOWNERS` file for maintainers to update.

This action was developed by the GitHub OSPO for our own use and developed in a way that we could open source it that it might be useful to you as well! If you want to know more about how we use it, reach out in an issue in this repository.

## Support

If you need support using this project or have questions about it, please [open up an issue in this repository](https://github.com/github-community-projects/cleanowners/issues). Requests made directly to GitHub staff or support team will be redirected here to open an issue. GitHub SLA's and support/services contracts do not apply to this repository.

### OSPO GitHub Actions as a Whole

All feedback regarding our GitHub Actions, as a whole, should be communicated through [issues on our github-ospo repository](https://github.com/github/github-ospo/issues/new).

## Use as a GitHub Action

1. Create a repository to host this GitHub Action or select an existing repository.
1. Select a best fit workflow file from the [examples below](#example-workflows).
1. Copy that example into your repository (from step 1) and into the proper directory for GitHub Actions: `.github/workflows/` directory with the file extension `.yml` (ie. `.github/workflows/cleanowners.yml`)
1. Edit the values (`ORGANIZATION`, `EXEMPT_REPOS`) from the sample workflow with your information.
1. Also edit the value for `GH_ENTERPRISE_URL` if you are using a GitHub Server and not using github.com. For github.com users, don't put anything in here.
1. Update the value of `GH_TOKEN`. Do this by creating a [GitHub API token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#creating-a-personal-access-token-classic) with permissions to read the repository/organization and write issues or pull requests. Then take the value of the API token you just created, and [create a repository secret](https://docs.github.com/en/actions/security-guides/encrypted-secrets) where the name of the secret is `GH_TOKEN` and the value of the secret the API token. It just needs to match between when you create the secret name and when you refer to it in the workflow file.
1. Commit the workflow file to the default branch (often `master` or `main`)
1. Wait for the action to trigger based on the `schedule` entry or manually trigger the workflow as shown in the [documentation](https://docs.github.com/en/actions/using-workflows/manually-running-a-workflow).

### Configuration

Below are the allowed configuration options:

#### Authentication

This action can be configured to authenticate with GitHub App Installation or Personal Access Token (PAT). If all configuration options are provided, the GitHub App Installation configuration has precedence. You can choose one of the following methods to authenticate:

##### GitHub App Installation

| field                        | required | default | description                                                                                                                                                                                             |
| ---------------------------- | -------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `GH_APP_ID`                  | True     | `""`    | GitHub Application ID. See [documentation](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/about-authentication-with-a-github-app) for more details.              |
| `GH_APP_INSTALLATION_ID`     | True     | `""`    | GitHub Application Installation ID. See [documentation](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/about-authentication-with-a-github-app) for more details. |
| `GH_APP_PRIVATE_KEY`         | True     | `""`    | GitHub Application Private Key. See [documentation](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/about-authentication-with-a-github-app) for more details.     |
| `GITHUB_APP_ENTERPRISE_ONLY` | False    | `false` | Set this input to `true` if your app is created in GHE and communicates with GHE.                                                                                                                       |

##### Personal Access Token (PAT)

| field      | required | default | description                                                                                                           |
| ---------- | -------- | ------- | --------------------------------------------------------------------------------------------------------------------- |
| `GH_TOKEN` | True     | `""`    | The GitHub Token used to scan the repository. Must have read access to all repository you are interested in scanning. |

#### Other Configuration Options

| field               | required                                        | default | description                                                                                                                                                                                                                                           |
| ------------------- | ----------------------------------------------- | ------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `GH_ENTERPRISE_URL` | False                                           | ""      | The `GH_ENTERPRISE_URL` is used to connect to an enterprise server instance of GitHub. github.com users should not enter anything here.                                                                                                               |
| `ORGANIZATION`      | Required to have `ORGANIZATION` or `REPOSITORY` |         | The name of the GitHub organization which you want this action to work from. ie. github.com/github would be `github`                                                                                                                                  |
| `REPOSITORY`        | Required to have `ORGANIZATION` or `REPOSITORY` |         | The name of the repository and organization which you want this action to work from. ie. `github-community-projects/cleanowners` or a comma separated list of multiple repositories `github-community-projects/cleanowners,super-linter/super-linter` |
| `EXEMPT_REPOS`      | False                                           | ""      | These repositories will be exempt from this action. ex: If my org is set to `github` then I might want to exempt a few of the repos but get the rest by setting `EXEMPT_REPOS` to `github-community-projects/cleanowners,github/contributors`         |
| `DRY_RUN`           | False                                           | False   | If set to true, this action will not create any pull requests. It will only log the repositories that could have the `CODEOWNERS` file updated. This is useful for testing or discovering the scope of this issue in your organization.               |
| `ISSUE_REPORT`      | False                                           | False   | If set to true, this action will create an issue in the repository with the report on the repositories that had users removed from the `CODEOWNERS` file.                                                                                             |

### Example workflows

#### Basic

```yaml
---
name: Weekly codeowners cleanup
on:
  workflow_dispatch:
  schedule:
    - cron: "3 2 1 * *"

permissions:
  contents: read

jobs:
  cleanowners:
    name: cleanowners
    runs-on: ubuntu-latest
    permissions:
      issues: write

    steps:
      - name: Run cleanowners action
        uses: github-community-projects/cleanowners@v2
        env:
          GH_TOKEN: ${{ secrets.GH_TOKEN }}
          ORGANIZATION: <YOUR_ORGANIZATION_GOES_HERE>
```

#### Advanced

```yaml
---
name: Weekly codeowners cleanup
on:
  workflow_dispatch:
  schedule:
    - cron: "3 2 1 * *"

permissions:
  contents: read

jobs:
  cleanowners:
    name: cleanowners
    runs-on: ubuntu-latest
    permissions:
      issues: write

    steps:
      - name: Run cleanowners action
        uses: github-community-projects/cleanowners@v2
        env:
          GH_TOKEN: ${{ secrets.GH_TOKEN }}
          ORGANIZATION: <YOUR_ORGANIZATION_GOES_HERE>
          EXEMPT_REPOS: "org_name/repo_name_1, org_name/repo_name_2"
          ISSUE_REPORT: true
      - name: Create issue
        uses: peter-evans/create-issue-from-file@v5
        with:
          title: Cleanowners Report
          content-filepath: ./report.md
          assignees: <YOUR_GITHUB_HANDLE_HERE>
          token: ${{ secrets.GITHUB_TOKEN }}
```

### Authenticating with a GitHub App and Installation

You can authenticate as a GitHub App Installation by providing additional environment variables. If `GH_TOKEN` is set alongside these GitHub App Installation variables, the `GH_TOKEN` will be ignored and not used.

```yaml
---
name: Weekly codeowners cleanup via GitHub App
on:
  workflow_dispatch:
  schedule:
    - cron: "3 2 1 * *"

permissions:
  contents: read

jobs:
  cleanowners:
    name: cleanowners
    runs-on: ubuntu-latest
    permissions:
      issues: write

    steps:
      - name: Run cleanowners action
        uses: github-community-projects/cleanowners@v2
        env:
          GH_APP_ID: ${{ secrets.GH_APP_ID }}
          GH_APP_INSTALLATION_ID: ${{ secrets.GH_APP_INSTALLATION_ID }}
          GH_APP_PRIVATE_KEY: ${{ secrets.GH_APP_PRIVATE_KEY }}
          ORGANIZATION: <YOUR_ORGANIZATION_GOES_HERE>
          EXEMPT_REPOS: "org_name/repo_name_1, org_name/repo_name_2"
```

## Local usage without Docker

1. Make sure you have at least Python3.11 installed
1. Copy `.env-example` to `.env`
1. Fill out the `.env` file with a _token_ from a user that has access to the organization (listed below). Tokens should have at least write:org and write:repository access.
1. Fill out the `.env` file with the configuration parameters you want to use
1. `pip3 install -r requirements.txt`
1. Run `python3 ./cleanowners.py`, which will output everything in the terminal

## License

[MIT](LICENSE)

## More OSPO Tools

Looking for more resources for your open source program office (OSPO)? Check out the [`github-ospo`](https://github.com/github/github-ospo) repository for a variety of tools designed to support your needs.
