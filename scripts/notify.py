#!/usr/bin/env python3

import argparse
import requests


def parse_args():
    parser = argparse.ArgumentParser(description="Send pipeline status to Telegram")
    parser.add_argument("--bot-token",     required=True,  help="Telegram bot token")
    parser.add_argument("--chat-id",       required=True,  help="Telegram chat ID")
    parser.add_argument("--status",        required=True,  choices=["success", "failure"])
    parser.add_argument("--job-name",      required=True,  help="Jenkins job name")
    parser.add_argument("--build-number",  required=True,  help="Jenkins build number")
    parser.add_argument("--text",          required=False, help="Override notification text")
    return parser.parse_args()


def send_message(bot_token, chat_id, text):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    resp = requests.post(url, data={"chat_id": chat_id, "text": text}, timeout=15)
    resp.raise_for_status()
    return resp.json()


def main():
    args = parse_args()

    if args.text:
        text = args.text
    elif args.status == "success":
        text = f"✅ SUCCESS: {args.job_name} #{args.build_number}"
    else:
        text = f"❌ FAILED: {args.job_name} #{args.build_number}"

    result = send_message(args.bot_token, args.chat_id, text)
    print(f"Notification sent: {text}")
    print(f"Telegram response: {result}")


if __name__ == "__main__":
    main()