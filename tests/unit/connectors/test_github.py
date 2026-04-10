from unittest.mock import MagicMock, patch, PropertyMock
from adapters.connectors.github import GitHubConnector
from domain.models import SourceType
from datetime import datetime, timezone
import pytest

@pytest.fixture
def mock_credentials():
    return {
        "personal_access_token": "ghp_test123",
        "repos": ["testorg/testrepo"]
    }

def test_pr_enrichment_creates_rich_document(mock_credentials):
    connector = GitHubConnector(mock_credentials, org_id="org-1")

    mock_pr = MagicMock()
    mock_pr.number = 47
    mock_pr.title = "Refactor payment service to use Stripe"
    mock_pr.body = "Switched from Razorpay to Stripe for international support"
    mock_pr.user.login = "arjun"
    mock_pr.merged = True
    mock_pr.merged_at = datetime(2025, 3, 12, tzinfo=timezone.utc)
    mock_pr.html_url = "https://github.com/testorg/testrepo/pull/47"
    mock_pr.get_files.return_value = [MagicMock(filename="payment_service.py", patch="- old\n+ new")]

    mock_repo = MagicMock()
    mock_repo.full_name = "testorg/testrepo"

    doc = connector._enrich_pr(mock_repo, mock_pr)

    assert doc is not None
    assert "PR #47" in doc.content
    assert "Refactor payment service" in doc.content
    assert "arjun" in doc.content
    assert "payment_service.py" in doc.content
    assert "Razorpay" in doc.content
    assert doc.source_type == SourceType.GITHUB_PR
    assert doc.authority_score == 0.9

def test_fetch_handles_github_exception_gracefully(mock_credentials):
    with patch('adapters.connectors.github.Github') as MockGithub:
        MockGithub.return_value.get_repo.side_effect = Exception("API rate limit")
        connector = GitHubConnector(mock_credentials, org_id="org-1")
        docs = connector.fetch_documents("org-1")
        assert docs == []  # must not raise

def test_missing_pat_raises_value_error():
    with pytest.raises(ValueError, match="personal_access_token"):
        GitHubConnector({"repos": []}, org_id="org-1")

def test_pr_without_body_still_creates_document(mock_credentials):
    connector = GitHubConnector(mock_credentials, org_id="org-1")
    mock_pr = MagicMock()
    mock_pr.number = 48
    mock_pr.title = "Fix typo"
    mock_pr.body = None  # no description
    mock_pr.merged = True
    mock_pr.merged_at = datetime(2025, 3, 1, tzinfo=timezone.utc)
    mock_pr.html_url = "https://github.com/testorg/testrepo/pull/48"
    mock_pr.get_files.return_value = []
    mock_repo = MagicMock()
    mock_repo.full_name = "testorg/testrepo"

    doc = connector._enrich_pr(mock_repo, mock_pr)
    assert doc is not None
    assert "No description provided" in doc.content
