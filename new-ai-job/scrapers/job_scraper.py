import requests
from bs4 import BeautifulSoup
from utils.logger import get_logger

logger = get_logger("Scraper")

# Expanded keywords for SDE and Data roles
TARGET_ROLES = [
    "software engineer", "software developer", "sde", "sde i", "sde ii", 
    "data analyst", "analyst", "backend developer", "frontend developer", 
    "full stack", "python developer", "java developer", "c++ developer",
    "machine learning", "data engineer", "intern"
]

class JobScraper:
    def __init__(self):
        self.jobs = []
        # Standard browser headers to avoid being blocked
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        }

    def filter_job(self, title):
        if not title: return False
        return any(role.lower() in title.lower() for role in TARGET_ROLES)

    def is_india_job(self, text):
        """Checks if a job description or location mentions India"""
        if not text: return False
        india_keywords = ["india", "bangalore", "bengaluru", "hyderabad", "pune", "mumbai", "delhi", "noida", "gurgaon", "chennai"]
        return any(word in text.lower() for word in india_keywords)

    def scrape_internshala(self):
        """Scrapes Internshala for SDE and Data roles in India"""
        logger.info("🇮🇳 Scraping Internshala (India Specific)...")
        try:
            # We target the 'software-engineering' and 'data-science' categories specifically
            categories = ["software-engineering", "data-science"]
            for cat in categories:
                url = f"https://internshala.com/jobs/{cat}"
                res = requests.get(url, headers=self.headers, timeout=15)
                soup = BeautifulSoup(res.text, "html.parser")
                
                # Internshala job cards typically have a specific class
                job_cards = soup.find_all("div", class_="job-card-container") # Note: class names can change
                
                if not job_cards: # Try fallback search for a different layout
                    job_cards = soup.find_all("div", class_="container-fluid")

                for card in job_cards:
                    title_elem = card.find("h3")
                    link_elem = card.find("a")
                    company_elem = card.find("div", class_="company-name") # Adjust based on actual HTML
                    
                    if title_elem and link_elem:
                        title = title_elem.text.strip()
                        if self.filter_job(title):
                            self.jobs.append({
                                "title": title,
                                "company": company_elem.text.strip() if company_elem else "Company Name Not Found",
                                "location": "India",
                                "url": "https://internshala.com" + link_elem['href'],
                                "tags": "India / Entry-Level",
                                "source": "Internshala",
                                "date": "Recent"
                            })
            logger.info("✅ Internshala completed.")
        except Exception as e: 
            logger.error(f"❌ Internshala failed: {e}")

    def scrape_remoteok(self):
        logger.info("🌐 Scraping RemoteOK (Filtering for India)...")
        try:
            res = requests.get("https://remoteok.com/api", headers=self.headers, timeout=15)
            data = res.json()
            for j in data[1:]: 
                # Only add if it's a tech role AND (mentions India OR is Worldwide Remote)
                if self.filter_job(j.get('position', '')):
                    loc = j.get('location', '')
                    if self.is_india_job(loc) or "Worldwide" in loc:
                        self.jobs.append({
                            "title": j.get('position'), "company": j.get('company'),
                            "location": loc, "url": j.get('url'),
                            "tags": j.get('tags', ''), "source": "RemoteOK", "date": j.get('date')
                        })
        except Exception as e: logger.error(f"❌ RemoteOK failed: {e}")

    def scrape_remotive(self):
        logger.info("🌐 Scraping Remotive (Filtering for India)...")
        try:
            res = requests.get("https://remotive.com/api/remote-jobs", headers=self.headers, timeout=15)
            data = res.json().get('jobs', [])
            for j in data:
                if self.filter_job(j.get('title', '')):
                    # Remotive is mostly global, we prioritize it as 'Remote'
                    self.jobs.append({
                        "title": j.get('title'), "company": j.get('company_name'),
                        "location": "Remote / Global", "url": j.get('url'),
                        "tags": j.get('category', ''), "source": "Remotive", "date": j.get('publication_date')
                    })
        except Exception as e: logger.error(f"❌ Remotive failed: {e}")

    def scrape_jobicy(self):
        logger.info("🌐 Scraping Jobicy Aggregator...")
        try:
            res = requests.get("https://jobicy.com/api/v2/remote-jobs", headers=self.headers, timeout=15)
            data = res.json().get('jobs', [])
            for j in data:
                if self.filter_job(j.get('title', '')):
                    self.jobs.append({
                        "title": j.get('title'), "company": j.get('company'),
                        "location": j.get('location', 'Remote'), "url": j.get('url'),
                        "tags": "Aggregated", "source": "Jobicy", "date": j.get('created_at')
                    })
        except Exception as e: logger.error(f"❌ Jobicy failed: {e}")

    def scrape_arbeitnow(self):
        logger.info("🌐 Scraping Arbeitnow...")
        try:
            res = requests.get("https://www.arbeitnow.com/api/job-board-api", headers=self.headers, timeout=15)
            data = res.json().get('data', [])
            for j in data:
                if self.filter_job(j.get('title', '')):
                    self.jobs.append({
                        "title": j.get('title'), "company": j.get('company', {}).get('name', 'Unknown'),
                        "location": j.get('location', 'Remote'), "url": j.get('url'),
                        "tags": "Tech", "source": "Arbeitnow", "date": j.get('created_at')
                    })
        except Exception as e: logger.error(f"❌ Arbeitnow failed: {e}")

    def scrape_weworkremotely(self):
        logger.info("🌐 Scraping WeWorkRemotely...")
        try:
            res = requests.get("https://weworkremotely.com/categories/remote-dev-jobs.rss", headers=self.headers, timeout=15)
            soup = BeautifulSoup(res.content, "xml")
            for item in soup.find_all("item"):
                title = item.find("title").text
                if self.filter_job(title):
                    self.jobs.append({
                        "title": title, "company": "Various", 
                        "location": "Remote", "url": item.find("link").text,
                        "tags": "WWR", "source": "WeWorkRemotely", "date": item.find("pubDate").text
                    })
        except Exception as e: logger.error(f"❌ WWR failed: {e}")

    def run_all(self):
        logger.info("🚀 Starting India-Focused scraping process...")
        self.scrape_internshala() # India specific
        self.scrape_remoteok()
        self.scrape_remotive()
        self.scrape_jobicy()
        self.scrape_arbeitnow()
        self.scrape_weworkremotely()
        
        # Deduplicate by URL
        seen_urls = set()
        unique_jobs = []
        for j in self.jobs:
            if j['url'] not in seen_urls:
                unique_jobs.append(j)
                seen_urls.add(j['url'])
        
        logger.info(f"✨ Successfully collected {len(unique_jobs)} unique jobs.")
        return unique_jobs
