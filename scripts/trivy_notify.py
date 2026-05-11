#!/usr/bin/env python3

import argparse
import re
import sys
import requests


def parse_args():
    parser = argparse.ArgumentParser(description="Parse Trivy report and notify Telegram")
    parser.add_argument("--report",        required=True,  help="Path to trivy-report.txt")
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
    pattern = re.compile(r'CVE-\d{4}-\d+.*' + severity + r'|' + severity + r'.*CVE-\d{4}-\d+')
    return sum(1 for line in lines if pattern.search(line))


def has_vulnerabilities(lines):
    return any(
        re.search(r'CVE-\d{4}-\d+.*(HIGH|CRITICAL)|(HIGH|CRITICAL).*CVE-\d{4}-\d+', line)
        for line in lines
    )


def send_message(bot_token, chat_id, text):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    resp = requests.post(url, data={"chat_id": chat_id, "text": text})
    resp.raise_for_status()
    return resp.json()


def send_document(bot_token, chat_id, filepath, caption):
    url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
    with open(filepath, "rb") as f:
        resp = requests.post(
            url,
            data={"chat_id": chat_id, "caption": caption},
            files={"document": f},
        )
    resp.raise_for_status()
    return resp.json()


def main():
    args = parse_args()

    with open(args.report, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    if not has_vulnerabilities(lines):
        print("No HIGH/CRITICAL vulnerabilities found. Skipping Telegram notification.")
        sys.exit(0)

    high_count     = count_severity(lines, "HIGH")
    critical_count = count_severity(lines, "CRITICAL")

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


if __name__ == "__main__":
    main()