"""Run this script to see Pydantic validate an AppScout record.

All values below are explicitly placeholders. They are not app research.
Run from the project root with: python -m examples.validate_app_record
"""

from datetime import date
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from appscout.models import AppResearchRecord


placeholder_record = AppResearchRecord(
    app_name="Example app (placeholder)",
    category="Example category (placeholder)",
    description="Placeholder record used only to demonstrate validation.",
    auth_methods=["placeholder"],
    access_model="unknown",
    api_type="unknown",
    api_breadth="unknown",
    mcp_status="unknown",
    buildability="unclear",
    blockers=["Placeholder only; replace with researched information."],
    evidence=[],
    confidence="low",
    last_checked=date.today(),
)

print("Record validated successfully:")
print(placeholder_record.model_dump_json(indent=2))
