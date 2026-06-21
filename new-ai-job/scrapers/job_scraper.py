import requests
from bs4 import BeautifulSoup
from utils.logger import get_logger

logger = get_logger("Scraper")

# Expanded keywords for SDE and Data roles.
# Includes both "Developer" and "Engineer" variants since boards use them
# interchangeably (e.g. WeWorkRemotely posts "Backend Engineer", not "Backend Developer").
TARGET_ROLES = [
    "software engineer", "software developer", "sde", "sde i", "sde ii",
    "data analyst", "data engineer", "data scientist", "analyst",
    "backend developer", "backend engineer", "frontend developer", "frontend engineer",
    "full stack", "fullstack",
    "python developer", "python engineer", "java developer", "java engineer",
    "c++ developer", "node developer", "react developer",
    "machine learning", "ml engineer", "devops engineer",
    "qa engineer", "test engineer", "sde intern", "software intern",
    "engineering intern", "intern"
]

INDIA_KEYWORDS = [
    "india", "bangalore", "bengaluru", "hyderabad", "pune", "mumbai",
    "delhi", "noida", "gurgaon", "gurugram", "chennai", "kolkata",
    "ahmedabad", "jaipur", "remote india", "in-remote"
]

# Public Greenhouse/Lever job boards for companies with a real, verified India presence.
# These are FREE, official, public JSON APIs — no auth, no scraping fragility.
#
# IMPORTANT: The correct Greenhouse API host is "boards-api.greenhouse.io"
# (NOT "api.greenhouse.io" — that host doesn't serve this API and 404s every time).
#
# Board slugs are case-sensitive and must match the company's actual ATS board
# token, which is the path segment in their public job board URL:
#   https://boards.greenhouse.io/<token>  ->  token is the slug below
# Slugs below were verified live (June 2026) to have active India-based postings.
GREENHOUSE_BOARDS = [
    "thoughtworks",     # Bangalore + many India offices, huge SDE volume
    "twilio",           # Bengaluru office, SDE/data roles
    "truecaller",       # Bangalore, Mumbai, Gurgaon offices
    "payoneer",         # Bangalore, Gurugram offices
    "circleslife",      # Bangalore office
    "productiv",        # Bangalore office
    "purestorage",      # Bangalore office
    "memryx",           # Bangalore office
]

LEVER_BOARDS = [
    "meesho",       # India e-commerce giant, very high SDE/data hiring volume
    "fampay",       # Bengaluru fintech, SDE roles
    "stable-money1",  # Bengaluru fintech, SDE roles
]


class JobScraper:
    def __init__(self):
        self.jobs = []
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "application/json, text/html, */*",
        }

    def filter_job(self, title):
        if not title:
            return False
        return any(role.lower() in title.lower() for role in TARGET_ROLES)

    def is_india_job(self, text):
        """Checks if a job description or location mentions India."""
        if not text:
            return False
        return any(word in text.lower() for word in INDIA_KEYWORDS)

    # ------------------------------------------------------------------
    # SOURCE 1: Greenhouse public job board API (FREE, official, stable)
    # ------------------------------------------------------------------
    def scrape_greenhouse(self):
        logger.info("🇮🇳 Scraping Greenhouse boards (India tech companies)...")
        added = 0
        for board in GREENHOUSE_BOARDS:
            try:
                url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true"
                res = requests.get(url, headers=self.headers, timeout=15)
                if res.status_code != 200:
                    logger.warning(f"   Greenhouse board '{board}' returned HTTP {res.status_code}, skipping.")
                    continue
                data = res.json()
                all_jobs = data.get("jobs", [])
                board_added = 0
                for j in all_jobs:
                    title = j.get("title", "")
                    location = (j.get("location") or {}).get("name", "")
                    if not self.filter_job(title):
                        continue
                    if not self.is_india_job(location):
                        continue
                    self.jobs.append({
                        "title": title,
                        "company": board.capitalize(),
                        "location": location or "India",
                        "url": j.get("absolute_url", ""),
                        "tags": "Greenhouse ATS",
                        "source": "Greenhouse",
                        "date": j.get("updated_at", "")[:10] if j.get("updated_at") else "Recent",
                    })
                    added += 1
                    board_added += 1
                logger.info(f"   ✓ Greenhouse '{board}': {len(all_jobs)} total postings, {board_added} matched filters.")
            except Exception as e:
                logger.warning(f"   Greenhouse board '{board}' failed: {e}")
        logger.info(f"✅ Greenhouse completed. {added} India jobs added.")

    # ------------------------------------------------------------------
    # SOURCE 2: Lever public job board API (FREE, official, stable)
    # ------------------------------------------------------------------
    def scrape_lever(self):
        logger.info("🇮🇳 Scraping Lever boards (India tech companies)...")
        added = 0
        for board in LEVER_BOARDS:
            try:
                url = f"https://api.lever.co/v0/postings/{board}?mode=json"
                res = requests.get(url, headers=self.headers, timeout=15)
                if res.status_code != 200:
                    logger.warning(f"   Lever board '{board}' returned HTTP {res.status_code}, skipping.")
                    continue
                data = res.json()
                board_added = 0
                for j in data:
                    title = j.get("text", "")
                    location = (j.get("categories") or {}).get("location", "")
                    if not self.filter_job(title):
                        continue
                    if not self.is_india_job(location):
                        continue
                    self.jobs.append({
                        "title": title,
                        "company": board,
                        "location": location or "India",
                        "url": j.get("hostedUrl", ""),
                        "tags": "Lever ATS",
                        "source": "Lever",
                        "date": "Recent",
                    })
                    added += 1
                    board_added += 1
                logger.info(f"   ✓ Lever '{board}': {len(data)} total postings, {board_added} matched filters.")
            except Exception as e:
                logger.warning(f"   Lever board '{board}' failed: {e}")
        logger.info(f"✅ Lever completed. {added} India jobs added.")

    # ------------------------------------------------------------------
    # SOURCE 3: Naukri.com (BEST-EFFORT — no public API, HTML scrape)
    # Naukri renders listings client-side via JS in many cases and
    # actively rate-limits/blocks non-browser traffic. This is kept as
    # a best-effort source: if it returns 0, that's expected sometimes,
    # not a bug. It will never crash the pipeline.
    # ------------------------------------------------------------------
    def scrape_naukri(self):
        logger.info("🇮🇳 Scraping Naukri (best-effort, may yield 0 results)...")
        added = 0
        try:
            searches = ["software-engineer-jobs", "data-analyst-jobs", "sde-jobs"]
            for slug in searches:
                url = f"https://www.naukri.com/{slug}"
                res = requests.get(url, headers=self.headers, timeout=15)
                if res.status_code != 200:
                    logger.warning(f"   Naukri '{slug}' returned HTTP {res.status_code} (likely blocked). Skipping.")
                    continue
                soup = BeautifulSoup(res.text, "html.parser")
                # Naukri's job cards live under article tags with class 'jobTuple' (subject to change)
                cards = soup.find_all("article", class_="jobTuple") or soup.find_all("div", class_="srp-jobtuple-wrapper")
                if not cards:
                    logger.warning(f"   Naukri '{slug}': no job cards found in HTML "
                                    "(page likely renders via JavaScript — static scraping can't reach it).")
                    continue
                for card in cards:
                    title_elem = card.find("a", class_="title")
                    company_elem = card.find("a", class_="comp-name")
                    if not title_elem:
                        continue
                    title = title_elem.text.strip()
                    if not self.filter_job(title):
                        continue
                    self.jobs.append({
                        "title": title,
                        "company": company_elem.text.strip() if company_elem else "Unknown",
                        "location": "India",
                        "url": title_elem.get("href", ""),
                        "tags": "Naukri",
                        "source": "Naukri",
                        "date": "Recent",
                    })
                    added += 1
        except Exception as e:
            logger.warning(f"   Naukri scraping failed entirely: {e}")
        logger.info(f"✅ Naukri completed. {added} jobs added (best-effort source).")

    # ------------------------------------------------------------------
    # SOURCE 4: Internshala — FIXED with honest failure reporting.
    # Internshala returns HTTP 403 to non-browser requests (confirmed).
    # This is kept so the door is open if Internshala relaxes blocking,
    # or if you plug in a paid scraping proxy later.
    # ------------------------------------------------------------------
    def scrape_internshala(self):
        logger.info("🇮🇳 Scraping Internshala (India Specific)...")
        added = 0
        try:
            categories = ["software-engineering", "data-science"]
            for cat in categories:
                url = f"https://internshala.com/jobs/{cat}"
                res = requests.get(url, headers=self.headers, timeout=15)
                if res.status_code == 403:
                    logger.warning(
                        f"   Internshala blocked the request (HTTP 403) for '{cat}'. "
                        "Internshala actively blocks scrapers — this is expected, not a bug. "
                        "No free public API exists for Internshala."
                    )
                    continue
                if res.status_code != 200:
                    logger.warning(f"   Internshala '{cat}' returned HTTP {res.status_code}, skipping.")
                    continue

                soup = BeautifulSoup(res.text, "html.parser")
                job_cards = soup.find_all("div", class_="individual_internship") \
                    or soup.find_all("div", class_="job-card-container") \
                    or soup.find_all("div", class_="container-fluid")

                if not job_cards:
                    logger.warning(f"   Internshala '{cat}': page loaded but no recognizable job cards "
                                    "(site markup may have changed).")
                    continue

                for card in job_cards:
                    title_elem = card.find("h3") or card.find("h4")
                    link_elem = card.find("a")
                    company_elem = card.find("p", class_="company-name") or card.find("div", class_="company-name")

                    if title_elem and link_elem:
                        title = title_elem.text.strip()
                        if self.filter_job(title):
                            href = link_elem.get("href", "")
                            self.jobs.append({
                                "title": title,
                                "company": company_elem.text.strip() if company_elem else "Company Name Not Found",
                                "location": "India",
                                "url": href if href.startswith("http") else f"https://internshala.com{href}",
                                "tags": "India / Entry-Level",
                                "source": "Internshala",
                                "date": "Recent",
                            })
                            added += 1
            logger.info(f"✅ Internshala completed. {added} jobs added.")
        except Exception as e:
            logger.error(f"❌ Internshala failed: {e}")

    # ------------------------------------------------------------------
    # SOURCE 5-9: Global boards, hard-filtered for India relevance
    # ------------------------------------------------------------------
    def scrape_remoteok(self):
        logger.info("🌐 Scraping RemoteOK (Filtering for India)...")
        added = 0
        try:
            res = requests.get("https://remoteok.com/api", headers=self.headers, timeout=15)
            data = res.json()
            for j in data[1:]:
                if self.filter_job(j.get('position', '')):
                    loc = j.get('location', '') or ""
                    tags = j.get('tags', [])
                    tags_str = ", ".join(tags) if isinstance(tags, list) else str(tags)
                    # RemoteOK convention: an EMPTY location field means "open to anywhere"
                    # (not "exclude this job") — only explicit non-India regions should be excluded.
                    is_open_remote = (not loc.strip()) or "worldwide" in loc.lower() or "anywhere" in loc.lower()
                    if self.is_india_job(loc) or is_open_remote:
                        self.jobs.append({
                            "title": j.get('position'), "company": j.get('company'),
                            "location": loc or "Worldwide Remote", "url": j.get('url'),
                            "tags": tags_str, "source": "RemoteOK", "date": j.get('date')
                        })
                        added += 1
            logger.info(f"✅ RemoteOK completed. {added} jobs added.")
        except Exception as e:
            logger.error(f"❌ RemoteOK failed: {e}")

    def scrape_remotive(self):
        logger.info("🌐 Scraping Remotive (Filtering for India)...")
        added = 0
        try:
            res = requests.get("https://remotive.com/api/remote-jobs", headers=self.headers, timeout=15)
            data = res.json().get('jobs', [])
            for j in data:
                if self.filter_job(j.get('title', '')):
                    loc = j.get('candidate_required_location', '')
                    if self.is_india_job(loc) or "worldwide" in loc.lower() or "anywhere" in loc.lower():
                        self.jobs.append({
                            "title": j.get('title'), "company": j.get('company_name'),
                            "location": loc or "Remote / Global", "url": j.get('url'),
                            "tags": j.get('category', ''), "source": "Remotive",
                            "date": j.get('publication_date')
                        })
                        added += 1
            logger.info(f"✅ Remotive completed. {added} jobs added.")
        except Exception as e:
            logger.error(f"❌ Remotive failed: {e}")

    def scrape_jobicy(self):
        logger.info("🌐 Scraping Jobicy Aggregator (Filtering for India)...")
        added = 0
        try:
            res = requests.get("https://jobicy.com/api/v2/remote-jobs", headers=self.headers, timeout=15)
            data = res.json().get('jobs', [])
            for j in data:
                if self.filter_job(j.get('title', '')):
                    loc = (j.get('location') or "Remote").strip() or "Remote"
                    # "Remote" with no further qualifier is conventionally open to any country,
                    # including India — don't exclude it just because it doesn't say "worldwide".
                    is_open_remote = loc.lower() in ("remote", "") or "worldwide" in loc.lower() or "anywhere" in loc.lower()
                    if self.is_india_job(loc) or is_open_remote:
                        self.jobs.append({
                            "title": j.get('title'), "company": j.get('company'),
                            "location": loc, "url": j.get('url'),
                            "tags": "Aggregated", "source": "Jobicy", "date": j.get('created_at')
                        })
                        added += 1
            logger.info(f"✅ Jobicy completed. {added} jobs added.")
        except Exception as e:
            logger.error(f"❌ Jobicy failed: {e}")

    def scrape_arbeitnow(self):
        logger.info("🌐 Scraping Arbeitnow (Filtering for India)...")
        added = 0
        try:
            res = requests.get("https://www.arbeitnow.com/api/job-board-api", headers=self.headers, timeout=15)
            data = res.json().get('data', [])
            for j in data:
                if self.filter_job(j.get('title', '')):
                    loc = j.get('location', 'Remote') or "Remote"
                    is_remote = j.get('remote', False)
                    if self.is_india_job(loc) or is_remote:
                        self.jobs.append({
                            "title": j.get('title'),
                            "company": j.get('company', {}).get('name', 'Unknown') if isinstance(j.get('company'), dict) else j.get('company_name', 'Unknown'),
                            "location": loc, "url": j.get('url'),
                            "tags": "Tech", "source": "Arbeitnow", "date": j.get('created_at')
                        })
                        added += 1
            logger.info(f"✅ Arbeitnow completed. {added} jobs added.")
        except Exception as e:
            logger.error(f"❌ Arbeitnow failed: {e}")

    def scrape_weworkremotely(self):
        logger.info("🌐 Scraping WeWorkRemotely...")
        added = 0
        try:
            res = requests.get("https://weworkremotely.com/categories/remote-dev-jobs.rss", headers=self.headers, timeout=15)
            soup = BeautifulSoup(res.content, "xml")
            for item in soup.find_all("item"):
                title = item.find("title").text
                if self.filter_job(title):
                    self.jobs.append({
                        "title": title, "company": "Various",
                        "location": "Remote (Worldwide)", "url": item.find("link").text,
                        "tags": "WWR", "source": "WeWorkRemotely", "date": item.find("pubDate").text
                    })
                    added += 1
            logger.info(f"✅ WeWorkRemotely completed. {added} jobs added.")
        except Exception as e:
            logger.error(f"❌ WWR failed: {e}")

    def run_all(self):
        logger.info("🚀 Starting India-Focused scraping process...")

        # India-specific / India-reliable sources first
        self.scrape_greenhouse()
        self.scrape_lever()
        self.scrape_internshala()
        self.scrape_naukri()

        # Global boards, hard-filtered for India relevance
        self.scrape_remoteok()
        self.scrape_remotive()
        self.scrape_jobicy()
        self.scrape_arbeitnow()
        self.scrape_weworkremotely()

        # Deduplicate by URL
        seen_urls = set()
        unique_jobs = []
        for j in self.jobs:
            url = j.get('url', '')
            if url and url not in seen_urls:
                unique_jobs.append(j)
                seen_urls.add(url)

        logger.info(f"✨ Successfully collected {len(unique_jobs)} unique jobs.")

        # Source breakdown for visibility
        from collections import Counter
        counts = Counter(j['source'] for j in unique_jobs)
        for src, count in counts.items():
            logger.info(f"   📊 {src}: {count} jobs")

        return unique_jobs
