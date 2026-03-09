"""GitHub and GitLab API integration service."""

import os
import logging
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from backend.app.models.database import APIKey, User
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class GitHubService:
    """GitHub API integration."""
    
    def __init__(self, access_token: Optional[str] = None):
        self.access_token = access_token
        self.api_base = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {access_token}" if access_token else "",
            "Accept": "application/vnd.github.v3+json",
        }
    
    async def get_user_info(self) -> Optional[Dict]:
        """Get authenticated user info."""
        if not self.access_token:
            return None
        
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_base}/user",
                    headers=self.headers,
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to get GitHub user info: {e}")
            return None
    
    async def get_repositories(self) -> Optional[List[Dict]]:
        """Get list of user's repositories."""
        if not self.access_token:
            return None
        
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_base}/user/repos",
                    headers=self.headers,
                    params={"per_page": 30, "sort": "updated"},
                )
                response.raise_for_status()
                repos = response.json()
                return [
                    {
                        "id": repo["id"],
                        "name": repo["name"],
                        "full_name": repo["full_name"],
                        "url": repo["html_url"],
                        "description": repo["description"],
                    }
                    for repo in repos
                ]
        except Exception as e:
            logger.error(f"Failed to get repositories: {e}")
            return None
    
    async def get_workflow_runs(self, owner: str, repo: str, limit: int = 10) -> Optional[List[Dict]]:
        """Get recent GitHub Actions workflow runs."""
        if not self.access_token:
            return None
        
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_base}/repos/{owner}/{repo}/actions/runs",
                    headers=self.headers,
                    params={"per_page": limit, "status": "completed"},
                )
                response.raise_for_status()
                data = response.json()
                return [
                    {
                        "id": run["id"],
                        "name": run["name"],
                        "status": run["status"],
                        "conclusion": run["conclusion"],
                        "created_at": run["created_at"],
                        "url": run["html_url"],
                    }
                    for run in data.get("workflow_runs", [])
                ]
        except Exception as e:
            logger.error(f"Failed to get workflow runs: {e}")
            return None
    
    async def get_workflow_logs(self, owner: str, repo: str, run_id: int) -> Optional[str]:
        """Get logs for a specific workflow run."""
        if not self.access_token:
            return None
        
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_base}/repos/{owner}/{repo}/actions/runs/{run_id}/logs",
                    headers=self.headers,
                )
                response.raise_for_status()
                return response.text
        except Exception as e:
            logger.error(f"Failed to get workflow logs: {e}")
            return None


class GitLabService:
    """GitLab API integration."""
    
    def __init__(self, access_token: Optional[str] = None, gitlab_url: str = "https://gitlab.com"):
        self.access_token = access_token
        self.gitlab_url = gitlab_url
        self.api_base = f"{gitlab_url}/api/v4"
        self.headers = {
            "PRIVATE-TOKEN": access_token if access_token else "",
        }
    
    async def get_user_info(self) -> Optional[Dict]:
        """Get authenticated user info."""
        if not self.access_token:
            return None
        
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_base}/user",
                    headers=self.headers,
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to get GitLab user info: {e}")
            return None
    
    async def get_projects(self) -> Optional[List[Dict]]:
        """Get list of user's projects."""
        if not self.access_token:
            return None
        
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_base}/projects",
                    headers=self.headers,
                    params={"per_page": 30},
                )
                response.raise_for_status()
                projects = response.json()
                return [
                    {
                        "id": proj["id"],
                        "name": proj["name"],
                        "path_with_namespace": proj["path_with_namespace"],
                        "url": proj["web_url"],
                        "description": proj["description"],
                    }
                    for proj in projects
                ]
        except Exception as e:
            logger.error(f"Failed to get projects: {e}")
            return None
    
    async def get_pipelines(self, project_id: int, limit: int = 10) -> Optional[List[Dict]]:
        """Get recent CI/CD pipelines."""
        if not self.access_token:
            return None
        
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_base}/projects/{project_id}/pipelines",
                    headers=self.headers,
                    params={"per_page": limit, "order_by": "updated_at", "sort": "desc"},
                )
                response.raise_for_status()
                pipelines = response.json()
                return [
                    {
                        "id": pipe["id"],
                        "status": pipe["status"],
                        "created_at": pipe["created_at"],
                        "updated_at": pipe["updated_at"],
                        "web_url": pipe["web_url"],
                    }
                    for pipe in pipelines
                ]
        except Exception as e:
            logger.error(f"Failed to get pipelines: {e}")
            return None


class APIKeyManager:
    """Manage API keys securely."""
    
    @staticmethod
    def store_api_key(
        db: Session,
        user: User,
        service: str,
        key: str,
    ) -> APIKey:
        """Store encrypted API key."""
        from backend.app.services.security import hash_key
        
        api_key = db.query(APIKey).filter(
            APIKey.user_id == user.id,
            APIKey.service == service,
        ).first()
        
        if api_key:
            api_key.key_hash = hash_key(key)
            api_key.is_active = True
        else:
            api_key = APIKey(
                user_id=user.id,
                service=service,
                key_hash=hash_key(key),
                is_active=True,
            )
            db.add(api_key)
        
        db.commit()
        db.refresh(api_key)
        logger.info(f"✓ Stored {service} API key for user {user.id}")
        
        return api_key
    
    @staticmethod
    def get_api_key(db: Session, user: User, service: str) -> Optional[str]:
        """Retrieve API key (requires decryption from vault)."""
        api_key = db.query(APIKey).filter(
            APIKey.user_id == user.id,
            APIKey.service == service,
            APIKey.is_active == True,
        ).first()
        
        if not api_key:
            return None
        
        # In production, decrypt from secure vault
        # For now, return None (keys are hashed, can't be retrieved)
        logger.warning(f"API keys are hashed and cannot be retrieved from vault")
        return None
    
    @staticmethod
    def has_api_key(db: Session, user: User, service: str) -> bool:
        """Check if user has API key for service."""
        api_key = db.query(APIKey).filter(
            APIKey.user_id == user.id,
            APIKey.service == service,
            APIKey.is_active == True,
        ).first()
        
        return api_key is not None
