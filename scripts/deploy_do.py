"""Deploy Sah.Bukti app + frontend to DigitalOcean."""
from __future__ import annotations

import io
import re
import sys
import tarfile
from pathlib import Path

import paramiko

HOST = "68.183.181.237"
USER = "root"
REMOTE = "/root/sahbukti"
REPO = Path(r"D:\kedai-ops")
SECRETS = Path(r"D:\MyVault\SECRETS.md")
SKIP_DIRS = {".git", "node_modules", ".venv", "__pycache__", "client/node_modules", "client/dist"}
SKIP_FILES = {".env", ".env.local", "start.sh"}


def load_password() -> str:
    text = SECRETS.read_text(encoding="utf-8")
    match = re.search(r"^-\s*Password:\s*(.+)$", text, re.MULTILINE)
    if not match:
        raise SystemExit("DigitalOcean password not found in vault secrets file")
    return match.group(1).strip()


def run(ssh: paramiko.SSHClient, cmd: str) -> str:
    print(f"$ {cmd}")
    _, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    if out.strip():
        print(out.rstrip().encode("ascii", errors="replace").decode("ascii"))
    if err.strip():
        print(err.rstrip().encode("ascii", errors="replace").decode("ascii"), file=sys.stderr)
    if exit_code != 0:
        raise SystemExit(f"Command failed ({exit_code})")
    return out


def build_tarball() -> io.BytesIO:
    buffer = io.BytesIO()
    include_roots = ["app", "frontend", "migrations", "requirements.txt", "LICENSE", "README.md"]
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for name in include_roots:
            path = REPO / name
            if path.is_file():
                tar.add(path, arcname=name)
                continue
            if not path.is_dir():
                continue
            for file_path in path.rglob("*"):
                rel = file_path.relative_to(REPO)
                if set(rel.parts) & SKIP_DIRS:
                    continue
                if any(part in SKIP_DIRS for part in rel.parts):
                    continue
                if file_path.name in SKIP_FILES:
                    continue
                if file_path.is_dir():
                    continue
                tar.add(file_path, arcname=str(rel).replace("\\", "/"))
    buffer.seek(0)
    return buffer


def patch_app_base_url(ssh: paramiko.SSHClient) -> None:
    script = r"""
from pathlib import Path
path = Path("/root/sahbukti/start.sh")
text = path.read_text(encoding="utf-8")
old = "export SAHBUKTI_APP_BASE_URL='http://arifaqyl.me'"
new = "export SAHBUKTI_APP_BASE_URL='https://arifaqyl.me/sahbukti'"
if new in text:
    print("start.sh base url already set")
elif old in text:
    text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")
    print("start.sh base url updated")
else:
    print("start.sh base url left unchanged")
"""
    run(ssh, f"python3 - <<'PY'\n{script}\nPY")


def main() -> None:
    password = load_password()
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=password, timeout=45)

    run(ssh, f"mkdir -p {REMOTE}")
    tarball = build_tarball()
    sftp = ssh.open_sftp()
    sftp.putfo(tarball, f"{REMOTE}/deploy.tar.gz")
    sftp.close()

    run(ssh, f"cd {REMOTE} && tar xzf deploy.tar.gz && rm deploy.tar.gz")
    patch_app_base_url(ssh)
    run(ssh, "pm2 restart sahbukti")
    run(ssh, "curl -sf http://127.0.0.1/sahbukti/ | grep -o '/sahbukti/assets/' | head -n 1")
    run(ssh, "curl -sfI http://127.0.0.1/sahbukti/assets/index-BW0-CNFN.js | head -n 1")
    ssh.close()
    print("Sah.Bukti deploy complete.")


if __name__ == "__main__":
    main()
