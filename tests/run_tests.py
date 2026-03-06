#!/usr/bin/env python3
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen


REPO_ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = REPO_ROOT / "artifacts"


def run(cmd: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=str(cwd or REPO_ROOT),
        env=os.environ.copy(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def fail(message: str, *, output: str | None = None, code: int = 1) -> None:
    print(f"FAIL: {message}")
    if output:
        print(output.rstrip())
    raise SystemExit(code)


def require_file(path: Path, description: str) -> None:
    if not path.exists():
        fail(f"Missing {description}: {path}")


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"Invalid JSON: {path}", output=str(exc))
    return {}


def demo_mode() -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    report_path = ARTIFACTS_DIR / "databricks_guardrails.json"
    guard = run([sys.executable, "tools/databricks_guardrails.py", "--format", "json", "--out", str(report_path)])
    if guard.returncode != 0:
        fail("Databricks guardrails failed (demo mode must be offline).", output=guard.stdout)

    report = load_json(report_path)
    if report.get("summary", {}).get("errors", 0) != 0:
        fail("Databricks guardrails reported errors.", output=json.dumps(report.get("findings", []), indent=2))

    demo = run([sys.executable, "pipelines/pipeline_demo.py"])
    if demo.returncode != 0:
        fail("Offline demo pipeline failed.", output=demo.stdout)

    out_path = REPO_ROOT / "data" / "processed" / "events_jsonl" / "events.jsonl"
    require_file(out_path, "offline demo output")
    if out_path.stat().st_size == 0:
        fail("Offline demo output is empty.", output=str(out_path))

    for required in ["NOTICE.md", "COMMERCIAL_LICENSE.md", "GOVERNANCE.md"]:
        require_file(REPO_ROOT / required, required)

    license_text = (REPO_ROOT / "LICENSE").read_text(encoding="utf-8", errors="replace")
    if "it.freddy.alvarez@gmail.com" not in license_text:
        fail("LICENSE must include the commercial licensing contact email.")

    print("OK: demo-mode tests passed (offline).")


def _dbx_get(host: str, token: str, path: str, *, timeout_s: int = 8) -> tuple[int, str]:
    base = host.rstrip("/") + "/"
    url = urljoin(base, path.lstrip("/"))
    req = Request(url, method="GET", headers={"Authorization": f"Bearer {token}"})
    with urlopen(req, timeout=timeout_s) as resp:
        status = resp.status
        body = resp.read().decode("utf-8", errors="replace")
    return status, body


def production_mode() -> None:
    if os.environ.get("PRODUCTION_TESTS_CONFIRM") != "1":
        fail(
            "Production-mode tests require an explicit opt-in.",
            output=(
                "Set `PRODUCTION_TESTS_CONFIRM=1` and rerun:\n"
                "  TEST_MODE=production PRODUCTION_TESTS_CONFIRM=1 python3 tests/run_tests.py\n"
            ),
            code=2,
        )

    ran_external_integration = False

    host = os.environ.get("DATABRICKS_HOST", "").strip()
    token = os.environ.get("DATABRICKS_TOKEN", "").strip()
    if host or token:
        missing = [k for k, v in {"DATABRICKS_HOST": host, "DATABRICKS_TOKEN": token}.items() if not v]
        if missing:
            fail(
                "Databricks production checks are partially configured.",
                output=(
                    "Set all required values and rerun:\n"
                    "  export DATABRICKS_HOST='https://<workspace-host>'\n"
                    "  export DATABRICKS_TOKEN='<personal-access-token>'\n"
                    "  TEST_MODE=production PRODUCTION_TESTS_CONFIRM=1 python3 tests/run_tests.py\n"
                ),
                code=2,
            )

        try:
            status, _ = _dbx_get(host, token, "/api/2.0/clusters/list")
            if status != 200:
                raise RuntimeError(f"unexpected status: {status}")
        except Exception as exc:
            fail(
                "Databricks REST API check failed.",
                output=(
                    "Verify DATABRICKS_HOST is correct and DATABRICKS_TOKEN is valid.\n\n"
                    f"{type(exc).__name__}: {exc}\n"
                ),
            )

        ran_external_integration = True

    if os.environ.get("TERRAFORM_VALIDATE") == "1":
        tf = shutil.which("terraform")
        if tf is None:
            fail(
                "TERRAFORM_VALIDATE=1 requires terraform.",
                output="Install Terraform and rerun production mode, or unset TERRAFORM_VALIDATE.",
                code=2,
            )
        ran_external_integration = True
        example_dir = REPO_ROOT / "infra" / "examples" / "dev"
        init = run([tf, "init", "-backend=false"], cwd=example_dir)
        if init.returncode != 0:
            fail("terraform init failed.", output=init.stdout, code=2)
        validate = run([tf, "validate"], cwd=example_dir)
        if validate.returncode != 0:
            fail("terraform validate failed.", output=validate.stdout)

    if not ran_external_integration:
        fail(
            "No external integration checks were executed in production mode.",
            output=(
                "Enable at least one real integration:\n"
                "- Set `DATABRICKS_HOST` and `DATABRICKS_TOKEN` to run a Databricks REST API check, and/or\n"
                "- Set `TERRAFORM_VALIDATE=1` to run Terraform validate.\n\n"
                "Then rerun:\n"
                "  TEST_MODE=production PRODUCTION_TESTS_CONFIRM=1 python3 tests/run_tests.py\n"
            ),
            code=2,
        )

    print("OK: production-mode tests passed (integrations executed).")


def main() -> None:
    mode = os.environ.get("TEST_MODE", "demo").strip().lower()
    if mode not in {"demo", "production"}:
        fail("Invalid TEST_MODE. Expected 'demo' or 'production'.", code=2)

    if mode == "demo":
        demo_mode()
        return

    production_mode()


if __name__ == "__main__":
    main()
