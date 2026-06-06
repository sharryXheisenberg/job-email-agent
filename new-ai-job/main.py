import warnings
# This ignores ALL warnings, including the urllib3 dependency warning
warnings.filterwarnings("ignore")

import argparse
import sys
import os  # Added os import just in case it's needed for validate_env
from dotenv import load_dotenv
from scheduler.runner import start_scheduler, run_pipeline
from utils.logger import get_logger

load_dotenv()
logger = get_logger("Main")
# ... rest of your code


import argparse
import sys
from dotenv import load_dotenv
from scheduler.runner import start_scheduler, run_pipeline
from utils.logger import get_logger

load_dotenv()
logger = get_logger("Main")

def validate_env():
    required = ["GROQ_API_KEY", "SENDER_EMAIL", "SENDER_APP_PASSWORD", "RECIPIENT_EMAILS"]
    missing = [var for var in required if not os.getenv(var)]
    if missing:
        logger.error(f"Missing environment variables: {', '.join(missing)}")
        sys.exit(1)

if __name__ == "__main__":
    import os
    validate_env()
    
    parser = argparse.ArgumentParser(description="AI Job Email Agent")
    parser.add_argument("--now", action="store_true", help="Run once and exit")
    parser.add_argument("--test", action="store_true", help="Dry run (no email sent)")
    
    args = parser.parse_args()
    
    if args.test:
        run_pipeline(dry_run=True)
    elif args.now:
        run_pipeline(dry_run=False)
    else:
        start_scheduler()
