"""
scrapers/job_scraper.py
-----------------------
Scrapes job listings from multiple free job boards:
  - RemoteOK
  - GitHub Jobs (via Awesome Remote Job style listings)
  - Remotive.io
  - We Work Remotely
  - HackerNews "Who is Hiring" (monthly thread)
"""

import requests
import json
import time
import random
from bs4 import BeautifulSoup
from utils.logger import get_logger

logger = get_logger("JobScraper")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

TARGET_ROLES = [
    "software engineer", "software developer", "sde", "sde intern",
    "data analyst", "analyst", "backend", "frontend", "full stack",
    "python developer", "java developer", "web developer"
]


def _is_relevant(title: str) -> bool:
    title_lower = title.lower()
    return any(role in title_lower for role in TARGET_ROLES)


def _safe_get(url: str, timeout: int = 10, retries: int = 2) -> requests.Response | None:
    for attempt in range(retries):
        try:
            time.sleep(random.uniform(0.5, 1.5))
            resp = requests.get(url, headers=HEADERS, timeout=timeout)
            resp.raise_for_status()
            return resp
        except Exception as e:
            logger.warning(f"Attempt {attempt+1} failed for {url}: {e}")
    return None


# ── Source 1: RemoteOK JSON API ──────────────────────────────────────────────
def scrape_remoteok() -> list[dict]:
    jobs = []
    try:
        resp = _safe_get("https://remoteok.com/api")
        if not resp:
            return jobs
        data = resp.json()
        # First item is a legal notice, skip it
        for item in data[1:]:
            title = item.get("position", "")
            if not _is_relevant(title):
                continue
            jobs.append({
                "title": title,
                "company": item.get("company", "Unknown"),
                "location": item.get("location", "Remote"),
                "url": item.get("url", f"https://remoteok.com/jobs/{item.get('id','')}"),
                "tags": ", ".join(item.get("tags", [])[:5]),
                "source": "RemoteOK",
                "date": item.get("date", "")[:10] if item.get("date") else "",
            })
            if len(jobs) >= 15:
                break
    except Exception as e:
        logger.error(f"RemoteOK scrape failed: {e}")
    logger.info(f"RemoteOK: {len(jobs)} jobs")
    return jobs


# ── Source 2: Remotive.io API ────────────────────────────────────────────────
def scrape_remotive() -> list[dict]:
    jobs = []
    search_terms = ["software-engineer", "developer", "data-analyst"]
    try:
        for term in search_terms:
            url = f"https://remotive.com/api/remote-jobs?search={term}&limit=20"
            resp = _safe_get(url)
            if not resp:
                continue
            data = resp.json()
            for item in data.get("jobs", []):
                title = item.get("title", "")
                if not _is_relevant(title):
                    continue
                jobs.append({
                    "title": title,
                    "company": item.get("company_name", "Unknown"),
                    "location": item.get("candidate_required_location", "Remote"),
                    "url": item.get("url", ""),
                    "tags": ", ".join(item.get("tags", [])[:5]),
                    "source": "Remotive",
                    "date": item.get("publication_date", "")[:10],
                })
            if len(jobs) >= 15:
                break
    except Exception as e:
        logger.error(f"Remotive scrape failed: {e}")
    logger.info(f"Remotive: {len(jobs)} jobs")
    return jobs


# ── Source 3: We Work Remotely ───────────────────────────────────────────────
def scrape_weworkremotely() -> list[dict]:
    jobs = []
    categories = [
        "https://weworkremotely.com/categories/remote-programming-jobs.rss",
        "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss",
        "https://weworkremotely.com/categories/remote-front-end-programming-jobs.rss",
    ]
    try:
        for feed_url in categories:
            resp = _safe_get(feed_url)
            if not resp:
                continue
            soup = BeautifulSoup(resp.text, "xml")
            for item in soup.find_all("item")[:10]:
                title_tag = item.find("title")
                link_tag = item.find("link")
                region_tag = item.find("region")
                company_tag = item.find("company")
                if not title_tag:
                    continue
                title = title_tag.text.strip()
                # WWR titles are "Company: Role"
                if ":" in title:
                    parts = title.split(":", 1)
                    company = parts[0].strip()
                    role = parts[1].strip()
                else:
                    company = company_tag.text if company_tag else "Unknown"
                    role = title
                if not _is_relevant(role):
                    continue
                url = link_tag.text.strip() if link_tag else ""
                jobs.append({
                    "title": role,
                    "company": company,
                    "location": region_tag.text if region_tag else "Remote",
                    "url": url,
                    "tags": "",
                    "source": "WeWorkRemotely",
                    "date": "",
                })
            if len(jobs) >= 15:
                break
    except Exception as e:
        logger.error(f"WeWorkRemotely scrape failed: {e}")
    logger.info(f"WeWorkRemotely: {len(jobs)} jobs")
    return jobs


# ── Source 4: GitHub Jobs via Jobicy API ─────────────────────────────────────
def scrape_jobicy() -> list[dict]:
    jobs = []
    try:
        url = "https://jobicy.com/api/v2/remote-jobs?count=20&tag=developer"
        resp = _safe_get(url)
        if not resp:
            return jobs
        data = resp.json()
        for item in data.get("jobs", []):
            title = item.get("jobTitle", "")
            if not _is_relevant(title):
                continue
            jobs.append({
                "title": title,
                "company": item.get("companyName", "Unknown"),
                "location": item.get("jobGeo", "Remote"),
                "url": item.get("url", ""),
                "tags": ", ".join(item.get("jobIndustry", [])[:3]) if isinstance(item.get("jobIndustry"), list) else "",
                "source": "Jobicy",
                "date": item.get("pubDate", "")[:10],
            })
            if len(jobs) >= 10:
                break
    except Exception as e:
        logger.error(f"Jobicy scrape failed: {e}")
    logger.info(f"Jobicy: {len(jobs)} jobs")
    return jobs


# ── Source 5: Arbeitnow (EU + Remote) ────────────────────────────────────────
def scrape_arbeitnow() -> list[dict]:
    jobs = []
    try:
        resp = _safe_get("https://www.arbeitnow.com/api/job-board-api")
        if not resp:
            return jobs
        data = resp.json()
        for item in data.get("data", []):
            title = item.get("title", "")
            if not _is_relevant(title):
                continue
            jobs.append({
                "title": title,
                "company": item.get("company_name", "Unknown"),
                "location": "Remote" if item.get("remote") else item.get("location", "EU"),
                "url": item.get("url", ""),
                "tags": ", ".join(item.get("tags", [])[:4]),
                "source": "Arbeitnow",
                "date": str(item.get("created_at", ""))[:10],
            })
            if len(jobs) >= 10:
                break
    except Exception as e:
        logger.error(f"Arbeitnow scrape failed: {e}")
    logger.info(f"Arbeitnow: {len(jobs)} jobs")
    return jobs


# ── Main collector ────────────────────────────────────────────────────────────
def collect_jobs(min_jobs: int = 10) -> list[dict]:
    """
    Collect jobs from all sources, deduplicate, and return at least min_jobs.
    """
    all_jobs: list[dict] = []
    scrapers = [
        scrape_remoteok,
        scrape_remotive,
        scrape_weworkremotely,
        scrape_jobicy,
        scrape_arbeitnow,
    ]
    for scraper in scrapers:
        try:
            results = scraper()
            all_jobs.extend(results)
        except Exception as e:
            logger.error(f"Scraper {scraper.__name__} crashed: {e}")

    # Deduplicate by URL
    seen_urls = set()
    unique_jobs = []
    for job in all_jobs:
        url = job.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_jobs.append(job)

    logger.info(f"Total unique jobs collected: {len(unique_jobs)}")

    if len(unique_jobs) < min_jobs:
        logger.warning(
            f"Only {len(unique_jobs)} jobs found, below minimum of {min_jobs}. "
            "Sending what we have."
        )

    return unique_jobs