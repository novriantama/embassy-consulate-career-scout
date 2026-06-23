import asyncio
import os
import sys
from google.antigravity import Agent
from tools import (
    read_user_resume, 
    search_active_postings, 
    send_local_alert, 
    send_notification_email, 
    save_application_log
)
from config import monitor_config, matcher_config, drafter_config

async def run_agent_step(config, prompt, step_name):
    """Runs an agent step with structured output, retrying on 429 Rate Limits at any stage.
    """
    delay = 15
    max_retries = 3
    for attempt in range(max_retries):
        try:
            async with Agent(config=config) as agent:
                response = await agent.chat(prompt)
                return await response.structured_output()
        except Exception as e:
            err_msg = str(e).lower()
            if "429" in err_msg or "quota" in err_msg or "resource_exhausted" in err_msg:
                print(f"⚠️ [Rate Limit 429] hit in {step_name}. Waiting {delay}s before retrying (Attempt {attempt + 1}/{max_retries})...")
                await asyncio.sleep(delay)
                delay *= 1.5
            else:
                raise e
    # Final attempt
    async with Agent(config=config) as agent:
        response = await agent.chat(prompt)
        return await response.structured_output()

async def scan_single_portal(url: str, resume_path: str):
    """Scans and evaluates a single embassy job portal URL.
    """
    print(f"\n==================================================")
    print(f"🔎 Scanning Portal: {url}")
    print(f"==================================================")
    
    # Step 1: Monitor Agent gathers job details
    print("🤖 Spawning Monitor Agent to extract job posting details...")
    job_details = await run_agent_step(
        monitor_config, 
        f"Scrape and extract job details from this page: {url}", 
        "Monitor Agent"
    )
        
    if not job_details:
        print("⚠️ Could not extract details or page structure is unreadable.")
        return
        
    embassy_name = job_details.get("embassy_name", "Unknown Embassy")
    job_title = job_details.get("job_title", "Unknown Position")
    
    if not job_details.get("is_embassy_local_staff"):
        print(f"ℹ️ [{embassy_name}] Opening found for '{job_title}', but it is not a 'Local Staff' position. Skipping.")
        return
        
    print(f"✅ Active Local Staff job found!")
    print(f"   Embassy:  {embassy_name}")
    print(f"   Position: {job_title}")
    print(f"   Deadline: {job_details.get('application_deadline', 'Not specified')}")
    print(f"   Email:    {job_details.get('contact_email', 'None found')}")

    # Read candidate resume
    resume_text = read_user_resume(resume_path)
    
    # Introduce small delay to respect API Rate Limits (Free Tier)
    print("⏳ Waiting to respect API rate limits...")
    await asyncio.sleep(4)
    
    # Step 2: Matcher Agent evaluates candidates against requirements
    print("\n🤖 Spawning Matcher Agent to assess candidate fit...")
    match_results = await run_agent_step(
        matcher_config,
        f"Compare this resume against the job requirements.\n\n"
        f"Job Requirements: {job_details.get('requirements', [])}\n\n"
        f"Candidate Resume:\n{resume_text}",
        "Matcher Agent"
    )
        
    if not match_results:
        print("⚠️ Matcher agent failed to produce structured outputs.")
        return
        
    fit_score = match_results.get("fit_score", 0)
    strengths = match_results.get("matching_strengths", [])
    print(f"📊 Candidate Fit Assessment:")
    print(f"   Fit Score: {fit_score}/100")
    print(f"   Strengths: {', '.join(strengths)}")
    
    # Check suitability threshold
    threshold = int(os.getenv("AUTO_APPLY_THRESHOLD", "85"))
    auto_apply_enabled = os.getenv("AUTO_APPLY_ENABLED", "False").lower() == "true"
    
    if fit_score >= threshold:
        print(f"🌟 Suitable Match Found! (Fit score {fit_score}% >= threshold {threshold}%)")
        
        # Introduce small delay to respect API Rate Limits (Free Tier)
        print("⏳ Waiting to respect API rate limits...")
        await asyncio.sleep(4)
        
        # Step 3: Drafter Agent drafts formal diplomatic cover letter
        print("🤖 Spawning Drafter Agent to write application email...")
        email_draft = await run_agent_step(
            drafter_config,
            f"Write a formal diplomatic application for the position of '{job_title}' "
            f"at '{embassy_name}'. The candidate has these key strengths: {strengths}.",
            "Drafter Agent"
        )
            
        if not email_draft:
            print("⚠️ Drafter agent failed to draft cover email.")
            return
            
        subject = email_draft.get("email_subject", f"Job Application: {job_title}")
        body = email_draft.get("email_body", "")
        
        # 1. Trigger Native Mac OS Notification Banner
        alert_msg = f"Found a suitable role: {job_title} at {embassy_name} ({fit_score}% match)!"
        send_local_alert("Diplomatic Career Scout", alert_msg)
        
        # 2. Save a draft copy to user's desktop
        desktop_save_path = os.path.expanduser(f"~/Desktop/draft_email_{embassy_name.replace(' ', '_')}.txt")
        try:
            with open(desktop_save_path, "w", encoding="utf-8") as f:
                f.write(f"Subject: {subject}\nRecipient: {job_details.get('contact_email', 'N/A')}\n\n{body}")
            print(f"💾 Draft application letter saved to Desktop: {desktop_save_path}")
        except Exception as e:
            print(f"⚠️ Could not write draft to Desktop: {str(e)}")

        # 3. Send Notification Email to user
        notification_body = (
            f"Hello,\n\n"
            f"The Diplomatic Career Scout found a suitable job posting:\n"
            f"Embassy: {embassy_name}\n"
            f"Position: {job_title}\n"
            f"Fit Score: {fit_score}/100\n"
            f"Match Strengths: {', '.join(strengths)}\n\n"
            f"A draft email has been prepared and saved to your Desktop.\n"
            f"Link to listing: {url}"
        )
        print("✉️ Sending alert notification email to you...")
        send_notification_email(
            subject=f"[Scout Match] {job_title} at {embassy_name}",
            body=notification_body
        )
        
        # 4. Handle Automatic Resume Submission
        contact_email = job_details.get("contact_email")
        if auto_apply_enabled:
            if contact_email:
                print(f"🚀 Auto-Apply is Enabled! Sending application resume to {contact_email}...")
                send_result = send_notification_email(
                    subject=subject,
                    body=body,
                    recipient=contact_email,
                    attachment_path=resume_path
                )
                print(f"📬 Application status: {send_result}")
                save_application_log(job_title, embassy_name, f"Auto-applied: {send_result}", fit_score, url)
            else:
                print("⚠️ Auto-apply enabled, but no application email address was found on the page.")
                save_application_log(job_title, embassy_name, "Matched (Auto-apply skipped: no email)", fit_score, url)
        else:
            print("ℹ️ Auto-apply is disabled in .env. Skipping submission step.")
            save_application_log(job_title, embassy_name, "Matched (Draft saved)", fit_score, url)
            
    else:
        print(f"❌ Candidate fit score ({fit_score}%) is below suitability threshold ({threshold}%). Skipping.")
        save_application_log(job_title, embassy_name, "Scanned (Below threshold)", fit_score, url)

async def main():
    print("==================================================")
    print("🚀 Starting Global Diplomatic Career Scout scans...")
    print("==================================================")
    
    search_keyword = sys.argv[1] if len(sys.argv) > 1 else "staf setempat"
    resume_path = sys.argv[2] if len(sys.argv) > 2 else "resume.txt"
    
    if not os.path.exists(resume_path):
        print(f"❌ Resume file not found at: {resume_path}")
        print("   Please create a resume or place it in the working directory.")
        return
        
    # Step 0: Search for active career portals globally
    print(f"🔍 Searching for Indonesian embassy portals with keyword: '{search_keyword}'...")
    portals = search_active_postings(search_keyword)
    
    # Handling fallback cases if no portals returned
    if not portals:
        print("💡 No portals discovered. Falling back to pre-configured test URL...")
        portals = ["https://kemlu.go.id/singapore/id/pages/karir"]
        
    print(f"📌 Discovered {len(portals)} candidate portal URLs to scan.")
    
    for i, url in enumerate(portals):
        try:
            if i > 0:
                print("⏳ Waiting to respect API rate limits...")
                await asyncio.sleep(6)
            await scan_single_portal(url, resume_path)
        except Exception as e:
            print(f"💥 Critical error scanning portal {url}: {str(e)}")
            
    print("\n==================================================")
    print("🏁 Scout Scanning Completed. Logs saved to applications_log.json.")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(main())
