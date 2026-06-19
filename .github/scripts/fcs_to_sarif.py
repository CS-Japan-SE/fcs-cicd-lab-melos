#!/usr/bin/env python3
"""Convert FCS scan JSON results to SARIF 2.1.0 format for GitHub Code Scanning."""
import json
import sys
import os
import glob

SEVERITY_MAP = {
    "critical": "error",
    "high": "error",
    "medium": "warning",
    "low": "note",
    "informational": "note",
}


def iac_to_sarif(data, repo_root=""):
    rules = {}
    results = []

    for detection in data.get("rule_detections", []):
        rule_id = detection["rule_uuid"]
        severity = detection.get("severity", "medium").lower()

        if rule_id not in rules:
            rules[rule_id] = {
                "id": rule_id,
                "name": detection["rule_name"].replace(" ", ""),
                "shortDescription": {"text": detection["rule_name"]},
                "fullDescription": {"text": detection.get("description", detection["rule_name"])},
                "defaultConfiguration": {"level": SEVERITY_MAP.get(severity, "warning")},
                "properties": {"tags": [detection.get("rule_category", "")], "precision": "high"},
            }

        for d in detection.get("detections", []):
            results.append({
                "ruleId": rule_id,
                "level": SEVERITY_MAP.get(severity, "warning"),
                "message": {"text": d.get("reason", detection["rule_name"])},
                "locations": [{
                    "physicalLocation": {
                        "artifactLocation": {"uri": d["file"], "uriBaseId": "%SRCROOT%"},
                        "region": {"startLine": max(1, d.get("line", 1))},
                    }
                }],
            })

    return {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {
                "driver": {
                    "name": "CrowdStrike FCS IaC",
                    "version": data.get("fcs_version", ""),
                    "rules": list(rules.values()),
                }
            },
            "results": results,
        }],
    }


def image_to_sarif(data):
    rules = {}
    results = []

    image_uri = "{}/{}:{}".format(
        data.get("ImageInfo", {}).get("Registry", ""),
        data.get("ImageInfo", {}).get("Repository", ""),
        data.get("ImageInfo", {}).get("Tag", ""),
    ).lstrip("/")

    for vuln in data.get("Vulnerabilities", []):
        v = vuln.get("Vulnerability", {})
        cve_id = v.get("ID", "UNKNOWN")
        severity = v.get("Severity", "medium").lower()

        if cve_id not in rules:
            rules[cve_id] = {
                "id": cve_id,
                "name": cve_id.replace("-", ""),
                "shortDescription": {"text": cve_id},
                "fullDescription": {"text": v.get("Description", cve_id)},
                "defaultConfiguration": {"level": SEVERITY_MAP.get(severity, "warning")},
                "helpUri": v.get("References", [None])[0] or "",
                "properties": {"precision": "high"},
            }

        pkg = vuln.get("Platform", {})
        pkg_name = pkg.get("Name", "unknown") if isinstance(pkg, dict) else str(pkg)

        results.append({
            "ruleId": cve_id,
            "level": SEVERITY_MAP.get(severity, "warning"),
            "message": {"text": "{} affects {} {}. Fix: {}".format(
                cve_id, pkg_name,
                pkg.get("Version", "") if isinstance(pkg, dict) else "",
                v.get("FixedIn", "no fix available"),
            )},
            "locations": [{
                "physicalLocation": {
                    "artifactLocation": {"uri": image_uri, "uriBaseId": "%SRCROOT%"},
                    "region": {"startLine": 1},
                }
            }],
        })

    return {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {
                "driver": {
                    "name": "CrowdStrike FCS Image",
                    "version": "",
                    "rules": list(rules.values()),
                }
            },
            "results": results,
        }],
    }


def convert(input_path, output_path, scan_type):
    with open(input_path) as f:
        data = json.load(f)

    if scan_type == "iac":
        sarif = iac_to_sarif(data)
    else:
        sarif = image_to_sarif(data)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(sarif, f, indent=2)

    print("Converted {} -> {} ({} results)".format(
        input_path, output_path, len(sarif["runs"][0]["results"])
    ))


if __name__ == "__main__":
    # Usage: fcs_to_sarif.py <scan_type> <input_dir_or_file> <output_sarif>
    scan_type = sys.argv[1]   # iac or image
    input_path = sys.argv[2]
    output_path = sys.argv[3]

    if os.path.isdir(input_path):
        json_files = glob.glob(os.path.join(input_path, "*.json"))
        if not json_files:
            print("No JSON files found in", input_path)
            sys.exit(0)
        input_path = json_files[0]

    convert(input_path, output_path, scan_type)
