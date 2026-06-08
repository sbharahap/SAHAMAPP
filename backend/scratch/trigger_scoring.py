import asyncio
from backend.workers import run_scoring_job

if __name__ == "__main__":
    print("🚀 Triggering weekly scoring job...")
    asyncio.run(run_scoring_job())
    print("🏁 Scoring job trigger complete.")
