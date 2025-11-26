"""
Cliente determinístico para a API do GitHub.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional

import requests


class GitHubError(RuntimeError):
    """Erro de alto nível retornado pela API do GitHub."""

    def __init__(self, status_code: int, message: str):
        super().__init__(f"GitHub error {status_code}: {message}")
        self.status_code = status_code
        self.message = message


@dataclass()
class GitHubConfig:
    owner: str
    repo: str
    token: str
    api_url: str = "https://api.github.com"


class GitHubClient:
    """
    Envelope determinístico sobre a API REST do GitHub.
    Operações suportadas:
      - criação de branches
      - criação de arquivos ou commits via Contents API
      - criação de pull requests
      - comentários em PR
    """

    def __init__(self, cfg: GitHubConfig):
        if not cfg.token:
            raise ValueError("GITHUB_TOKEN ausente para GitHubClient.")
        self.cfg = cfg
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"token {cfg.token}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "Metanucleus-Evolution/1.0",
            }
        )

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    @property
    def base(self) -> str:
        return f"{self.cfg.api_url}/repos/{self.cfg.owner}/{self.cfg.repo}"

    def _url(self, path: str) -> str:
        return f"{self.base}{path}"

    def _request(self, method: str, url: str, *, expected_status: Iterable[int] = (200,), **kwargs) -> Dict[str, Any]:
        kwargs.setdefault('timeout', 30)  # 30 second timeout
        resp = self.session.request(method, url, **kwargs)
        if expected_status and resp.status_code not in expected_status:
            raise GitHubError(resp.status_code, resp.text)
        if resp.status_code == 204 or not resp.content:
            return {}
        return resp.json()

    # ------------------------------------------------------------------
    # Branches
    # ------------------------------------------------------------------

    def branch_exists(self, branch: str) -> bool:
        url = self._url(f"/git/ref/heads/{branch}")
        resp = self.session.get(url)
        if resp.status_code == 200:
            return True
        if resp.status_code == 404:
            return False
        raise GitHubError(resp.status_code, resp.text)

    def create_branch(self, new_branch: str, from_branch: str = "main") -> Dict[str, Any]:
        if self.branch_exists(new_branch):
            return {"ref": f"refs/heads/{new_branch}"}
        base_ref = self._request("GET", self._url(f"/git/ref/heads/{from_branch}"))
        sha = base_ref["object"]["sha"]
        payload = {"ref": f"refs/heads/{new_branch}", "sha": sha}
        return self._request("POST", self._url("/git/refs"), json=payload, expected_status=(201,))

    # ------------------------------------------------------------------
    # Files (Contents API)
    # ------------------------------------------------------------------

    def get_file_metadata(self, path: str, branch: str) -> Optional[Dict[str, Any]]:
        url = self._url(f"/contents/{path}")
        resp = self.session.get(url, params={"ref": branch})
        if resp.status_code == 404:
            return None
        if resp.status_code >= 400:
            raise GitHubError(resp.status_code, resp.text)
        return resp.json()

    def create_or_update_file(self, *, path: str, content: str, message: str, branch: str) -> Dict[str, Any]:
        metadata = self.get_file_metadata(path, branch)
        sha = metadata["sha"] if metadata else None
        payload = {
            "message": message,
            "content": base64.b64encode(content.encode("utf-8")).decode("utf-8"),
            "branch": branch,
        }
        if sha:
            payload["sha"] = sha
        return self._request("PUT", self._url(f"/contents/{path}"), json=payload, expected_status=(200, 201))

    def delete_file(self, *, path: str, message: str, branch: str) -> Dict[str, Any]:
        metadata = self.get_file_metadata(path, branch)
        if not metadata:
            return {}
        payload = {"message": message, "sha": metadata["sha"], "branch": branch}
        return self._request("DELETE", self._url(f"/contents/{path}"), json=payload, expected_status=(200, 204))

    # ------------------------------------------------------------------
    # Pull requests e comentários
    # ------------------------------------------------------------------

    def create_pull_request(
        self,
        *,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str = "main",
        draft: bool = False,
    ) -> Dict[str, Any]:
        payload = {
            "title": title,
            "body": body,
            "head": head_branch,
            "base": base_branch,
            "draft": draft,
        }
        return self._request("POST", self._url("/pulls"), json=payload, expected_status=(201,))

    def comment_on_pr(self, *, pr_number: int, body: str) -> Dict[str, Any]:
        payload = {"body": body}
        return self._request(
            "POST",
            self._url(f"/issues/{pr_number}/comments"),
            json=payload,
            expected_status=(201,),
        )


__all__ = [
    "GitHubClient",
    "GitHubConfig",
    "GitHubError",
]
