import requests
from bs4 import BeautifulSoup
from utils.logger import get_logger

logger = get_logger("Scraper")

TARGET_ROLES = ["software engineer", "software developer", "sde", "data analyst", "analyst", "backend", "frontend", "full stack", "python developer", "java developer"]

class JobScraper:
    def __init__(self):
        self.jobs = []

    def filter_job(self, title):
        return any(role.lower() in title.lower() for role in TARGET_ROLES)

    def scrape_remoteok(self):
        try:
            res = requests.get("https://remoteok.com/api", timeout=10)
            data = res.json()
            for j in data[1:]: # First element is often a legal notice
                if self.filter_job(j.get('position', '')):
                    self.jobs.append({
                        "title": j.get('position'), "company": j.get('company'),
                        "location": j.get('location', 'Remote'), "url": j.get('url'),
                        "tags": j.get('tags', ''), "source": "RemoteOK", "date": j.get('date')
                    })
        except Exception as e: logger.error(f"RemoteOK failed: {e}")

    def scrape_remotive(self):
        try:
            res = requests.get("https://remotive.com/api/remote-jobs", timeout=10)
            data = res.json().get('jobs', [])
            for j in data:
                if self.filter_job(j.get('title', '')):
                    self.jobs.append({
                        "title": j.get('title'), "company": j.get('company_name'),
                        "location": "Remote", "url": j.get('url'),
                        "tags": j.get('category', ''), "source": "Remotive", "date": j.get('publication_date')
                    })
        except Exception as e: logger.error(f"Remotive failed: {e}")

    def scrape_weworkremotely(self):
        try:
            res = requests.get("https://weworkremotely.com/categories/remote-dev-jobs.rss", timeout=10)
            soup = BeautifulSoup(res.content, "xml")
            for item in soup.find_all("item"):
                title = item.find("title").text
                if self.filter_job(title):
                    self.jobs.append({
                        "title": title, "company": "Various", 
                        "location": "Remote", "url": item.find("link").text,
                        "tags": "WWR", "source": "WeWorkRemotely", "date": item.find("pubDate").text
                    })
        except Exception as e: logger.error(f"WWR failed: {e}")

    def run_all(self):
        logger.info("Starting scraping process...")
        self.scrape_remoteok()
        self.scrape_remotive()
        self.scrape_weworkremotely()
        # Deduplicate
        seen_urls = set()
        unique_jobs = []
        for j in self.jobs:
            if j['url'] not in seen_urls:
                unique_jobs.append(j)
                seen_urls.add(j['url'])
        return unique_jobs
