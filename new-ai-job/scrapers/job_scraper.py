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

# Pune-specific keywords — used to flag/prioritize Pune jobs from any source,
# and as the location filter for the 4 Pune-only job sites below.
PUNE_KEYWORDS = ["pune", "pimpri", "chinchwad", "hinjewadi", "hinjawadi", "wakad", "baner", "kothrud"]

# Phrases that signal an ENTRY-LEVEL role (0-2 years experience).
# Checked against title + any short description/snippet text we get from a source.
ENTRY_LEVEL_PATTERNS = [
    "fresher", "freshers", "entry level", "entry-level", "0-1 year", "0-2 year",
    "0 to 1 year", "0 to 2 year", "1-2 year", "1 to 2 year", "intern", "internship",
    "graduate", "graduate engineer trainer", "get", "trainee", "junior",
    "no experience", "0+ years", "1+ year", "associate engineer",
]

# Phrases that signal a SENIOR / too-experienced role — used to actively
# EXCLUDE jobs even if they otherwise match a target role keyword, since
# noisy aggregators (jobsavior, jobsora, apna) mix all experience levels
# together with no structured experience field to filter on.
SENIOR_EXCLUDE_PATTERNS = [
    "senior", "sr.", "sr ", "lead ", "principal", "staff engineer",
    "manager", "head of", "director", "vp ", "architect", "10+ years",
    "8+ years", "7+ years", "6+ years", "5+ years", "4+ years", "3+ years",
    "3-5 years", "5-8 years", "4-6 years", "minimum 5", "minimum 4", "minimum 3",
]


def is_entry_level(*texts):
    """
    Returns True if the combined text looks like an entry-level (0-2 yrs) role.
    Conservative: if we see an explicit senior/years-heavy marker, reject.
    If we see an explicit entry marker, accept. If neither is present, we
    can't tell from title alone — caller decides whether to keep or drop
    based on context (see usage below).
    """
    combined = " ".join(t for t in texts if t).lower()
    if any(p in combined for p in SENIOR_EXCLUDE_PATTERNS):
        return False
    if any(p in combined for p in ENTRY_LEVEL_PATTERNS):
        return True
    return None  # unknown — title gives no signal either way

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

    def is_pune_job(self, text):
        """Checks if a job description or location mentions Pune specifically."""
        if not text:
            return False
        return any(word in text.lower() for word in PUNE_KEYWORDS)

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

    # ------------------------------------------------------------------
    # SOURCE 10: JobSavior — Pune-specific listing page (best-effort HTML)
    # No public API. Server-rendered HTML, so static scraping CAN reach
    # it (unlike Naukri/Internshala), but markup/classes may shift over
    # time. Multiple selector fallbacks are tried before giving up.
    # ------------------------------------------------------------------
    def scrape_jobsavior_pune(self):
        logger.info("📍 Scraping JobSavior (Pune)...")
        added = 0
        try:
            url = "https://in.jobsavior.com/job-offers/pune"
            res = requests.get(url, headers=self.headers, timeout=15)
            if res.status_code != 200:
                logger.warning(f"   JobSavior returned HTTP {res.status_code}, skipping.")
                return
            soup = BeautifulSoup(res.text, "html.parser")

            cards = (soup.find_all("div", class_="job-item")
                      or soup.find_all("article")
                      or soup.find_all("div", class_="card"))

            if not cards:
                logger.warning("   JobSavior: no recognizable job cards found "
                                "(site markup may have changed). 0 jobs added.")
                return

            for card in cards:
                title_elem = card.find(["h2", "h3", "a"])
                if not title_elem:
                    continue
                title = title_elem.get_text(strip=True)
                snippet = card.get_text(" ", strip=True)

                if not self.filter_job(title):
                    continue
                entry_check = is_entry_level(title, snippet)
                if entry_check is False:
                    continue  # explicitly senior — skip

                link_elem = card.find("a")
                href = link_elem.get("href", "") if link_elem else ""
                if href and not href.startswith("http"):
                    href = "https://in.jobsavior.com" + href

                company_elem = card.find(["span", "div"], class_=lambda c: c and "company" in c.lower())

                self.jobs.append({
                    "title": title,
                    "company": company_elem.get_text(strip=True) if company_elem else "Unknown",
                    "location": "Pune, India",
                    "url": href,
                    "tags": "Pune / Entry-Level" if entry_check else "Pune",
                    "source": "JobSavior",
                    "date": "Recent",
                })
                added += 1
            logger.info(f"✅ JobSavior completed. {added} Pune jobs added.")
        except Exception as e:
            logger.warning(f"   JobSavior scraping failed: {e}")

    # ------------------------------------------------------------------
    # SOURCE 11: Jobsora — Pune-specific listing page (best-effort HTML)
    # ------------------------------------------------------------------
    def scrape_jobsora_pune(self):
        logger.info("📍 Scraping Jobsora (Pune)...")
        added = 0
        try:
            url = "https://in.jobsora.com/jobs-pune"
            res = requests.get(url, headers=self.headers, timeout=15)
            if res.status_code != 200:
                logger.warning(f"   Jobsora returned HTTP {res.status_code}, skipping.")
                return
            soup = BeautifulSoup(res.text, "html.parser")

            cards = (soup.find_all("div", class_="vacancy-item")
                      or soup.find_all("article")
                      or soup.find_all("div", class_="job-card"))

            if not cards:
                logger.warning("   Jobsora: no recognizable job cards found "
                                "(site markup may have changed). 0 jobs added.")
                return

            for card in cards:
                title_elem = card.find(["h2", "h3", "a"])
                if not title_elem:
                    continue
                title = title_elem.get_text(strip=True)
                snippet = card.get_text(" ", strip=True)

                if not self.filter_job(title):
                    continue
                entry_check = is_entry_level(title, snippet)
                if entry_check is False:
                    continue

                link_elem = card.find("a")
                href = link_elem.get("href", "") if link_elem else ""
                if href and not href.startswith("http"):
                    href = "https://in.jobsora.com" + href

                company_elem = card.find(["span", "div"], class_=lambda c: c and "company" in c.lower())

                self.jobs.append({
                    "title": title,
                    "company": company_elem.get_text(strip=True) if company_elem else "Unknown",
                    "location": "Pune, India",
                    "url": href,
                    "tags": "Pune / Entry-Level" if entry_check else "Pune",
                    "source": "Jobsora",
                    "date": "Recent",
                })
                added += 1
            logger.info(f"✅ Jobsora completed. {added} Pune jobs added.")
        except Exception as e:
            logger.warning(f"   Jobsora scraping failed: {e}")

    # ------------------------------------------------------------------
    # SOURCE 12: Naukri Fresher Jobs in Pune (BEST-EFFORT — no public API)
    # Naukri renders job listings via client-side JavaScript, so a plain
    # HTTP GET will not contain the job cards in most cases. This is kept
    # as a best-effort source consistent with scrape_naukri() above: if
    # it returns 0, that is expected, not a bug.
    # ------------------------------------------------------------------
    def scrape_naukri_fresher_pune(self):
        logger.info("📍 Scraping Naukri Fresher Jobs (Pune, best-effort)...")
        added = 0
        try:
            url = "https://www.naukri.com/fresher-jobs-in-pune"
            res = requests.get(url, headers=self.headers, timeout=15)
            if res.status_code != 200:
                logger.warning(f"   Naukri fresher-Pune returned HTTP {res.status_code} (likely blocked). Skipping.")
                return
            soup = BeautifulSoup(res.text, "html.parser")
            cards = soup.find_all("article", class_="jobTuple") or soup.find_all("div", class_="srp-jobtuple-wrapper")

            if not cards:
                logger.warning("   Naukri fresher-Pune: no job cards found in static HTML "
                                "(page renders via JavaScript — static scraping can't reach it, as expected).")
                return

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
                    "location": "Pune, India",
                    "url": title_elem.get("href", ""),
                    "tags": "Pune / Fresher",
                    "source": "Naukri-Fresher-Pune",
                    "date": "Recent",
                })
                added += 1
            logger.info(f"✅ Naukri fresher-Pune completed. {added} jobs added.")
        except Exception as e:
            logger.warning(f"   Naukri fresher-Pune scraping failed: {e}")

    # ------------------------------------------------------------------
    # SOURCE 13: Apna.co — Pune listing page (best-effort HTML)
    # Apna is server-rendered (confirmed reachable) but is a general
    # blue-collar + white-collar jobs board, so the role filter does
    # most of the work here to surface only SDE/data/analyst postings.
    # ------------------------------------------------------------------
    def scrape_apna_pune(self):
        logger.info("📍 Scraping Apna.co (Pune)...")
        added = 0
        try:
            url = "https://apna.co/jobs/jobs-in-pune"
            res = requests.get(url, headers=self.headers, timeout=15)
            if res.status_code != 200:
                logger.warning(f"   Apna.co returned HTTP {res.status_code}, skipping.")
                return
            soup = BeautifulSoup(res.text, "html.parser")

            # Apna job cards are typically anchor tags linking to /job/pune/<slug>-<id>
            links = soup.find_all("a", href=lambda h: h and "/job/pune/" in h)

            if not links:
                logger.warning("   Apna.co: no job links found "
                                "(site markup may have changed). 0 jobs added.")
                return

            for link in links:
                title = link.get_text(" ", strip=True)
                if not title:
                    continue
                if not self.filter_job(title):
                    continue
                entry_check = is_entry_level(title)
                if entry_check is False:
                    continue

                href = link.get("href", "")
                if href and not href.startswith("http"):
                    href = "https://apna.co" + href

                self.jobs.append({
                    "title": title,
                    "company": "See listing",
                    "location": "Pune, India",
                    "url": href,
                    "tags": "Pune / Entry-Level" if entry_check else "Pune",
                    "source": "Apna",
                    "date": "Recent",
                })
                added += 1
            logger.info(f"✅ Apna.co completed. {added} Pune jobs added.")
        except Exception as e:
            logger.warning(f"   Apna.co scraping failed: {e}")

    def run_all(self):
        logger.info("🚀 Starting India-Focused scraping process...")

        # India-specific / India-reliable sources first
        self.scrape_greenhouse()
        self.scrape_lever()
        self.scrape_internshala()
        self.scrape_naukri()

        # Pune-specific sources (new)
        self.scrape_jobsavior_pune()
        self.scrape_jobsora_pune()
        self.scrape_naukri_fresher_pune()
        self.scrape_apna_pune()

        # Global boards, hard-filtered for India relevance
        self.scrape_remoteok()
        self.scrape_remotive()
        self.scrape_jobicy()
        self.scrape_arbeitnow()
        self.scrape_weworkremotely()

        # ------------------------------------------------------------
        # ENTRY-LEVEL FILTER (0-2 years experience) — applied globally
        # across every source, not just the Pune-specific ones. We only
        # DROP a job when the title/snippet explicitly signals senior
        # experience (e.g. "Senior", "5+ years", "Lead"). Jobs with no
        # explicit experience signal either way are KEPT, since most
        # genuine SDE-I / Analyst / Intern postings don't always spell
        # out "0-2 years" in the title — being strict in the other
        # direction would wipe out most of the real entry-level supply.
        # ------------------------------------------------------------
        filtered_jobs = []
        senior_dropped = 0
        for j in self.jobs:
            check = is_entry_level(j.get('title', ''), j.get('tags', ''))
            if check is False:
                senior_dropped += 1
                continue
            filtered_jobs.append(j)
        logger.info(f"   🎯 Entry-level filter: dropped {senior_dropped} senior/experienced postings, "
                    f"kept {len(filtered_jobs)} entry-level or unspecified-experience jobs.")
        self.jobs = filtered_jobs

        # ------------------------------------------------------------
        # DEDUPLICATION — strengthened.
        # Primary key: URL (most reliable when present and not a generic
        # listing-page URL). Fallback key: normalized (title + company),
        # because some scraped sources (e.g. WeWorkRemotely "Various",
        # or a card with no href) can produce blank/duplicate URLs while
        # still being genuinely different postings, or genuinely the same
        # posting mirrored across two sources. Both keys must be unseen
        # for a job to be kept.
        # ------------------------------------------------------------
        seen_urls = set()
        seen_title_company = set()
        unique_jobs = []
        for j in self.jobs:
            url = (j.get('url') or '').strip().rstrip('/')
            title_key = (j.get('title') or '').strip().lower()
            company_key = (j.get('company') or '').strip().lower()
            combo_key = f"{title_key}::{company_key}"

            if url:
                if url in seen_urls:
                    continue
                seen_urls.add(url)
            # Even with a unique/blank URL, also guard against the same
            # title+company appearing twice across different sources.
            if combo_key in seen_title_company and title_key and company_key:
                continue
            seen_title_company.add(combo_key)
            unique_jobs.append(j)

        # Surface Pune jobs first, since that's this run's priority,
        # without dropping non-Pune jobs from the digest.
        unique_jobs.sort(key=lambda j: 0 if self.is_pune_job(j.get('location', '')) else 1)

        logger.info(f"✨ Successfully collected {len(unique_jobs)} unique jobs.")

        pune_count = sum(1 for j in unique_jobs if self.is_pune_job(j.get('location', '')))
        logger.info(f"   📍 Of which Pune-located: {pune_count}")

        # Source breakdown for visibility
        from collections import Counter
        counts = Counter(j['source'] for j in unique_jobs)
        for src, count in counts.items():
            logger.info(f"   📊 {src}: {count} jobs")

        return unique_jobs
