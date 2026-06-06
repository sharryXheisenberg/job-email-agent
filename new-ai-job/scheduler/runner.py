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
    
    if len(raw_jobs) < int(os.getenv("MIN_JOBS", 10)):
        logger.warning(f"Not enough jobs found ({len(raw_jobs)}). Proceeding anyway.")

    # 2. AI processing
    agent = JobAgent(os.getenv("GROQ_API_KEY"))
    ranked_jobs = agent.rank_and_summarise(raw_jobs)
    intro = agent.generate_email_intro(ranked_jobs)
    
    if dry_run:
        logger.info("DRY RUN: Printing top 3 jobs instead of sending email:")
        for j in ranked_jobs[:3]:
            print(f"Rank {j.get('rank', '?')}: {j.get('title', 'n/a')} - {j.get('company', 'n/a')}")
        return
        return

    # 3. Build Email
    html = build_html_email(ranked_jobs, intro)
    plain = build_plain_email(ranked_jobs, intro)
    subject = f"Tech Job Digest - {datetime.now().strftime('%Y-%m-%d')} | Fresh Openings Inside"
    
    # 4. Send
    recipients = os.getenv("RECIPIENT_EMAILS").split(",")
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
