import asyncio
import os
import sys
from google.antigravity import Agent
from tools import read_user_resume, search_embassy_portals
from config import monitor_config, matcher_config, drafter_config

async def run_scout(search_keyword: str, resume_path: str):
    print("🚀 Triggering Diplomatic Career Scout...")

    # Step 0: Search for the correct embassy career page
    print(f"\n🔍 Step 0: Searching for portals matching keyword: '{search_keyword}'...")
    portals = search_embassy_portals(search_keyword)
    if not portals or "Search error" in portals[0]:
        print(f"❌ Failed to find embassy portals or search was blocked: {portals}")
        print("💡 Outgoing network might be disabled or connection refused. Falling back to default URL: https://kemlu.go.id/singapore/id/pages/karir")
        target_url = "https://kemlu.go.id/singapore/id/pages/karir"
    else:
        target_url = portals[0]
        
    print(f"📌 Target Portal URL: {target_url}")

    # Step 1: Monitor Agent checks the portal
    print("\n🔍 Step 1: Spawning Monitor Agent to check portal...")
    async with Agent(config=monitor_config) as monitor_agent:
        response = await monitor_agent.chat(f"Scrape and check this portal: {target_url}")
        job_details = await response.structured_output()
    
    if not job_details or not job_details.get("is_embassy_local_staff"):
        print("❌ No 'Local Staff' openings found on the portal. Terminating workflow.")
        return

    print(f"✅ Found local staff job: {job_details['job_title']} (Deadline: {job_details['application_deadline']})")

    # Step 2: Matcher Agent reads resume and job requirements
    print("\n📊 Step 2: Spawning Matcher Agent to compare with resume...")
    
    if not os.path.exists(resume_path):
        print(f"⚠️ Resume not found at {resume_path}. Please create a sample resume first.")
        return
        
    resume_text = read_user_resume(resume_path)
    
    async with Agent(config=matcher_config) as matcher_agent:
        response = await matcher_agent.chat(
            f"Job requirements: {job_details['requirements']}\n\n"
            f"User Resume:\n{resume_text}"
        )
        match_results = await response.structured_output()

    print(f"ℹ️ Fit Score: {match_results['fit_score']}/100")
    print(f"ℹ️ Strengths: {', '.join(match_results['matching_strengths'])}")

    # Step 3: Drafter Agent drafts and saves the email
    print("\n✍️ Step 3: Spawning Drafter Agent to write application email...")
    async with Agent(config=drafter_config) as drafter_agent:
        response = await drafter_agent.chat(
            f"Draft a diplomatic application email for the '{job_details['job_title']}' position.\n"
            f"Emphasize these 3 key strengths: {match_results['matching_strengths']}.\n"
            f"Ensure to save the output."
        )
        final_draft = await response.structured_output()
        
    print(f"\n🎉 Workflow complete! {final_draft['save_status']}")

if __name__ == "__main__":
    keyword = sys.argv[1] if len(sys.argv) > 1 else "KBRI Singapore local staff karir"
    resume = sys.argv[2] if len(sys.argv) > 2 else "resume.txt"
    
    # Run the async pipeline
    asyncio.run(run_scout(keyword, resume))
