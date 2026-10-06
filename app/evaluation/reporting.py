"""Persist machine-readable and human-readable baseline reports."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def build_report(
    *, suites: dict[str, Any], configuration: dict[str, Any], dataset_sizes: dict[str, int]
) -> dict[str, Any]:
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset_sizes": dataset_sizes,
        "configuration": configuration,
        "suites": suites,
        "limitations": [
            "Small manually curated labels are a baseline set, not a representative production benchmark.",
            "Complaint labels and KB relevance judgments need domain review before drawing broad conclusions.",
            "No LLM correctness, hallucination, or resolution-quality metric is reported without reviewed ground truth.",
            "Historical support-ticket answers are not used as authoritative ground truth.",
        ],
    }


def write_reports(report: dict[str, Any], report_dir: Path) -> tuple[Path, Path]:
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / "latest.json"
    markdown_path = report_dir / "latest.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, markdown_path


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Support Resolution Assistant Evaluation Baseline",
        "",
        f"- Timestamp: `{report['created_at']}`",
        "- Datasets: " + ", ".join(
            f"{name}={count}" for name, count in report["dataset_sizes"].items()
        ),
        "",
        "## Model and configuration",
        "",
        "| Setting | Value |",
        "| --- | --- |",
    ]
    lines.extend(
        f"| {key} | `{value}` |" for key, value in report["configuration"].items()
    )
    for suite_name, suite in report["suites"].items():
        lines.extend([
            "",
            f"## {suite_name.replace('_', ' ').title()}",
            "",
            f"Dataset version: `{suite['dataset_version']}`; examples: {suite['example_count']}",
        ])
        if "successful_response_count" in suite:
            lines.append(f"Successful responses: {suite['successful_response_count']}")
        if "invalid_model_output_count" in suite:
            lines.append(f"Invalid model outputs: {suite['invalid_model_output_count']}")
        lines.extend([
            "",
            "| Metric | Value |",
            "| --- | ---: |",
        ])
        for metric, value in suite["metrics"].items():
            if isinstance(value, (int, float)):
                lines.append(f"| {metric} | {value:.4f} |" if isinstance(value, float) else f"| {metric} | {value} |")
        if "hit_definition" in suite:
            lines.extend(["", suite["hit_definition"], "", suite["mrr_definition"]])
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in report["limitations"])
    lines.append("")
    return "\n".join(lines)
