import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
from pypdf import PdfReader
import os

def search_embassy_portals(keyword: str) -> list[str]:
    """Searches for Indonesian Embassy (KBRI) or Consulate (KJRI) job/career portal URLs.

    Args:
        keyword: The search keyword (e.g., 'KBRI Singapore local staff', 'KJRI Sydney karir').
    """
    try:
        # We query DuckDuckGo HTML search since it doesn't require API keys or trigger CAPTCHAs easily
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
        
        # Parse the DuckDuckGo redirect links (uddg parameter contains the actual URL)
        for a in soup.find_all('a'):
            href = a.get('href', '')
            if 'uddg=' in href:
                parsed = urllib.parse.urlparse(href)
                params = urllib.parse.parse_qs(parsed.query)
                if 'uddg' in params:
                    actual_url = params['uddg'][0]
                    if "kemlu.go.id" in actual_url and actual_url not in links:
                        links.append(actual_url)
            elif "kemlu.go.id" in href and href.startswith('http') and href not in links:
                links.append(href)
                
        return links[:5]  # Return top 5 relevant embassy pages
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
        
        # Extract text and clean up excess white space
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

def save_email_draft(content: str) -> str:
    """Saves the drafted diplomatic email to a text file on the local drive.

    Args:
        content: The text content of the email draft.
    """
    try:
        save_path = os.path.expanduser("~/Desktop/embassy_application_draft.txt")
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Draft successfully saved to {save_path}"
    except Exception as e:
        return f"Error saving draft: {str(e)}"
