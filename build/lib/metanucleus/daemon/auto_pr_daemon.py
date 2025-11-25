from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Optional

import requests  # type: ignore

from metanucleus.core.meta_kernel import MetaKernel

REPO_ROOT = Path(__file__).resolve().parents[2]
STATE_FILE = REPO_ROOT / ".metanucleus_daemon_state.json"


@dataclass
class DaemonState:
    last_processed_sha: Optional[str] = None

    @classmethod
    def load(cls) -> "DaemonState":
        if not STATE_FILE.exists():
            return cls()
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            return cls(**data)
        except Exception:
            return cls()

    def save(self) -> None:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")


def run_cmd(cmd: List[str], *, check: bool = True) -> subprocess.CompletedProcess:
    proc = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    if check and proc.returncode != 0:
        raise RuntimeError(
            f"Comando falhou: {' '.join(cmd)}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    return proc


def git_pull() -> None:
    run_cmd(["git", "fetch", "origin"])
    run_cmd(["git", "checkout", "main"])
    run_cmd(["git", "reset", "--hard", "origin/main"])


def get_current_sha() -> str:
    proc = run_cmd(["git", "rev-parse", "HEAD"])
    return proc.stdout.strip()


def run_tests() -> bool:
    proc = run_cmd([sys.executable, "-m", "pytest"], check=False)
    print("[metanucleus-daemon] pytest returncode =", proc.returncode)
    return proc.returncode == 0


def git_has_changes() -> bool:
    proc = run_cmd(["git", "status", "--porcelain"], check=False)
    return bool(proc.stdout.strip())


def git_commit_all(message: str) -> None:
    run_cmd(["git", "add", "-A"])
    run_cmd(["git", "commit", "-m", message])


def git_push(branch: str) -> None:
    run_cmd(["git", "push", "origin", branch])


def create_branch_name(base_sha: str) -> str:
    return f"auto-evolve/{base_sha[:7]}-{int(time.time())}"


def create_github_pr(branch: str, base: str = "main") -> None:
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not token or not repo:
        print("[metanucleus-daemon] GITHUB_TOKEN ou GITHUB_REPOSITORY não definidos; PR ignorado.")
        return

    url = f"https://api.github.com/repos/{repo}/pulls"
    title = f"auto-evolve: patches do Metanúcleo ({branch})"
    body = (
        "Este PR foi gerado automaticamente pelo Metanúcleo.\n\n"
        f"- branch: `{branch}`\n"
        f"- base: `{base}`\n"
        "- modo: daemon 24/7\n"
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    payload = {"title": title, "head": branch, "base": base, "body": body}

    response = requests.post(url, json=payload, headers=headers, timeout=30)
    if response.status_code >= 300:
        print(
            f"[metanucleus-daemon] falha ao criar PR: {response.status_code}\n{response.text}"
        )
    else:
        print("[metanucleus-daemon] PR criado:", response.json().get("html_url"))


def run_auto_evolution_once(source: str = "daemon") -> bool:
    print("[metanucleus-daemon] rodando testes iniciais...")
    if not run_tests():
        print("[metanucleus-daemon] testes falharam; ciclo abortado.")
        return False

    kernel = MetaKernel()
    print("[metanucleus-daemon] executando run_auto_evolution_cycle...")
    patches = kernel.run_auto_evolution_cycle(
        domains=["all"],
        max_patches=None,
        apply_changes=True,
        source=source,
    )

    if not patches:
        print("[metanucleus-daemon] nenhum patch sugerido.")
        return False

    print(f"[metanucleus-daemon] patches aplicados: {len(patches)}")

    print("[metanucleus-daemon] rodando testes após aplicar patches...")
    if not run_tests():
        print(
            "[metanucleus-daemon] testes falharam após os patches; revise manualmente o working tree."
        )
        return False

    if not git_has_changes():
        print("[metanucleus-daemon] sem mudanças detectadas no git.")
        return False

    base_sha = get_current_sha()
    branch = create_branch_name(base_sha)
    print("[metanucleus-daemon] criando branch:", branch)

    run_cmd(["git", "checkout", "-b", branch])
    git_commit_all("auto-evolve: patches sugeridos pelo Metanúcleo")
    git_push(branch)
    create_github_pr(branch=branch, base="main")

    git_pull()
    return True


def main() -> int:
    interval_seconds = int(os.environ.get("METANUCLEUS_DAEMON_INTERVAL", "600"))
    state = DaemonState.load()

    print("[metanucleus-daemon] iniciado")
    print("  REPO_ROOT:", REPO_ROOT)
    print("  interval_seconds:", interval_seconds)
    print()

    while True:
        try:
            git_pull()
            current_sha = get_current_sha()

            if state.last_processed_sha == current_sha:
                print("[metanucleus-daemon] nenhum commit novo; aguardando...")
            else:
                print("[metanucleus-daemon] novo commit detectado:", current_sha)
                pr_created = run_auto_evolution_once(source="daemon")
                state.last_processed_sha = current_sha
                state.save()
                if pr_created:
                    print("[metanucleus-daemon] PR criado neste ciclo.")
        except Exception as exc:
            print("[metanucleus-daemon] erro durante o ciclo:", repr(exc))

        print(f"[metanucleus-daemon] dormindo {interval_seconds} segundos...\n")
        time.sleep(interval_seconds)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
