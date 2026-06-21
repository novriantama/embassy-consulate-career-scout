from google.antigravity import LocalAgentConfig
from tools import scrape_kbri_portal, save_email_draft
from schemas import JobPosting, ResumeMatch, EmailDraft

# 1. The Monitor configures a web scraper tool and returns structured job details
monitor_config = LocalAgentConfig(
    system_instructions=(
        "You are a strict data extraction agent. Use the scrape_kbri_portal tool "
        "on the provided URL. Determine if there is a 'Local Staff' (Staf Setempat) opening. "
        "Do not summarize or guess. Extract the details to match the schema exactly."
    ),
    tools=[scrape_kbri_portal],
    response_schema=JobPosting
)

# 2. The Matcher compares job requirements against a resume and returns match details
matcher_config = LocalAgentConfig(
    system_instructions=(
        "You are an expert HR Analyst specialized in embassy recruitment. Compare the job requirements "
        "against the user's resume text. Determine the fit score, match strengths (exactly 3), and "
        "missing skills."
    ),
    response_schema=ResumeMatch
)

# 3. The Drafter drafts a diplomatic cover email and saves it to disk
drafter_config = LocalAgentConfig(
    system_instructions=(
        "You write highly formal, diplomatic emails for embassy applications. Use the job details "
        "and the candidate's 3 matching strengths to draft a compelling cover email. Use the "
        "save_email_draft tool to save the email draft, and return the schema."
    ),
    tools=[save_email_draft],
    response_schema=EmailDraft
)
