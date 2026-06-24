import urllib.request
import urllib.parse
from bs4 import BeautifulSoup

# Bypass system-wide proxy settings which can cause Errno 61 Connection Refused on local Mac environments
try:
    proxy_handler = urllib.request.ProxyHandler({})
    opener = urllib.request.build_opener(proxy_handler)
    urllib.request.install_opener(opener)
except Exception:
    pass

def search_active_postings(keyword: str = "staf setempat") -> list[str]:
    """Broadly searches the kemlu.go.id domain for active job openings/portals matching the keyword.
    """
    # Preloaded list of major embassy and consulate career portals around the world as fallback
    fallback_portals = [
        "https://kemlu.go.id/singapore/id/pages/karir",
        "https://kemlu.go.id/london/id/pages/karir",
        "https://kemlu.go.id/washington/id/pages/karir",
        "https://kemlu.go.id/canberra/id/pages/karir",
        "https://kemlu.go.id/tokyo/id/pages/karir",
        "https://kemlu.go.id/kualalumpur/id/pages/karir",
        "https://kemlu.go.id/sydney/id/pages/karir"
    ]
    try:
        # Search specifically under kemlu.go.id domain for maximum relevance
        query = f"site:kemlu.go.id {keyword}"
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded_query}&df=m"
        
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
                    
        return links[:8] if links else fallback_portals
    except Exception:
        print("ℹ️ Search engine query unavailable (standard network/ISP block on search scraper).")
        print("💡 Proceeding directly with preloaded global Indonesian Embassy & Consulate career portals...")
        return fallback_portals

def scrape_kbri_portal(url: str) -> str:
    """Scrapes raw text content from an Indonesian Embassy (KBRI) career portal URL.
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
