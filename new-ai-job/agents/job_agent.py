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
        if not jobs: return []
        
        # Prepare compact list for prompt
        compact_jobs = [{"idx": i, "t": j['title'], "c": j['company'], "tags": j['tags']} for i, j in enumerate(jobs)]
        
        # Updated prompt to be more strict about JSON format
        prompt = (
            "Rank these jobs for a fresh grad Software Engineer/Data Analyst. "
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
            
            # Extract the list from the 'jobs' key
            rank_list = results.get('jobs', []) if isinstance(results, dict) else []
            
            # Match AI results back to the original job objects
            for job in jobs:
                idx = jobs.index(job)
                match = next((r for r in rank_list if r.get('idx') == idx), {})
                job['rank'] = match.get('rank', 99)
                job['ai_summary'] = match.get('summary', "Interesting tech role.")
            
            return sorted(jobs, key=lambda x: x['rank'])
        except Exception as e:
            logger.error(f"AI Ranking failed: {e}")
            # Fallback: if AI fails, return original jobs with rank 99
            for j in jobs:
                j['rank'] = 99
                j['ai_summary'] = "AI summary unavailable."
            return jobs

    def generate_email_intro(self, jobs):
        try:
            top_jobs = [f"{j['title']} at {j['company']}" for j in jobs[:3]]
            prompt = f"Write a 2-sentence energetic intro for a job digest email featuring these roles: {', '.join(top_jobs)}. No emojis."
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}]
            )
            return completion.choices[0].message.content
        except Exception as e:
            logger.error(f"AI Intro generation failed: {e}")
            return "Here are the best tech job openings found for you today!"
