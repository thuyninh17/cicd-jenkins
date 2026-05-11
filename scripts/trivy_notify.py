#!/usr/bin/env python3

import argparse
import json
import re
import sys
import requests


def parse_args():
    parser = argparse.ArgumentParser(description="Parse Trivy report and notify Telegram")
    parser.add_argument("--report",        required=True,  help="Path to trivy-report.txt")
    parser.add_argument("--report-json",   required=False, help="Path to trivy-report.json (preferred for accurate counting)")
    parser.add_argument("--bot-token",     required=True,  help="Telegram bot token")
    parser.add_argument("--chat-id",       required=True,  help="Telegram chat ID")
    parser.add_argument("--job-name",      required=True,  help="Jenkins job name")
    parser.add_argument("--build-number",  required=True,  help="Jenkins build number")
    parser.add_argument("--image",         required=True,  help="Docker image name")
    return parser.parse_args()


def count_severity(lines, severity):
    """
    Đếm số CVE dựa vào pattern 'CVE-XXXX-XXXX' xuất hiện trên cùng dòng với severity.
    Tránh dùng ký tự │ vì có thể bị encoding khác nhau.
    """
    sev = re.escape(severity)
    pattern = re.compile(rf'(CVE-\d{{4}}-\d+.*\b{sev}\b)|(\b{sev}\b.*CVE-\d{{4}}-\d+)')
    return sum(1 for line in lines if pattern.search(line))

def _count_from_json(report_json_path: str):
    """
    Trivy JSON is the only reliable way to count actual vulnerabilities.
    We count unique VulnerabilityID per severity to avoid duplicates across packages/layers.
    """
    with open(report_json_path, "r", encoding="utf-8", errors="replace") as f:
        data = json.load(f)

    by_sev = {"HIGH": set(), "CRITICAL": set()}

    results = data.get("Results") or []
    for r in results:
        vulns = r.get("Vulnerabilities") or []
        for v in vulns:
            sev = (v.get("Severity") or "").upper()
            vid = v.get("VulnerabilityID") or v.get("VulnID") or v.get("ID")
            if not vid:
                continue
            if sev in by_sev:
                by_sev[sev].add(str(vid))

    return len(by_sev["HIGH"]), len(by_sev["CRITICAL"])


def has_vulnerabilities(lines):
    return any(
        re.search(r'(CVE-\d{4}-\d+.*\b(HIGH|CRITICAL)\b)|(\b(HIGH|CRITICAL)\b.*CVE-\d{4}-\d+)', line)
        for line in lines
    )


def send_message(bot_token, chat_id, text):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    resp = requests.post(url, data={"chat_id": chat_id, "text": text}, timeout=15)
    resp.raise_for_status()
    return resp.json()


def send_document(bot_token, chat_id, filepath, caption):
    url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
    with open(filepath, "rb") as f:
        resp = requests.post(
            url,
            data={"chat_id": chat_id, "caption": caption},
            files={"document": f},
            timeout=60,
        )
    resp.raise_for_status()
    return resp.json()


def main():
    args = parse_args()

    with open(args.report, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    high_count = 0
    critical_count = 0

    if args.report_json:
        try:
            high_count, critical_count = _count_from_json(args.report_json)
        except Exception as e:
            print(f"[WARN] Failed to parse JSON report ({args.report_json}): {e}. Falling back to text parsing.")
            high_count = count_severity(lines, "HIGH")
            critical_count = count_severity(lines, "CRITICAL")
    else:
        high_count = count_severity(lines, "HIGH")
        critical_count = count_severity(lines, "CRITICAL")

    if (high_count + critical_count) == 0 and not has_vulnerabilities(lines):
        print("No HIGH/CRITICAL vulnerabilities found. Skipping Telegram notification.")
        sys.exit(0)

    print(f"[DEBUG] HIGH={high_count}, CRITICAL={critical_count}")

    summary = (
        f"⚠️ Trivy Vulnerabilities Detected\n\n"
        f"Job:   {args.job_name}\n"
        f"Build: #{args.build_number}\n"
        f"Image: {args.image}\n\n"
        f"Total: HIGH={high_count}, CRITICAL={critical_count}\n\n"
        f"📎 Full CVE report attached below."
    )

    print(summary)

    send_message(args.bot_token, args.chat_id, summary)
    print("Summary message sent.")

    send_document(
        args.bot_token,
        args.chat_id,
        args.report,
        caption=f"Full Trivy Report - {args.job_name} #{args.build_number}",
    )
    print("Full report sent.")

    # Signal to CI that vulnerabilities were found (distinct from runtime failure).
    sys.exit(2)


if __name__ == "__main__":
    main()