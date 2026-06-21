import json
from groq import Groq
from utils.logger import get_logger

logger = get_logger("AIAgent")


class JobAgent:
    def __init__(self, api_key):
        self.client = Groq(api_key=api_key)
        # THIS MUST BE llama-3.1-8b-instant
        self.model = "llama-3.1-8b-instant"

    def rank_and_summarise(self, jobs):
        if not jobs:
            return []

        # Prepare compact list for prompt
        compact_jobs = [
            {"idx": i, "t": j.get('title', ''), "c": j.get('company', ''), "tags": j.get('tags', '')}
            for i, j in enumerate(jobs)
        ]

        prompt = (
            "Rank these jobs for a fresh grad Software Engineer/Data Analyst based in India. "
            "Prioritize India-based and India-eligible remote roles slightly higher when relevant. "
            "Return ONLY a JSON object with a key 'jobs' containing an array of objects. "
            "Each object must have 'idx' (int), 'rank' (int), and 'summary' (string, max 15 words). "
            f"\n\nJobs: {json.dumps(compact_jobs)}"
        )

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            results = json.loads(completion.choices[0].message.content)
            rank_list = results.get('jobs', []) if isinstance(results, dict) else []

            # Build a lookup by idx instead of jobs.index(job), which breaks
            # silently when two jobs are equal/duplicate dicts.
            rank_map = {item.get('idx'): item for item in rank_list if 'idx' in item}

            for i, job in enumerate(jobs):
                match = rank_map.get(i, {})
                job['rank'] = match.get('rank', 99)
                job['ai_summary'] = match.get('summary', "Interesting tech role.")

            return sorted(jobs, key=lambda x: x.get('rank', 99))
        except Exception as e:
            logger.error(f"AI Ranking failed: {e}")
            # Fallback: if AI fails, return original jobs with rank 99
            for j in jobs:
                j['rank'] = 99
                j['ai_summary'] = "AI summary unavailable."
            return jobs

    def generate_email_intro(self, jobs):
        if not jobs:
            return "No new job openings were found today. Check back tomorrow!"
        try:
            top_jobs = [f"{j.get('title','')} at {j.get('company','')}" for j in jobs[:3]]
            prompt = (
                f"Write a 2-sentence energetic intro for a job digest email for an India-based "
                f"job seeker, featuring these roles: {', '.join(top_jobs)}. No emojis."
            )
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}]
            )
            return completion.choices[0].message.content
        except Exception as e:
            logger.error(f"AI Intro generation failed: {e}")
            return "Here are the best tech job openings found for you today!"
