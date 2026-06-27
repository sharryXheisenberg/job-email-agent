import os
import schedule
import time
from datetime import datetime
from dotenv import load_dotenv
from scrapers.job_scraper import JobScraper
from agents.job_agent import JobAgent
from templates.email_template import build_html_email, build_plain_email
from utils.email_sender import send_email
from utils.logger import get_logger

load_dotenv()
logger = get_logger("Runner")


def run_pipeline(dry_run=False):
    logger.info("Pipeline started...")

    # 1. Scraping
    scraper = JobScraper()
    raw_jobs = scraper.run_all()

    # os.getenv default only applies when the var is completely UNSET.
    # GitHub Actions passes an unset secret through as an EMPTY STRING, not
    # absent, which would otherwise crash with
    # "invalid literal for int() with base 10: ''". This handles both cases.
    min_jobs_raw = os.getenv("MIN_JOBS", "10").strip()
    min_jobs = int(min_jobs_raw) if min_jobs_raw else 10
    if len(raw_jobs) < min_jobs:
        logger.warning(f"Not enough jobs found ({len(raw_jobs)} < {min_jobs} minimum). Proceeding anyway.")

    if not raw_jobs:
        logger.error("No jobs found from any source. Aborting this run — nothing to send.")
        return

    # 2. AI processing
    agent = JobAgent(os.getenv("GROQ_API_KEY"))
    ranked_jobs = agent.rank_and_summarise(raw_jobs)
    intro = agent.generate_email_intro(ranked_jobs)

    if dry_run:
        pune_count = sum(1 for j in ranked_jobs if "pune" in (j.get('location', '') or "").lower())
        logger.info(f"DRY RUN: {len(ranked_jobs)} jobs collected ({pune_count} Pune-located). "
                    f"Printing top 5 instead of sending email:")
        for j in ranked_jobs[:5]:
            print(f"Rank {j.get('rank', '?')}: {j.get('title', 'n/a')} - {j.get('company', 'n/a')} "
                  f"[{j.get('source', 'n/a')}] - {j.get('location', 'n/a')}")
        return

    # 3. Build Email
    html = build_html_email(ranked_jobs, intro)
    plain = build_plain_email(ranked_jobs, intro)
    subject = f"Tech Job Digest (Pune + India Focus) - {datetime.now().strftime('%Y-%m-%d')} | Entry-Level Openings Inside"

    # 4. Send
    recipients_raw = os.getenv("RECIPIENT_EMAILS", "")
    recipients = [r.strip() for r in recipients_raw.split(",") if r.strip()]
    if not recipients:
        logger.error("No RECIPIENT_EMAILS configured. Aborting send.")
        return

    send_email(
        os.getenv("SENDER_EMAIL"),
        os.getenv("SENDER_APP_PASSWORD"),
        recipients,
        subject,
        html,
        plain
    )
    logger.info("✅ Pipeline completed successfully.")


def start_scheduler():
    send_time = os.getenv("SEND_TIME", "09:00")
    schedule.every().day.at(send_time).do(run_pipeline)

    logger.info(f"Scheduler active. Jobs will be sent daily at {send_time}")
    # Run once immediately on startup
    run_pipeline()

    while True:
        schedule.run_pending()
        time.sleep(30)
