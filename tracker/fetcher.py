from __future__ import annotations

import logging
import os
import re

import requests
from bs4 import BeautifulSoup
from github import Github, GithubException, RateLimitExceededException

from .models import ProjectConfig

logger = logging.getLogger(__name__)

_GITHUB_RE = re.compile(r"https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?(?:/.*)?$")
MAX_RELEASES = 5


class FetchError(Exception):
    pass


class RateLimitError(FetchError):
    pass


def fetch_changelog(project_cfg: ProjectConfig) -> str:
    """Return changelog text for a project using the best available source."""
    if project_cfg.changelog_url:
        return _scrape_url(project_cfg.changelog_url)

    github_match = _GITHUB_RE.match(project_cfg.repo) if project_cfg.repo else None
    if github_match:
        owner, repo = github_match.group(1), github_match.group(2)
        text = _fetch_github(owner, repo)
        if text:
            return text

    if project_cfg.homepage:
        return _scrape_url(project_cfg.homepage)

    logger.warning(
        "[%s] No repo, homepage, or changelog_url — skipping fetch.", project_cfg.name
    )
    return ""


def _fetch_github(owner: str, repo: str) -> str:
    token = os.environ.get("GITHUB_TOKEN")
    gh = Github(token)
    try:
        gh_repo = gh.get_repo(f"{owner}/{repo}")
        releases = list(gh_repo.get_releases()[:MAX_RELEASES])
        bodies = [r.body for r in releases if r.body and r.body.strip()]
        if bodies:
            return "\n\n---\n\n".join(
                f"## {releases[i].tag_name}\n{bodies[i]}"
                for i, b in enumerate(bodies)
            )
        # Fall back to CHANGELOG.md
        for filename in ("CHANGELOG.md", "CHANGELOG"):
            try:
                content = gh_repo.get_contents(filename)
                if hasattr(content, "decoded_content"):
                    return content.decoded_content.decode("utf-8", errors="replace")
            except GithubException:
                continue
        return ""
    except RateLimitExceededException:
        raise RateLimitError(f"GitHub API rate limit exceeded for {owner}/{repo}")
    except GithubException as exc:
        logger.error("GitHub API error for %s/%s: %s", owner, repo, exc)
        return ""


def _scrape_url(url: str) -> str:
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "software-tracker/1.0"})
        if not resp.ok:
            logger.warning("Fetching %s returned HTTP %s", url, resp.status_code)
            return ""
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()
        return soup.get_text(separator="\n", strip=True)
    except requests.RequestException as exc:
        logger.warning("Failed to fetch %s: %s", url, exc)
        return ""
