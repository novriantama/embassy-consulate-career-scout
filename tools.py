import urllib.request
import urllib.parse
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from bs4 import BeautifulSoup
from pypdf import PdfReader
import os
import json
from datetime import datetime

# Helper to load .env variables without external library dependencies
def load_env_variables():
    if os.path.exists(".env"):
        with open(".env", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip()

# Initialize environment configurations
load_env_variables()

def search_active_postings(keyword: str = "staf setempat") -> list[str]:
    """Broadly searches the kemlu.go.id domain for active job openings/portals matching the keyword.

    Args:
        keyword: Search query (e.g. 'staf setempat', 'local staff', 'lowongan').
    """
    try:
        # Search specifically under kemlu.go.id domain for maximum relevance
        query = f"site:kemlu.go.id {keyword}"
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
        
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        )
        with urllib.request.urlopen(req) as response:
            html = response.read()
            
        soup = BeautifulSoup(html, "html.parser")
        links = []
        
        # Extract direct URLs from redirect parameter (uddg)
        for a in soup.find_all('a'):
            href = a.get('href', '')
            if 'uddg=' in href:
                parsed = urllib.parse.urlparse(href)
                params = urllib.parse.parse_qs(parsed.query)
                if 'uddg' in params:
                    actual_url = params['uddg'][0]
                    # Filter for official MoFA subdomains and avoid duplicate pages
                    if "kemlu.go.id" in actual_url and actual_url not in links:
                        # Skip general index pages or foreign ministry contact directories
                        if any(term in actual_url.lower() for term in ["/pages/", "/karir", "/career", "/lowongan", "/berita", "/news"]):
                            links.append(actual_url)
            elif "kemlu.go.id" in href and href.startswith('http') and href not in links:
                if any(term in href.lower() for term in ["/pages/", "/karir", "/career", "/lowongan", "/berita", "/news"]):
                    links.append(href)
                    
        return links[:8]  # Return top 8 job/career pages
    except Exception as e:
        return [f"Search error: {str(e)}"]

def scrape_kbri_portal(url: str) -> str:
    """Scrapes raw text content from an Indonesian Embassy (KBRI) career portal URL.

    Args:
        url: The URL of the embassy job portal page to scrape.
    """
    try:
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        )
        with urllib.request.urlopen(req) as response:
            html = response.read()
        
        soup = BeautifulSoup(html, "html.parser")
        
        # Remove navigation, headers, scripts, and footers to isolate content
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.extract()
            
        text = soup.get_text(separator="\n")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n".join(lines)
    except Exception as e:
        return f"Error scraping portal: {str(e)}"

def read_user_resume(path: str) -> str:
    """Extracts text content from a local resume file (PDF or TXT).

    Args:
        path: The absolute filesystem path to the user's resume file.
    """
    try:
        if path.endswith(".pdf"):
            reader = PdfReader(path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            return text.strip()
        else:
            with open(path, "r", encoding="utf-8") as f:
                return f.read().strip()
    except Exception as e:
        return f"Error reading resume: {str(e)}"

def send_local_alert(title: str, message: str) -> str:
    """Sends a native Mac OS notification banner.

    Args:
        title: The title of the notification.
        message: The body description of the notification.
    """
    try:
        escaped_title = title.replace('"', '\\"')
        escaped_message = message.replace('"', '\\"')
        cmd = f'osascript -e \'display notification "{escaped_message}" with title "{escaped_title}"\''
        os.system(cmd)
        return "Notification sent successfully."
    except Exception as e:
        return f"Failed to send native notification: {str(e)}"

def send_notification_email(subject: str, body: str, recipient: str = None, attachment_path: str = None) -> str:
    """Sends an email notification or application to the target recipient.

    Args:
        subject: The subject of the email.
        body: The HTML or plain text body of the email.
        recipient: The email address to send to. Defaults to NOTIFICATION_RECEIVER from env.
        attachment_path: Optional path to file (like a resume PDF) to attach.
    """
    # Load configuration
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = os.getenv("SMTP_PORT", "587")
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    use_tls = os.getenv("SMTP_USE_TLS", "True").lower() == "true"
    
    default_recipient = recipient or os.getenv("NOTIFICATION_RECEIVER")
    
    if not default_recipient:
        # Fallback logging if no receiver specified
        print(f"⚠️ [MOCK EMAIL] No recipient address configured. Draft saved locally.\nSubject: {subject}\nRecipient: {recipient or 'N/A'}")
        return "Mock email saved (no receiver specified)."
        
    if not smtp_server or not smtp_username or not smtp_password:
        # Fallback mock logging if SMTP credentials are not present
        print(f"⚠️ [MOCK EMAIL] SMTP credentials missing. Logged application draft:\nTo: {default_recipient}\nSubject: {subject}\nAttachment: {attachment_path or 'None'}")
        
        # Save a copy locally on desktop for user visibility
        try:
            save_path = os.path.expanduser(f"~/Desktop/draft_email_{int(datetime.now().timestamp())}.txt")
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(f"To: {default_recipient}\nSubject: {subject}\n\n{body}")
            return f"Mock email drafted and saved on Desktop at {save_path}"
        except Exception as e:
            return f"Mock email drafted. Desktop write failed: {str(e)}"

    try:
        # Prepare message
        msg = MIMEMultipart()
        msg['From'] = smtp_username
        msg['To'] = default_recipient
        msg['Subject'] = subject
        
        # Attach email body
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # Attach resume/file if present
        if attachment_path and os.path.exists(attachment_path):
            with open(attachment_path, "rb") as f:
                attach = MIMEApplication(f.read(), _subtype="pdf" if attachment_path.endswith(".pdf") else "octet-stream")
                attach.add_header('Content-Disposition', 'attachment', filename=os.path.basename(attachment_path))
                msg.attach(attach)
                
        # Send via SMTP
        server = smtplib.SMTP(smtp_server, int(smtp_port))
        if use_tls:
            server.starttls()
        server.login(smtp_username, smtp_password)
        server.sendmail(smtp_username, default_recipient, msg.as_string())
        server.quit()
        
        return "Email sent successfully!"
    except Exception as e:
        return f"Failed to send email: {str(e)}"

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
