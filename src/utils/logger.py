import os
import json
from datetime import datetime

def save_application_log(job_title: str, embassy: str, status: str, fit_score: int, url: str) -> None:
    """Logs the job scan and application outcomes locally to a JSON file.
    """
    log_path = "applications_log.json"
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "embassy": embassy,
        "job_title": job_title,
        "fit_score": fit_score,
        "status": status,
        "url": url
    }
    
    logs = []
    if os.path.exists(log_path):
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                logs = json.load(f)
        except Exception:
            logs = []
            
    logs.append(log_entry)
    
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=4)
