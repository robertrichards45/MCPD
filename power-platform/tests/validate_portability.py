"""Guardrails for a portable, pre-tenant MCPD Sentinel handoff."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
manifest = (ROOT / "solution-manifest.yaml").read_text(encoding="utf-8")
registry = (ROOT / "module-registry.yaml").read_text(encoding="utf-8")
prototype = ROOT / "prototype"

required = [
    "mcpd_GenAIEnabled", "mcpd_GenAIBaseUrl", "mcpd_GenAIModel",
    "mcpd_SharePointDocumentSiteUrl", "mcpd_EnableFTO",
]
missing = [name for name in required if name not in manifest]
if missing:
    print("FAIL: manifest missing environment variables: " + ", ".join(missing))
    sys.exit(1)

if "managed_for_production: true" not in manifest:
    print("FAIL: managed production setting is not enabled")
    sys.exit(1)

module_names = re.findall(r"^\s*-\s+key:\s*([A-Za-z0-9_-]+)", registry, re.MULTILINE)
preview_data = (prototype / "preview-data.js").read_text(encoding="utf-8")
missing_modules = [name for name in module_names if name not in preview_data]
if missing_modules:
    print("FAIL: preview is missing registered modules: " + ", ".join(missing_modules))
    sys.exit(1)

scan_roots = [ROOT / "app", ROOT / "flows", ROOT / "deployment", ROOT / "design"]
forbidden = re.compile(r"(?:password|client_secret|tenant[_-]?id|access[_-]?token)\s*[:=]\s*['\"]?[^\s,'\"]+", re.I)
hits = []
for folder in scan_roots:
    for path in folder.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".yaml", ".yml", ".json", ".md", ".fx", ".txt"}:
            for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                if forbidden.search(line) and "example" not in line.lower() and "placeholder" not in line.lower():
                    hits.append(f"{path.relative_to(ROOT)}:{line_no}")
if hits:
    print("FAIL: possible hard-coded secret/tenant value: " + ", ".join(hits))
    sys.exit(1)

print(f"PASS: portability checks passed ({len(module_names)} registered modules, environment-based configuration, no secret patterns).")
