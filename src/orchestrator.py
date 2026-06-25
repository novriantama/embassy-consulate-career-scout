import asyncio
import os
import sys
import json
from openai import AsyncOpenAI
from src.tools import (
    read_user_resume, 
    search_active_postings, 
    send_local_alert, 
    send_notification_email, 
    scrape_kbri_portal
)
from src.config import monitor_config, matcher_config, drafter_config
from src.utils.logger import save_application_log
from src.utils.env import load_env_variables

# Load environment configurations
load_env_variables()

# Initialize the OpenAI compatible client
api_key = os.getenv("LLM_API_KEY", "ollama")
base_url = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
model_name = os.getenv("LLM_MODEL", "qwen2.5")

client = AsyncOpenAI(
    api_key=api_key,
    base_url=base_url
)

# Cumulative token usage session state
SESSION_USAGE = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

async def run_agent_step(config, prompt, step_name):
    """Runs an agent step with structured output using Qwen via OpenAI compatible API.
    Retries on rate limits or API connection errors.
    """
    system_instructions = config["system_instructions"]
    response_schema = config["response_schema"]
    
    delay = 5
    max_retries = 3
    
    for attempt in range(max_retries + 1):
        try:
            try:
                # Try OpenAI structured outputs first (Beta parse endpoint)
                response = await client.beta.chat.completions.parse(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system_instructions},
                        {"role": "user", "content": prompt}
                    ],
                    response_format=response_schema
                )
                usage = response.usage
                if usage:
                    SESSION_USAGE["prompt_tokens"] += usage.prompt_tokens
                    SESSION_USAGE["completion_tokens"] += usage.completion_tokens
                    SESSION_USAGE["total_tokens"] += usage.total_tokens
                    print(f"   [LLM Usage] Prompt: {usage.prompt_tokens} t | Completion: {usage.completion_tokens} t | Total: {usage.total_tokens} t")
                parsed = response.choices[0].message.parsed
                if parsed is not None:
                    return parsed.model_dump()
            except Exception as parse_err:
                # Fallback to standard json_object with manual validation
                schema_json = json.dumps(response_schema.model_json_schema(), indent=2)
                fallback_system = (
                    f"{system_instructions}\n\n"
                    f"CRITICAL: You must return a JSON object conforming exactly to this JSON schema:\n"
                    f"{schema_json}"
                )
                response = await client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": fallback_system},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"}
                )
                usage = response.usage
                if usage:
                    SESSION_USAGE["prompt_tokens"] += usage.prompt_tokens
                    SESSION_USAGE["completion_tokens"] += usage.completion_tokens
                    SESSION_USAGE["total_tokens"] += usage.total_tokens
                    print(f"   [LLM Usage] Prompt: {usage.prompt_tokens} t | Completion: {usage.completion_tokens} t | Total: {usage.total_tokens} t")
                content = response.choices[0].message.content
                parsed_json = json.loads(content)
                validated = response_schema.model_validate(parsed_json)
                return validated.model_dump()
                
        except Exception as e:
            err_msg = str(e).lower()
            is_retryable = any(code in err_msg for code in ["429", "503", "quota", "rate limit", "resource_exhausted"])
            if is_retryable and attempt < max_retries:
                print(f"⚠️ [LLM Error] hit in {step_name}: {str(e)}. Waiting {delay}s before retrying (Attempt {attempt + 1}/{max_retries})...")
                await asyncio.sleep(delay)
                delay *= 1.5
            else:
                print(f"❌ [LLM Error] in {step_name}: {str(e)}")
                raise e

async def scan_single_portal(url: str, resume_path: str):
    """Scans and evaluates a single embassy job portal URL.
    """
    print(f"\n==================================================")
    print(f"🔎 Scanning Portal: {url}")
    print(f"==================================================")
    
    # Pre-scrape raw text in python
    print("🌐 Scraping portal content...")
    scraped_text = scrape_kbri_portal(url)
    
    if not scraped_text or scraped_text.startswith("Error"):
        print(f"⚠️ Failed to scrape portal content: {scraped_text}")
        return
        
    # Skip generic/blank pages (less than 150 characters cannot contain a real job posting)
    if len(scraped_text.strip()) < 150:
        print(f"⚠️ Page content is too short to contain a job posting ({len(scraped_text.strip())} chars). Skipping.")
        return
        
    # Step 1: Monitor Agent gathers job details
    print("🤖 Spawning Monitor Agent to extract job posting details...")
    job_details = await run_agent_step(
        monitor_config, 
        f"Analyze the following scraped text and extract job details:\n\n{scraped_text}", 
        "Monitor Agent"
    )
        
    if not job_details:
        print("⚠️ Could not extract details or page structure is unreadable.")
        return
        
    embassy_name = job_details.get("embassy_name", "Unknown Embassy")
    job_title = job_details.get("job_title", "Unknown Position")
    
    if not job_details.get("is_embassy_staff"):
        print(f"ℹ️ [{embassy_name}] Opening found for '{job_title}', but it is not a 'Staff' or 'Pegawai' position. Skipping.")
        return
        
    print(f"✅ Active Staff/Pegawai job found!")
    print(f"   Embassy:  {embassy_name}")
    print(f"   Position: {job_title}")
    print(f"   Deadline: {job_details.get('application_deadline', 'Not specified')}")
    print(f"   Email:    {job_details.get('contact_email', 'None found')}")

    # Read candidate resume
    resume_text = read_user_resume(resume_path)
    
    # Introduce small delay to respect API Rate Limits if any
    print("⏳ Waiting before next step...")
    await asyncio.sleep(2)
    
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
    
    # Construct base notification body for all found jobs
    requirements_str = "\n".join(f"- {req}" for req in job_details.get("requirements", []))
    notification_body = (
        f"Hello,\n\n"
        f"The Diplomatic Career Scout found an active job opening:\n\n"
        f"Embassy/Consulate: {embassy_name}\n"
        f"Position:          {job_title}\n"
        f"Deadline:          {job_details.get('application_deadline', 'Not specified')}\n"
        f"Link to job:       {url}\n\n"
        f"Job Description / Requirements:\n"
        f"{requirements_str}\n\n"
        f"📊 Candidate Fit Assessment:\n"
        f"Fit Score: {fit_score}/100\n"
        f"Match Strengths: {', '.join(strengths)}\n"
    )
    
    if fit_score >= threshold:
        print(f"🌟 Suitable Match Found! (Fit score {fit_score}% >= threshold {threshold}%)")
        
        # Introduce small delay to respect API Rate Limits if any
        print("⏳ Waiting before next step...")
        await asyncio.sleep(2)
        
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
            notification_body += "\n⚠️ (Drafting agent failed to generate formal cover letter. Only scan alert is sent.)"
            print("✉️ Sending alert notification email to you...")
            send_notification_email(
                subject=f"[Scout Found] {job_title} at {embassy_name} ({fit_score}% Fit)",
                body=notification_body
            )
            save_application_log(job_title, embassy_name, "Matched (Drafter failed)", fit_score, url)
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

        # Append details about draft to the notification body
        notification_body += (
            f"\n🌟 Suitable Match Found! (Fit score {fit_score}% >= threshold {threshold}%)\n"
            f"A draft email has been prepared and saved to your Desktop:\n"
            f"{desktop_save_path}\n"
        )
        print("✉️ Sending alert notification email to you...")
        send_notification_email(
            subject=f"[Scout Match] {job_title} at {embassy_name} ({fit_score}% Fit)",
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
        print(f"❌ Candidate fit score ({fit_score}%) is below suitability threshold ({threshold}%). Skipping draft cover letter.")
        notification_body += f"\n❌ Candidate fit score ({fit_score}%) is below suitability threshold ({threshold}%). No draft cover letter prepared."
        print("✉️ Sending alert notification email to you...")
        send_notification_email(
            subject=f"[Scout Found] {job_title} at {embassy_name} ({fit_score}% Fit)",
            body=notification_body
        )
        save_application_log(job_title, embassy_name, "Scanned (Below threshold)", fit_score, url)

async def main():
    print("==================================================")
    print("🚀 Starting Global Diplomatic Career Scout scans...")
    print("==================================================")
    
    search_keyword = sys.argv[1] if len(sys.argv) > 1 else "staf"
    resume_path = sys.argv[2] if len(sys.argv) > 2 else "resume.txt"
    
    # Handle the resume path search if default doesn't exist
    if resume_path == "resume.txt" and not os.path.exists(resume_path):
        # Scan current directory for files with "Resume" and ".pdf"
        pdf_resumes = [f for f in os.listdir(".") if "resume" in f.lower() and f.endswith(".pdf")]
        if pdf_resumes:
            resume_path = pdf_resumes[0]
            print(f"ℹ️ Found resume file: {resume_path}")
            
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
                print("⏳ Waiting before next scan...")
                await asyncio.sleep(3)
            await scan_single_portal(url, resume_path)
        except Exception as e:
            print(f"💥 Critical error scanning portal {url}: {str(e)}")
            
    print("\n==================================================")
    print("🏁 Scout Scanning Completed. Logs saved to applications_log.json.")
    print(f"📊 Cumulative Token Usage:")
    print(f"   Prompt Tokens:     {SESSION_USAGE['prompt_tokens']:,}")
    print(f"   Completion Tokens: {SESSION_USAGE['completion_tokens']:,}")
    print(f"   Total Tokens:      {SESSION_USAGE['total_tokens']:,}")
    print("==================================================")
