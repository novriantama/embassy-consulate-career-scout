from pydantic import BaseModel, Field

# The structure returned by the Monitor agent
class JobPosting(BaseModel):
    job_title: str = Field(description="The title of the job opening.")
    is_embassy_local_staff: bool = Field(description="True if the job is for Local Staff (Staf Setempat), False otherwise.")
    requirements: list[str] = Field(description="List of key requirements/skills extracted from the job posting.")
    application_deadline: str = Field(description="The application deadline or timeline info.")

# The structure returned by the Matcher agent
class ResumeMatch(BaseModel):
    fit_score: int = Field(description="Candidate's matching score from 0 to 100 based on requirements.")
    matching_strengths: list[str] = Field(description="Exactly 3 key strengths or matching areas from candidate's resume.")
    missing_skills: list[str] = Field(description="Key job requirements not covered by the candidate's resume.")

# The structure returned by the Drafter agent
class EmailDraft(BaseModel):
    email_subject: str = Field(description="The formal, diplomatic subject line of the application email.")
    email_body: str = Field(description="The complete, polished body of the application email.")
    save_status: str = Field(description="The status of the saving operation.")
