from google.antigravity import LocalAgentConfig
from tools import scrape_kbri_portal
from schemas import JobPosting, ResumeMatch, EmailDraft

# 1. The Monitor configures a web scraper tool and returns structured job details including contact email
monitor_config = LocalAgentConfig(
    system_instructions=(
        "You are a strict data extraction agent. Use the scrape_kbri_portal tool "
        "on the provided URL. Identify if there is an active 'Local Staff' (Staf Setempat) opening. "
        "Do not summarize or guess. Extract the embassy/consulate name (e.g., 'KBRI Singapore', "
        "'KJRI Sydney'), the job title, requirements, deadline, and the contact/application email "
        "address (if visible on the page). Return the exact JSON schema."
    ),
    tools=[scrape_kbri_portal],
    response_schema=JobPosting
)

# 2. The Matcher compares job requirements against a resume and returns suitability scores
matcher_config = LocalAgentConfig(
    system_instructions=(
        "You are an expert HR Analyst specialized in embassy recruitment. Compare the job requirements "
        "against the user's resume text. Determine the fit score (0-100), extract exactly 3 matching strengths, "
        "and list any missing requirements. Mark 'is_suitable' as True if the fit_score is 80 or above, otherwise False."
    ),
    response_schema=ResumeMatch
)

# 3. The Drafter drafts a highly formal diplomatic application cover email
drafter_config = LocalAgentConfig(
    system_instructions=(
        "You write highly formal, diplomatic cover emails for Indonesian embassy job applications. "
        "Use the job details (title, embassy name) and the candidate's 3 key strengths to draft a compelling "
        "message. Return the subject and body structured according to the schema."
    ),
    response_schema=EmailDraft
)
