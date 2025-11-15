#!/usr/bin/env python3
import json
import os
import sys
from jsonschema import validate, ValidationError, Draft7Validator

# Path to schema (adjust if your structure differs)
SCHEMA_PATH = os.path.expanduser("~/NDRP/schema/entry_schema.json")

# ---------------------------------------------------------
# Load schema
# ---------------------------------------------------------
def load_schema(path=SCHEMA_PATH):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERROR] Unable to load schema at {path}: {e}")
        sys.exit(1)

# ---------------------------------------------------------
# Validate a single entry
# ---------------------------------------------------------
def validate_entry(entry, schema):
    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(entry), key=lambda e: e.path)

    if errors:
        return False, format_errors(errors)
    return True, None

# ---------------------------------------------------------
# Format errors in clear human-readable text
# ---------------------------------------------------------
def format_errors(errors):
    formatted = []
    for err in errors:
        loc = ".".join([str(x) for x in err.path]) or "root"
        formatted.append(f"- At `{loc}`: {err.message}")
    return "\n".join(formatted)

# ---------------------------------------------------------
# Validate an entire JSONL dataset
# ---------------------------------------------------------
def validate_jsonl(jsonl_path):
    schema = load_schema()
    results = {
        "valid": 0,
        "invalid": 0,
        "errors": []
    }

    try:
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue

                try:
                    entry = json.loads(line)
                except json.JSONDecodeError as e:
                    results["invalid"] += 1
                    results["errors"].append({
                        "line": i,
                        "error": f"Malformed JSON: {e}"
                    })
                    continue

                ok, err = validate_entry(entry, schema)
                if ok:
                    results["valid"] += 1
                else:
                    results["invalid"] += 1
                    results["errors"].append({
                        "line": i,
                        "error": err
                    })

        return results

    except FileNotFoundError:
        print(f"[ERROR] File not found: {jsonl_path}")
        sys.exit(1)

# ---------------------------------------------------------
# CLI usage
# ---------------------------------------------------------
def main():
    if len(sys.argv) != 2:
        print("Usage: python validate.py <dataset.jsonl>")
        sys.exit(1)

    jsonl_file = sys.argv[1]

    print(f"🔍 Validating dataset: {jsonl_file}\n")
    results = validate_jsonl(jsonl_file)

    print(f"Valid entries:   {results['valid']}")
    print(f"Invalid entries: {results['invalid']}")

    if results["errors"]:
        print("\n⚠️  Errors:")
        for err in results["errors"]:
            print(f"\nLine {err['line']}:")
            print(err["error"])
    else:
        print("\n✨ No validation errors. Dataset conforms to NDRP-1.0.")

if __name__ == "__main__":
    main()
