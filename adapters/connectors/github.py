from domain.models import Document, SourceType
from ports.connector_port import ConnectorPort
from datetime import datetime, timezone
from typing import Optional
from github import Github, GithubException
import logging

logger = logging.getLogger(__name__)

# Authority scores — code is ground truth, PRs are high-authority decisions
AUTHORITY_SCORES = {
    "code":    1.0,   # source files — what the system actually does
    "pr":      0.9,   # why it was changed — architectural decisions
    "readme":  0.8,   # how to use it — intended behaviour
    "issue":   0.6,   # what was reported — problems and context
}

class GitHubConnector(ConnectorPort):
    """
    Fetches documents from GitHub repos.

    Priority order for ingestion:
    1. Merged PRs (last 90 days) — PR enrichment is the moat
    2. README files — entry point for every repo
    3. Source files (.py, .java, .js, .ts, .go, .rs) — code context
    4. Open issues (last 60 days) — active problems

    Never fetches: binaries, lock files, generated files, node_modules
    """

    SUPPORTED_CODE_EXTENSIONS = {
        '.py', '.java', '.js', '.ts', '.jsx', '.tsx',
        '.go', '.rs', '.rb', '.php', '.cs', '.cpp', '.c',
        '.md', '.txt', '.yaml', '.yml', '.json', '.toml'
    }

    SKIP_PATHS = {
        'node_modules', 'vendor', '.git', '__pycache__',
        'dist', 'build', '.next', 'target', 'venv', '.env'
    }

    def __init__(self, credentials: dict, org_id: str):
        self._org_id = org_id
        self._pat = credentials.get('personal_access_token')
        if not self._pat:
            raise ValueError("GitHub connector requires 'personal_access_token' in credentials")
        self._client = Github(self._pat)
        self._repo_names = credentials.get('repos', [])  # list of "owner/repo" strings

    def source_type(self) -> SourceType:
        return SourceType.GITHUB_PR  # primary type — overridden per-document in _to_document

    def fetch_documents(self, org_id: str, since: Optional[datetime] = None) -> list[Document]:
        documents = []
        since = since or datetime(2000, 1, 1, tzinfo=timezone.utc)

        logger.info(f"[GitHub] fetch_documents called with {len(self._repo_names)} repos: {self._repo_names}")

        if not self._repo_names:
            logger.warning("[GitHub] No repositories configured. Returning empty document list.")
            return documents

        for repo_name in self._repo_names:
            try:
                logger.debug(f"[GitHub] Fetching from repo: {repo_name}")
                repo = self._client.get_repo(repo_name)

                prs = self._fetch_prs(repo, since)
                readme = self._fetch_readme(repo)
                code_files = self._fetch_code_files(repo, since)
                issues = self._fetch_issues(repo, since)

                documents.extend(prs)
                documents.extend(readme)
                documents.extend(code_files)
                documents.extend(issues)

                logger.info(f"[GitHub] ✅ Fetched from {repo_name}: {len(prs)} PRs, {len(readme)} READMEs, {len(code_files)} code files, {len(issues)} issues")
            except Exception as e:
                logger.error(f"[GitHub] ❌ Failed to fetch {repo_name}: {e}", exc_info=True)
                continue

        logger.info(f"[GitHub] ✅ Total documents fetched: {len(documents)}")
        return documents

    def _fetch_prs(self, repo, since: datetime) -> list[Document]:
        """
        THE MOAT FEATURE.

        Each PR becomes a rich Document containing:
        - PR title and description (the human-written explanation of WHY)
        - Author and merge date (who decided this and when)
        - Files changed (what was affected)
        - First 2000 chars of diff (what actually changed)

        This answers: "why was X changed?", "who decided Y?", "what did the Z refactor touch?"
        """
        documents = []
        try:
            for pr in repo.get_pulls(state='closed', sort='updated', direction='desc'):
                if not pr.merged:
                    continue
                if pr.merged_at and pr.merged_at < since:
                    break  # PRs are sorted by updated, stop when we pass since

                doc = self._enrich_pr(repo, pr)
                if doc:
                    documents.append(doc)
        except GithubException as e:
            logger.error(f"[GitHub] PR fetch failed for {repo.full_name}: {e}")
        return documents

    def _enrich_pr(self, repo, pr) -> Optional[Document]:
        """Build a rich text representation of a PR for chunking."""
        try:
            changed_files = [f.filename for f in pr.get_files()]

            # Get first 2000 chars of diff for the most changed file
            diff_preview = ""
            for f in pr.get_files():
                if f.patch:
                    diff_preview = f.patch[:2000]
                    break

            content = f"""PR #{pr.number}: {pr.title}
Author: {pr.user.login}
Merged: {pr.merged_at.strftime('%B %d, %Y') if pr.merged_at else 'unknown'}
Repo: {repo.full_name}

Description:
{pr.body or 'No description provided.'}

Files changed ({len(changed_files)}):
{chr(10).join(changed_files[:20])}
{'... and more' if len(changed_files) > 20 else ''}

Key diff preview:
{diff_preview}
"""
            return Document(
                id=f"github_pr_{repo.full_name.replace('/', '_')}_{pr.number}",
                org_id=self._org_id,
                source_type=SourceType.GITHUB_PR,
                source_url=pr.html_url,
                title=f"PR #{pr.number}: {pr.title}",
                content=content,
                authority_score=AUTHORITY_SCORES["pr"],
                updated_at=pr.merged_at or pr.updated_at,
            )
        except Exception as e:
            logger.error(f"[GitHub] PR enrichment failed for PR #{pr.number}: {e}")
            return None

    def _fetch_readme(self, repo) -> list[Document]:
        try:
            readme = repo.get_readme()
            content = readme.decoded_content.decode('utf-8')
            return [Document(
                id=f"github_readme_{repo.full_name.replace('/', '_')}",
                org_id=self._org_id,
                source_type=SourceType.GITHUB_CODE,
                source_url=readme.html_url,
                title=f"README — {repo.full_name}",
                content=content,
                authority_score=AUTHORITY_SCORES["readme"],
                updated_at=datetime.now(timezone.utc),
            )]
        except Exception:
            return []

    def _fetch_code_files(self, repo, since: datetime) -> list[Document]:
        """Fetch source files — skip binaries, lock files, generated code.

        OPTIMIZED: Only fetch from recent commits (last 5), and limit to 5 files total.
        This avoids thousands of API calls and GitHub rate limiting.
        """
        documents = []
        try:
            # Only look at LAST 5 commits to avoid making 100+ API calls
            logger.debug(f"[GitHub] Fetching code files from recent commits (limit: 5)")
            commits = list(repo.get_commits(since=since))[:5]  # DRASTICALLY reduced from 50
            changed_paths = set()

            for commit in commits:
                for f in commit.files:
                    ext = '.' + f.filename.split('.')[-1] if '.' in f.filename else ''
                    if ext in self.SUPPORTED_CODE_EXTENSIONS:
                        if not any(skip in f.filename for skip in self.SKIP_PATHS):
                            changed_paths.add(f.filename)

            # Only fetch FIRST 5 files
            for path in list(changed_paths)[:5]:  # REDUCED from 30 to 5
                try:
                    logger.debug(f"[GitHub] Fetching code file: {path}")
                    file_content = repo.get_contents(path)
                    content = file_content.decoded_content.decode('utf-8', errors='ignore')
                    if len(content.strip()) < 50:  # skip near-empty files
                        continue
                    documents.append(Document(
                        id=f"github_code_{repo.full_name.replace('/', '_')}_{path.replace('/', '_')}",
                        org_id=self._org_id,
                        source_type=SourceType.GITHUB_CODE,
                        source_url=f"https://github.com/{repo.full_name}/blob/main/{path}",
                        title=f"{path} — {repo.full_name}",
                        content=content,
                        authority_score=AUTHORITY_SCORES["code"],
                        updated_at=datetime.now(timezone.utc),
                    ))
                except Exception as e:
                    logger.debug(f"[GitHub] Could not fetch {path}: {e}")
                    continue
        except GithubException as e:
            logger.error(f"[GitHub] Code file fetch failed: {e}")
        return documents

    def _fetch_issues(self, repo, since: datetime) -> list[Document]:
        documents = []
        try:
            for issue in repo.get_issues(state='all', since=since, sort='updated'):
                if issue.pull_request:
                    continue  # skip PRs listed as issues
                content = f"""Issue #{issue.number}: {issue.title}
State: {issue.state}
Author: {issue.user.login}
Created: {issue.created_at.strftime('%B %d, %Y')}
Labels: {', '.join(l.name for l in issue.labels) or 'none'}

{issue.body or 'No description.'}
"""
                documents.append(Document(
                    id=f"github_issue_{repo.full_name.replace('/', '_')}_{issue.number}",
                    org_id=self._org_id,
                    source_type=SourceType.GITHUB_CODE,
                    source_url=issue.html_url,
                    title=f"Issue #{issue.number}: {issue.title}",
                    content=content,
                    authority_score=AUTHORITY_SCORES["issue"],
                    updated_at=issue.updated_at,
                ))
        except GithubException as e:
            logger.error(f"[GitHub] Issue fetch failed: {e}")
        return documents
