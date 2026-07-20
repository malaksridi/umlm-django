"""
Intégration avec l'API GitHub — section 4.3 "Détection automatique" du cahier des charges.

Utilise l'API REST publique de GitHub (pas besoin de cloner les repos)
pour récupérer le dernier commit d'une branche donnée.

Doc officielle : https://docs.github.com/en/rest/commits/commits
"""
import re
import requests
from django.conf import settings

GITHUB_API_BASE = "https://api.github.com"


def extract_owner_repo(github_url: str) -> tuple[str, str]:
    """
    Extrait 'owner' et 'repo' depuis une URL GitHub classique.
    Ex: https://github.com/nachd-it/module-rh -> ("nachd-it", "module-rh")
    """
    match = re.search(r"github\.com/([^/]+)/([^/.]+)", github_url)
    if not match:
        raise ValueError(f"URL GitHub invalide : {github_url}")
    return match.group(1), match.group(2)


def get_latest_commit(github_url: str, branch: str = "main") -> str | None:
    """
    Retourne le SHA du dernier commit d'une branche sur GitHub.
    Retourne None si le repo/la branche est introuvable (ex: module absent).
    """
    owner, repo = extract_owner_repo(github_url)
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/commits/{branch}"

    headers = {"Accept": "application/vnd.github+json"}
    token = getattr(settings, "GITHUB_API_TOKEN", None)
    if token:
        headers["Authorization"] = f"Bearer {token}"

    response = requests.get(url, headers=headers, timeout=10)

    if response.status_code == 404:
        return None  # module absent / branche inexistante -> "Non intégré"

    response.raise_for_status()
    return response.json()["sha"]


def get_local_commit(local_path: str, branch: str = "main") -> str | None:
    """
    Récupère le commit HEAD local d'un projet cloné sur le serveur.
    Suppose que 'local_path' est un dépôt git valide.
    """
    import subprocess

    try:
        result = subprocess.run(
            ["git", "-C", local_path, "rev-parse", branch],
            capture_output=True, text=True, timeout=10, check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
