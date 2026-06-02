"""
main.py
-------
Entry point for the AI Job Email Agent.

Usage:
  python main.py            → start scheduler (runs once now, then daily at SEND_TIME)
  python main.py --now      → run pipeline immediately and exit (for testing)
  python main.py --test     → dry run: scrape + AI rank, print results, do NOT send email
"""

import sys
import os
from dotenv import load_dotenv

# Load .env FIRST before any other import that reads env vars
load_dotenv()

from utils.logger import get_logger

logger = get_logger("Main")


def _check_env():
    missing = []
    for key in ["GROQ_API_KEY", "SENDER_EMAIL", "SENDER_APP_PASSWORD", "RECIPIENT_EMAILS"]:
        if not os.getenv(key):
            missing.append(key)
    if missing:
        logger.error(
            f"Missing required environment variables: {', '.join(missing)}\n"
            "Copy .env.example → .env and fill in the values."
        )
        sys.exit(1)


def cmd_test():
    """Dry run – print jobs to terminal, no email sent."""
    from scrapers.job_scraper import collect_jobs
    from agents.job_agent import rank_and_summarise, generate_email_intro

    min_jobs = int(os.getenv("MIN_JOBS", "10"))
    print("\n🔍  Scraping job boards...\n")
    jobs = collect_jobs(min_jobs=min_jobs)
    if not jobs:
        print("No jobs found. Check your internet connection.")
        return

    print(f"✅  Scraped {len(jobs)} jobs. Sending to Groq for ranking...\n")
    jobs = rank_and_summarise(jobs)
    intro = generate_email_intro(jobs)

    print("=" * 70)
    print(intro)
    print("=" * 70)
    for i, j in enumerate(jobs, 1):
        print(f"\n#{i}  {j.get('title','N/A')}  [{j.get('source','')}]")
        print(f"    {j.get('company','?')}  ·  {j.get('location','Remote')}")
        if j.get("ai_summary"):
            print(f"    🤖 {j['ai_summary']}")
        print(f"    🔗 {j.get('url','')}")
    print("\n✅  Dry run complete. No email sent.")


def cmd_now():
    """Run the full pipeline immediately."""
    from scheduler.runner import run_pipeline
    run_pipeline()


def cmd_schedule():
    """Start the daemon scheduler."""
    from scheduler.runner import start_scheduler
    start_scheduler()


if __name__ == "__main__":
    _check_env()

    arg = sys.argv[1] if len(sys.argv) > 1 else ""

    if arg == "--test":
        cmd_test()
    elif arg == "--now":
        cmd_now()
    else:
        cmd_schedule()