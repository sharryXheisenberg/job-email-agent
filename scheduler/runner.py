"""
scheduler/runner.py
-------------------
Schedules the job digest to run once daily at the time
configured in SEND_TIME (default 09:00).
"""

import os
import time
import schedule
from utils.logger import get_logger

logger = get_logger("Scheduler")


def run_pipeline():
    """Full pipeline: scrape → AI rank → build email → send."""
    # Import here to avoid circular imports
    from scrapers.job_scraper import collect_jobs
    from agents.job_agent import rank_and_summarise, generate_email_intro
    from templates.email_template import build_html_email, build_plain_email
    from utils.email_sender import send_job_digest

    min_jobs = int(os.getenv("MIN_JOBS", "10"))

    logger.info("=" * 60)
    logger.info("Pipeline started")
    logger.info("=" * 60)

    # 1. Scrape
    logger.info("Step 1/4 – Scraping job boards...")
    jobs = collect_jobs(min_jobs=min_jobs)
    if not jobs:
        logger.error("No jobs collected. Aborting this run.")
        return

    # 2. AI rank + summarise
    logger.info("Step 2/4 – AI ranking & summarising with Groq...")
    jobs = rank_and_summarise(jobs)

    # 3. Build email
    logger.info("Step 3/4 – Building email...")
    intro      = generate_email_intro(jobs)
    html_body  = build_html_email(jobs, intro)
    plain_body = build_plain_email(jobs, intro)

    # 4. Send
    logger.info("Step 4/4 – Sending email...")
    success = send_job_digest(html_body, plain_body)
    if success:
        logger.info("✅ Pipeline completed successfully!")
    else:
        logger.error("❌ Pipeline completed but email failed to send.")


def start_scheduler():
    send_time = os.getenv("SEND_TIME", "09:00").strip()
    logger.info(f"Scheduler started. Daily digest will be sent at {send_time}.")
    logger.info("Press Ctrl+C to stop.\n")

    schedule.every().day.at(send_time).do(run_pipeline)

    # Also run immediately on first start so you can verify it works
    logger.info("Running pipeline now for initial verification...")
    run_pipeline()

    while True:
        schedule.run_pending()
        time.sleep(30)