"""
Cadly DFM Part Analyzer
Analyzes the currently open Fusion 360 part for manufacturing violations.

Usage: python analyze_part.py [--process all|fdm|sla|cnc]
Requires: Fusion 360 add-in running on http://localhost:5000
"""

import sys
import os
import json
import argparse
import requests

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.dfm.analyzer import DFMAnalyzer
from src.dfm.violations import Severity
from src.cost.estimator import CostEstimator

FUSION_URL = "http://localhost:5000"


def print_header(title):
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_section(title):
    print()
    print(f"--- {title} ---")


def severity_symbol(sev):
    return {"critical": "XX", "warning": "!!", "suggestion": "**"}.get(sev, "  ")


def main():
    parser = argparse.ArgumentParser(description="Cadly DFM Part Analyzer")
    parser.add_argument("--process", default="all", choices=["all", "fdm", "sla", "cnc"],
                        help="Filter analysis by manufacturing process")
    args = parser.parse_args()

    print_header("Cadly DFM Part Analyzer")

    # Check connection
    print("\nConnecting to Fusion 360...", end=" ")
    try:
        resp = requests.get(f"{FUSION_URL}/test_connection", timeout=5)
        print("Connected!")
    except Exception:
        print("FAILED")
        print(f"Cannot reach Fusion 360 at {FUSION_URL}")
        print("Make sure the add-in is running.")
        return 1

    # Run DFM analysis
    print(f"Running DFM analysis (process filter: {args.process})...")
    analyzer = DFMAnalyzer(FUSION_URL)
    result = analyzer.analyze(args.process)
    data = result.to_dict()

    # Part summary
    print_section("Part Summary")
    print(f"  Name:           {data['part_name']}")
    print(f"  Volume:         {data['body_volume_cm3']:.4f} cm3")
    print(f"  Surface Area:   {data['body_area_cm2']:.4f} cm2")
    print(f"  Manufacturable: {'Yes' if data['is_manufacturable'] else 'NO'}")
    print(f"  Best Process:   {data['recommended_process']}")

    # Violations
    print_section(f"DFM Violations ({data['violation_count']} total)")
    print(f"  Critical: {data['critical_count']}  |  Warning: {data['warning_count']}  |  Suggestion: {data['violation_count'] - data['critical_count'] - data['warning_count']}")
    print()

    if not data["violations"]:
        print("  No violations found! Part is ready for manufacturing.")
    else:
        for i, v in enumerate(data["violations"], 1):
            sev = v["severity"].upper()
            sym = severity_symbol(v["severity"])
            fixable = " [AUTO-FIX]" if v["fixable"] else ""
            print(f"  [{sym}] #{i}  {v['rule_id']}  ({sev}){fixable}")
            print(f"       {v['message']}")
            print(f"       Current: {v['current_value']:.2f}  |  Required: {v['required_value']:.2f}")
            print(f"       Feature: {v['feature_id']}")
            print()

    # Cost estimation
    print_section("Cost Estimates")
    try:
        resp = requests.get(f"{FUSION_URL}/get_body_properties", timeout=20)
        body_props = resp.json()
        bodies = body_props.get("bodies", [])
        if bodies:
            first = bodies[0]
            estimator = CostEstimator()
            estimates = estimator.estimate_all(
                volume_cm3=first.get("volume_cm3", 0),
                area_cm2=first.get("area_cm2", 0),
                bounding_box=first.get("bounding_box", {"min": [0,0,0], "max": [1,1,1]}),
            )
            recommendation = estimator.get_recommendation(estimates)

            print(f"  {'Process':<10} {'Material':>10} {'Time':>10} {'Setup':>10} {'TOTAL':>10}")
            print(f"  {'-'*10} {'-'*10} {'-'*10} {'-'*10} {'-'*10}")
            for est in estimates:
                rec = " <-- BEST" if est.process == recommendation else ""
                print(f"  {est.process:<10} ${est.material_cost:>8.2f} ${est.time_cost:>8.2f} ${est.setup_cost:>8.2f} ${est.total_cost:>8.2f}{rec}")
        else:
            print("  No bodies found for cost estimation.")
    except Exception as e:
        print(f"  Cost estimation failed: {e}")

    # Raw data dump
    print_section("Raw Analysis JSON")
    print(json.dumps(data, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
