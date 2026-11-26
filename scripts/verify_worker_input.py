"""Use byte-safe stdin to verify frozen edition gates; no private credentials used."""
import json
import subprocess
import sys

worker, edition = sys.argv[1:]
def execute(args, payload=None):
    data = None if payload is None else (json.dumps(payload, ensure_ascii=True) + "\n").encode("utf-8")
    result = subprocess.run([worker, *args], input=data, capture_output=True, timeout=25)
    return result.returncode, [json.loads(line) for line in result.stdout.decode("utf-8-sig").splitlines() if line.strip()]
def denied(args, payload=None):
    code, messages = execute(args, payload)
    assert code == 1 and messages and messages[0].get("message") == "internal_only", (args, code, messages)
code, keys = execute(["list-keys"])
assert code == 0
names = [k.get("name") for k in keys[0].get("keys", [])]
if edition == "personal":
    assert "UPEXNOTE_PG_PASSWORD" not in names
    code, settings = execute(["get-settings"])
    assert code == 0 and settings[0].get("storage_mode") == "local" and not settings[0].get("vps_configured")
    for command in ("admin-overview","admin-data-sql","api-admin-challenge","support-admin-list","telemetry-overview","account-elevate","tunnel-keep"):
        denied([command])
    denied(["db-check","--mode","vps"])
    denied(["account-login","--mode","local"], {"admin_secret": "TEST_ONLY"})
    code, lines = execute(["serve"], {"id": "deny", "argv": ["admin-overview"], "stdin": "{}"})
    assert code == 0 and any(json.loads(x.get("line", "{}")).get("message") == "internal_only" for x in lines if x.get("line")), lines
    print("PERSONAL_DENIALS_OK")
else:
    assert "UPEXNOTE_PG_PASSWORD" in names, names
    print("INTERNAL_EDITION_FLAG_OK")
