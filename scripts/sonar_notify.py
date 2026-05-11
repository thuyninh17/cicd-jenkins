#!/usr/bin/env python3

import argparse
import requests


DEFAULT_METRICS = [
    "bugs",
    "vulnerabilities",
    "security_hotspots",
    "code_smells",
    "coverage",
    "duplicated_lines_density",
    "ncloc",
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Fetch SonarQube summary and send detailed Telegram notification."
    )
    parser.add_argument("--sonar-host", required=True, help="SonarQube host URL")
    parser.add_argument("--project-key", required=True, help="SonarQube project key")
    parser.add_argument("--sonar-token", required=True, help="SonarQube token")
    parser.add_argument("--quality-gate", required=True, help="Quality gate status from Jenkins")
    parser.add_argument("--bot-token", required=True, help="Telegram bot token")
    parser.add_argument("--chat-id", required=True, help="Telegram chat id")
    parser.add_argument("--job-name", required=True, help="Jenkins job name")
    parser.add_argument("--build-number", required=True, help="Jenkins build number")
    parser.add_argument("--build-url", required=False, default="", help="Jenkins build URL")
    parser.add_argument("--branch-name", required=False, default="", help="Jenkins branch name")
    return parser.parse_args()


def sonar_auth(token):
    return (token, "")


def fetch_quality_gate_details(sonar_host, project_key, token):
    url = f"{sonar_host.rstrip('/')}/api/qualitygates/project_status"
    resp = requests.get(
        url,
        params={"projectKey": project_key},
        auth=sonar_auth(token),
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json().get("projectStatus", {})
    return data.get("status", "UNKNOWN"), data.get("conditions", []) or []


def fetch_metrics(sonar_host, project_key, token):
    url = f"{sonar_host.rstrip('/')}/api/measures/component"
    resp = requests.get(
        url,
        params={"component": project_key, "metricKeys": ",".join(DEFAULT_METRICS)},
        auth=sonar_auth(token),
        timeout=20,
    )
    resp.raise_for_status()
    measures = (resp.json().get("component") or {}).get("measures", []) or []
    return {m.get("metric"): m.get("value", "-") for m in measures if m.get("metric")}


def format_condition(condition):
    metric = condition.get("metricKey", "unknown_metric")
    status = condition.get("status", "UNKNOWN")
    actual = condition.get("actualValue", "-")
    error = condition.get("errorThreshold", "-")
    comparator = condition.get("comparator", "")
    symbol = "✅" if status == "OK" else "❌"
    return f"{symbol} {metric}: {actual} {comparator} {error}".strip()


def send_telegram(bot_token, chat_id, message):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    resp = requests.post(
        url,
        data={"chat_id": chat_id, "text": message},
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()


def main():
    args = parse_args()

    dashboard = f"{args.sonar_host.rstrip('/')}/dashboard?id={args.project_key}"
    gate_symbol = "✅" if args.quality_gate == "OK" else "⚠️"

    details_error = ""
    gate_api_status = args.quality_gate
    conditions = []
    metrics = {}

    try:
        gate_api_status, conditions = fetch_quality_gate_details(
            args.sonar_host, args.project_key, args.sonar_token
        )
        metrics = fetch_metrics(args.sonar_host, args.project_key, args.sonar_token)
    except Exception as exc:
        details_error = f"Could not fetch Sonar API details: {exc}"

    lines = [
        f"{gate_symbol} SONARQUBE SUMMARY",
        f"Project: {args.project_key}",
        f"Job: {args.job_name}",
        f"Build: #{args.build_number}",
        f"Branch: {args.branch_name or 'N/A'}",
        f"Quality Gate (Jenkins): {args.quality_gate}",
        f"Quality Gate (Sonar API): {gate_api_status}",
        "",
        "Key Metrics:",
        f"- Bugs: {metrics.get('bugs', '-')}",
        f"- Vulnerabilities: {metrics.get('vulnerabilities', '-')}",
        f"- Security Hotspots: {metrics.get('security_hotspots', '-')}",
        f"- Code Smells: {metrics.get('code_smells', '-')}",
        f"- Coverage: {metrics.get('coverage', '-')}%",
        f"- Duplications: {metrics.get('duplicated_lines_density', '-')}%",
        f"- Lines of Code: {metrics.get('ncloc', '-')}",
    ]

    if conditions:
        lines.extend(["", "Quality Gate Conditions:"])
        lines.extend(format_condition(c) for c in conditions)

    if args.build_url:
        lines.extend(["", f"Jenkins: {args.build_url}"])

    lines.append(f"Dashboard: {dashboard}")

    if details_error:
        lines.extend(["", f"Note: {details_error}"])

    message = "\n".join(lines)
    result = send_telegram(args.bot_token, args.chat_id, message)
    print(f"Sonar notification sent for {args.project_key}.")
    print(f"Telegram response: {result}")


if __name__ == "__main__":
    main()
