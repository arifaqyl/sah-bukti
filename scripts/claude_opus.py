import ssl
import argparse
import json
import os
import sys
from pathlib import Path
from urllib import request


def get_env(name: str) -> str:
    value = os.environ.get(name)
    if value:
        return value
    return os.popen(
        f'powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable(\'{name}\', \'User\')"'
    ).read().strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt-file", required=True)
    parser.add_argument("--model", default="claude-opus-4.6")
    parser.add_argument("--output-file", default="")
    args = parser.parse_args()

    base_url = get_env("KRACKED_CLAUDE_BASE_URL")
    api_key = get_env("KRACKED_CLAUDE_API_KEY")

    if not base_url:
        raise SystemExit("KRACKED_CLAUDE_BASE_URL is not set.")
    if not api_key:
        raise SystemExit("KRACKED_CLAUDE_API_KEY is not set.")

    prompt_path = Path(args.prompt_file)
    if not prompt_path.exists():
        raise SystemExit(f"Prompt file not found: {prompt_path}")

    payload = {
        "model": args.model or "claude-opus-4.6",
        "messages": [{"role": "user", "content": prompt_path.read_text(encoding="utf-8")}],
    }

    req = request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    ssl_context = ssl._create_unverified_context()

    with request.urlopen(req, timeout=180, context=ssl_context) as response:
        body = json.loads(response.read().decode("utf-8"))

    text = body["choices"][0]["message"]["content"]

    if args.output_file:
        Path(args.output_file).write_text(text, encoding="utf-8")

    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
