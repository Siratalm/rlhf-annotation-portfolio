"""
RLHF Dataset Validator
======================
Author: Md Mustakim Ali — AI Data Specialist
Purpose: Validates the RLHF preference dataset and safety feedback samples
         for completeness, consistency, and quality metrics.

Usage:
    python validate_dataset.py
"""

import csv
import os
from collections import Counter

# ─── Config ────────────────────────────────────────────────────────────────────

PREFERENCE_FILE = "data/rlhf_preference_dataset.csv"
SAFETY_FILE = "data/safety_feedback_samples.csv"

SCORE_FIELDS = [
    "if_score_a", "ac_score_a", "hp_score_a", "sf_score_a", "ff_score_a",
    "if_score_b", "ac_score_b", "hp_score_b", "sf_score_b", "ff_score_b",
    "weighted_score_a", "weighted_score_b"
]

REQUIRED_PREFERENCE_FIELDS = [
    "prompt_id", "prompt", "domain", "difficulty",
    "response_a", "response_b", "preferred",
    "confidence", "reasoning"
]

REQUIRED_SAFETY_FIELDS = [
    "sample_id", "prompt_category", "prompt",
    "model_response", "safety_label", "severity", "annotator_note"
]

VALID_PREFERENCES = {"A", "B", "Tie"}
VALID_SAFETY_LABELS = {"SAFE", "PHARM", "HARM", "BIAS", "MISINFO", "OVERREF", "CAVEAT"}
VALID_SEVERITIES = {"Low", "Medium", "High", "Critical"}
VALID_CONFIDENCES = {"Low", "Medium", "High"}

# ─── Helpers ───────────────────────────────────────────────────────────────────

def separator(title=""):
    width = 60
    if title:
        print(f"\n{'─' * 5} {title} {'─' * (width - len(title) - 7)}")
    else:
        print("─" * width)

def check_mark(condition):
    return "✅" if condition else "❌"

def load_csv(filepath):
    if not os.path.exists(filepath):
        print(f"  ❌ File not found: {filepath}")
        return []
    with open(filepath, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)

# ─── Preference Dataset Validation ─────────────────────────────────────────────

def validate_preference_dataset(filepath):
    separator("RLHF PREFERENCE DATASET")
    rows = load_csv(filepath)

    if not rows:
        return

    errors = []
    warnings = []
    score_values = {field: [] for field in SCORE_FIELDS}
    domain_counts = Counter()
    difficulty_counts = Counter()
    preference_counts = Counter()
    confidence_counts = Counter()

    for i, row in enumerate(rows, 1):
        pid = row.get("prompt_id", f"Row {i}")

        # Check required fields
        for field in REQUIRED_PREFERENCE_FIELDS:
            if not row.get(field, "").strip():
                errors.append(f"[{pid}] Missing required field: '{field}'")

        # Check preference value
        pref = row.get("preferred", "").strip().strip('"')
        if pref not in VALID_PREFERENCES:
            errors.append(f"[{pid}] Invalid preferred value: '{pref}' (expected A, B, or Tie)")
        else:
            preference_counts[pref] += 1

        # Check confidence value
        conf = row.get("confidence", "").strip()
        if conf not in VALID_CONFIDENCES:
            warnings.append(f"[{pid}] Unexpected confidence value: '{conf}'")
        else:
            confidence_counts[conf] += 1

        # Check scores are numeric and in range 1-5
        for field in ["if_score_a", "ac_score_a", "hp_score_a", "sf_score_a", "ff_score_a",
                      "if_score_b", "ac_score_b", "hp_score_b", "sf_score_b", "ff_score_b"]:
            val_str = row.get(field, "").strip()
            try:
                val = float(val_str)
                if not (1.0 <= val <= 5.0):
                    errors.append(f"[{pid}] Score out of range (1-5): {field}={val}")
                score_values[field].append(val)
            except ValueError:
                errors.append(f"[{pid}] Non-numeric score: {field}='{val_str}'")

        # Check weighted scores
        for field in ["weighted_score_a", "weighted_score_b"]:
            val_str = row.get(field, "").strip()
            try:
                val = float(val_str)
                if not (1.0 <= val <= 5.0):
                    warnings.append(f"[{pid}] Weighted score out of range: {field}={val}")
                score_values[field].append(val)
            except ValueError:
                warnings.append(f"[{pid}] Non-numeric weighted score: {field}='{val_str}'")

        # Check reasoning is not empty
        reasoning = row.get("reasoning", "").strip()
        if len(reasoning) < 15:
            warnings.append(f"[{pid}] Reasoning is very short (<15 chars): '{reasoning}'")

        # Track distributions
        domain_counts[row.get("domain", "Unknown")] += 1
        difficulty_counts[row.get("difficulty", "Unknown")] += 1

    # ── Print Results ──
    print(f"\n  Total rows: {len(rows)}")
    print(f"  {check_mark(not errors)} Errors: {len(errors)}")
    print(f"  {check_mark(not warnings)} Warnings: {len(warnings)}")

    if errors:
        print("\n  ERRORS:")
        for e in errors:
            print(f"    ❌ {e}")

    if warnings:
        print("\n  WARNINGS:")
        for w in warnings:
            print(f"    ⚠️  {w}")

    separator("Preference Distribution")
    total = sum(preference_counts.values())
    for pref, count in sorted(preference_counts.items()):
        pct = (count / total * 100) if total else 0
        bar = "█" * int(pct / 5)
        print(f"  {pref:5s}: {count:3d} ({pct:5.1f}%) {bar}")

    separator("Confidence Distribution")
    for conf, count in sorted(confidence_counts.items()):
        print(f"  {conf:7s}: {count}")

    separator("Domain Coverage")
    for domain, count in sorted(domain_counts.items(), key=lambda x: -x[1]):
        print(f"  {domain:30s}: {count}")

    separator("Difficulty Distribution")
    for diff, count in sorted(difficulty_counts.items()):
        print(f"  {diff:8s}: {count}")

    separator("Average Scores (A vs B)")
    dim_labels = {"if": "Instruction Following", "ac": "Accuracy", "hp": "Helpfulness",
                  "sf": "Safety", "ff": "Fluency & Format"}
    for dim, label in dim_labels.items():
        vals_a = score_values.get(f"{dim}_score_a", [])
        vals_b = score_values.get(f"{dim}_score_b", [])
        avg_a = sum(vals_a) / len(vals_a) if vals_a else 0
        avg_b = sum(vals_b) / len(vals_b) if vals_b else 0
        print(f"  {label:25s}  A: {avg_a:.2f}  B: {avg_b:.2f}")

    ws_a = score_values.get("weighted_score_a", [])
    ws_b = score_values.get("weighted_score_b", [])
    avg_ws_a = sum(ws_a) / len(ws_a) if ws_a else 0
    avg_ws_b = sum(ws_b) / len(ws_b) if ws_b else 0
    print(f"\n  {'Weighted Score (avg)':25s}  A: {avg_ws_a:.2f}  B: {avg_ws_b:.2f}")

    return len(errors) == 0

# ─── Safety Dataset Validation ──────────────────────────────────────────────────

def validate_safety_dataset(filepath):
    separator("SAFETY FEEDBACK DATASET")
    rows = load_csv(filepath)

    if not rows:
        return

    errors = []
    warnings = []
    label_counts = Counter()
    severity_counts = Counter()

    for i, row in enumerate(rows, 1):
        sid = row.get("sample_id", f"Row {i}")

        # Check required fields
        for field in REQUIRED_SAFETY_FIELDS:
            if not row.get(field, "").strip():
                errors.append(f"[{sid}] Missing required field: '{field}'")

        # Check safety label
        label = row.get("safety_label", "").strip()
        if label not in VALID_SAFETY_LABELS:
            errors.append(f"[{sid}] Invalid safety_label: '{label}'")
        else:
            label_counts[label] += 1

        # Check severity
        severity = row.get("severity", "").strip()
        if severity not in VALID_SEVERITIES:
            errors.append(f"[{sid}] Invalid severity: '{severity}'")
        else:
            severity_counts[severity] += 1

        # Check corrective_action for HARM labels
        if label in {"HARM", "BIAS", "MISINFO"} and not row.get("corrective_action", "").strip():
            warnings.append(f"[{sid}] HARM/BIAS/MISINFO label has no corrective_action")

        # Annotator note length
        note = row.get("annotator_note", "").strip()
        if len(note) < 20:
            warnings.append(f"[{sid}] Annotator note very short: '{note}'")

    # ── Print Results ──
    print(f"\n  Total rows: {len(rows)}")
    print(f"  {check_mark(not errors)} Errors: {len(errors)}")
    print(f"  {check_mark(not warnings)} Warnings: {len(warnings)}")

    if errors:
        print("\n  ERRORS:")
        for e in errors:
            print(f"    ❌ {e}")

    if warnings:
        print("\n  WARNINGS:")
        for w in warnings:
            print(f"    ⚠️  {w}")

    separator("Safety Label Distribution")
    label_descriptions = {
        "SAFE": "Safe — no concerns",
        "CAVEAT": "Needs disclaimer",
        "OVERREF": "Over-refusal",
        "PHARM": "Potential harm",
        "BIAS": "Bias detected",
        "MISINFO": "Misinformation",
        "HARM": "Clear violation"
    }
    total = sum(label_counts.values())
    for label in ["SAFE", "CAVEAT", "OVERREF", "PHARM", "BIAS", "MISINFO", "HARM"]:
        count = label_counts.get(label, 0)
        pct = (count / total * 100) if total else 0
        desc = label_descriptions.get(label, "")
        print(f"  {label:8s}: {count:3d} ({pct:5.1f}%) — {desc}")

    separator("Severity Distribution")
    for sev in ["Low", "Medium", "High", "Critical"]:
        count = severity_counts.get(sev, 0)
        print(f"  {sev:10s}: {count}")

    return len(errors) == 0

# ─── Summary ────────────────────────────────────────────────────────────────────

def print_summary(pref_ok, safety_ok):
    separator("OVERALL SUMMARY")
    print(f"\n  {check_mark(pref_ok)} RLHF Preference Dataset")
    print(f"  {check_mark(safety_ok)} Safety Feedback Dataset")

    if pref_ok and safety_ok:
        print("\n  ✅ All datasets passed validation. Ready to share.")
    else:
        print("\n  ❌ Issues found. Review errors above before sharing.")
    separator()

# ─── Main ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  RLHF ANNOTATION PORTFOLIO — DATASET VALIDATOR")
    print("  Author: Md Mustakim Ali | AI Data Specialist")
    print("=" * 60)

    pref_ok = validate_preference_dataset(PREFERENCE_FILE)
    safety_ok = validate_safety_dataset(SAFETY_FILE)
    print_summary(pref_ok, safety_ok)
