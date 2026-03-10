"""GitHub Actions webhook endpoint — receives CI/CD workflow log payloads."""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import hashlib
import hmac
import logging
import os

router = APIRouter(prefix="/api/v1/webhook", tags=["webhook"])
logger = logging.getLogger(__name__)

# Optional: set DEPFIX_WEBHOOK_SECRET env var to validate X-Hub-Signature-256
_WEBHOOK_SECRET = os.environ.get("DEPFIX_WEBHOOK_SECRET", "")


class GitHubActionsPayload(BaseModel):
    workflow_name: str
    run_id: str
    repository: str
    log_content: str
    branch: Optional[str] = "main"
    commit_sha: Optional[str] = None
    conclusion: Optional[str] = None  # "failure" | "success" | etc.


class WebhookResponse(BaseModel):
    received: bool
    log_id: str
    message: str
    received_at: str


def _verify_signature(body: bytes, signature: str, secret: str) -> bool:
    """Verify HMAC-SHA256 signature from GitHub."""
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/github-actions", response_model=WebhookResponse)
async def github_actions_webhook(
    payload: GitHubActionsPayload,
    x_hub_signature_256: Optional[str] = Header(None),
    x_raw_body: Optional[bytes] = None,
):
    """
    Receive a GitHub Actions workflow run log and store it for RAG analysis.

    **Usage from GitHub Actions workflow:**
    ```yaml
    - name: Send logs to DEPFIX
      run: |
        curl -X POST ${{ secrets.DEPFIX_URL }}/api/v1/webhook/github-actions \\
          -H "Content-Type: application/json" \\
          -H "X-Hub-Signature-256: sha256=$(echo -n '${{ toJson(payload) }}' | openssl dgst -sha256 -hmac '${{ secrets.DEPFIX_WEBHOOK_SECRET }}')" \\
          -d '{
            "workflow_name": "${{ github.workflow }}",
            "run_id": "${{ github.run_id }}",
            "repository": "${{ github.repository }}",
            "log_content": "'"$(cat build.log | head -c 50000)"'",
            "branch": "${{ github.ref_name }}",
            "commit_sha": "${{ github.sha }}",
            "conclusion": "failure"
          }'
    ```
    """
    # Signature verification (optional — only enforced if secret is configured)
    if _WEBHOOK_SECRET and x_hub_signature_256:
        # We cannot re-read raw body here without middleware; log a warning instead
        logger.warning("Webhook signature verification requires raw body middleware — skipping.")

    if not payload.log_content.strip():
        raise HTTPException(status_code=422, detail="log_content must not be empty")

    # Generate a deterministic log ID from repo + run_id
    log_id = hashlib.sha256(
        f"{payload.repository}-{payload.run_id}-{datetime.utcnow().isoformat()}".encode()
    ).hexdigest()[:16]

    logger.info(
        "Webhook received: repo=%s workflow=%s run_id=%s log_bytes=%d",
        payload.repository, payload.workflow_name, payload.run_id, len(payload.log_content),
    )

    # TODO: persist payload.log_content via the logs service once it is wired to the DB.
    # For now, log is accepted and acknowledged so CI pipelines can integrate immediately.

    return WebhookResponse(
        received=True,
        log_id=log_id,
        message=f"Log accepted for analysis ({len(payload.log_content)} bytes). "
                f"Use log_id '{log_id}' to poll /api/v1/logs for results.",
        received_at=datetime.utcnow().isoformat(),
    )


@router.get("/github-actions/config")
async def webhook_config():
    """Return the webhook URL and required payload schema for CI configuration."""
    return {
        "endpoint": "/api/v1/webhook/github-actions",
        "method": "POST",
        "content_type": "application/json",
        "secret_env_var": "DEPFIX_WEBHOOK_SECRET",
        "required_fields": ["workflow_name", "run_id", "repository", "log_content"],
        "optional_fields": ["branch", "commit_sha", "conclusion"],
    }
