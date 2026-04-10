"""12-category taxonomy (ids match frontend src/lib/categories.js)."""
import os

CATEGORY_IDS = [
    "food_dining",
    "transport",
    "shopping",
    "housing",
    "health_medical",
    "entertainment",
    "travel",
    "education",
    "finance",
    "subscriptions",
    "family_personal",
    "uncategorised",
]

IDX_TO_ID = {i: c for i, c in enumerate(CATEGORY_IDS)}
ID_TO_IDX = {c: i for i, c in enumerate(CATEGORY_IDS)}

# Spec §3.2.3 defaults:
# - review when top confidence < 0.65
# - uncategorised when very low (< 0.50)
# These are env-tunable for statement/OCR heavy workloads.
REVIEW_THRESHOLD = float(os.environ.get("REVIEW_THRESHOLD", "0.65"))
UNCATEGORISED_THRESHOLD = float(os.environ.get("UNCATEGORISED_THRESHOLD", "0.20"))
