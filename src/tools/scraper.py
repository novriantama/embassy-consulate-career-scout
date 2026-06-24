import urllib.request
import urllib.parse
import json
import os
import re
from bs4 import BeautifulSoup

# Bypass system-wide proxy settings which can cause Errno 61 Connection Refused on local Mac environments
try:
    proxy_handler = urllib.request.ProxyHandler({})
    opener = urllib.request.build_opener(proxy_handler)
    urllib.request.install_opener(opener)
except Exception:
    pass

# Comprehensive list of Indonesian Embassy and Consulate representative cities
ALL_CITIES = [
    "singapore", "london", "washington", "canberra", "tokyo", "kualalumpur", "sydney",
    "melbourne", "perth", "penang", "johorbahru", "kotakinabalu", "kuching", "bangkok",
    "songkhla", "manila", "davao", "hanoi", "hochiminh", "phnompenh", "vientiane",
    "yangon", "dili", "portmoresby", "vanimo", "wellington", "suva", "noumea",
    "seoul", "beijing", "shanghai", "guangzhou", "hongkong", "newdelhi", "mumbai",
    "dhaka", "colombo", "islamabad", "karachi", "kabul", "tehran", "baghdad",
    "paris", "berlin", "frankfurt", "hamburg", "thehague", "brussels", "vienna",
    "bern", "geneva", "rome", "vatican", "madrid", "lisbon", "athens", "ankara",
    "istanbul", "moscow", "kiev", "warsaw", "prague", "budapest", "bucharest",
    "sofia", "stockholm", "copenhagen", "oslo", "helsinki", "dublin", "bratislava",
    "zagreb", "sarajevo", "belgrade", "riyadh", "jeddah", "cairo", "abudhabi",
    "dubai", "doha", "manama", "kuwait", "muscat", "amman", "damascus", "beirut",
    "sanaa", "tripoli", "algiers", "rabat", "tunis", "khartoum", "pretoria",
    "capetown", "nairobi", "addisababa", "dakar", "abuja", "harare", "antananarivo",
    "daressalaam", "windhoek", "maputo", "luanda", "brazzaville", "yaounde",
    "newyork", "losangeles", "sanfrancisco", "chicago", "houston", "ottawa",
    "vancouver", "toronto", "mexico", "havana", "bogota", "caracas", "quito",
    "lima", "brasilia", "paramaribo", "buenosaires", "santiago", "lapaz"
]

# Custom mappings for specific subdomains or Instagram handles that don't follow city patterns
CITIES_MAPPING = {
    "singapore": {"web": "singapore", "insta": ["kbri.singapura", "kbri.singapore"]},
    "london": {"web": "london", "insta": ["indonesianembassylondon", "kbri.london"]},
    "washington": {"web": "washington", "insta": ["kbriwashdc", "kbri.washington"]},
    "canberra": {"web": "canberra", "insta": ["kbricanberra"]},
    "tokyo": {"web": "tokyo", "insta": ["kbritokyo"]},
    "kualalumpur": {"web": "kualalumpur", "insta": ["kbrikualalumpur", "indonesiainkualalumpur"]},
    "sydney": {"web": "sydney", "insta": ["kjrisydney", "indonesiainsydney"]},
    "melbourne": {"web": "melbourne", "insta": ["kjrimelbourne", "indonesiainmelbourne"]},
    "perth": {"web": "perth", "insta": ["kjriperth", "indonesiainperth"]},
    "penang": {"web": "penang", "insta": ["kjripenang"]},
    "johorbahru": {"web": "johorbahru", "insta": ["kjrijohorbahru"]},
    "bangkok": {"web": "bangkok", "insta": ["kbribangkok", "indonesiainbangkok"]},
    "seoul": {"web": "seoul", "insta": ["kbriseoul", "indonesiainseoul"]},
    "berlin": {"web": "berlin", "insta": ["kbriberlin"]},
    "cairo": {"web": "cairo", "insta": ["kbricairo"]},
    "riyadh": {"web": "riyadh", "insta": ["kbririyadh"]},
    "jeddah": {"web": "jeddah", "insta": ["kjrijeddah"]},
    "beijing": {"web": "beijing", "insta": ["kbribeijing"]},
    "hongkong": {"web": "hongkong", "insta": ["kjrihongkong"]},
    "thehague": {"web": "thehague", "insta": ["kbrithehague"]},
    "hague": {"web": "thehague", "insta": ["kbrithehague"]},
    "paris": {"web": "paris", "insta": ["kbriparis"]},
    "rome": {"web": "rome", "insta": ["kbriroma", "kbrirome"]},
    "hochiminh": {"web": "hochiminhcity", "insta": ["kjrihcmc"]},
    "losangeles": {"web": "losangeles", "insta": ["kjrilosangeles"]},
    "sanfrancisco": {"web": "sanfrancisco", "insta": ["kjrisanfrancisco"]},
    "newyork": {"web": "newyork", "insta": ["kjrinewyork", "indonesiainnewyork"]},
    "chicago": {"web": "chicago", "insta": ["kjrichicago"]},
    "houston": {"web": "houston", "insta": ["kjrihouston"]}
}

def search_active_postings(keyword: str = "staf setempat") -> list[str]:
    """Broadly searches the kemlu.go.id and instagram.com domains for active job openings/portals matching the keyword.
    """
    # 1. First, check if keyword requests specific cities
    targeted = []
    keyword_lower = keyword.lower()
    for city in ALL_CITIES:
        if city in keyword_lower or city.replace(" ", "") in keyword_lower:
            web_sub = CITIES_MAPPING.get(city, {}).get("web", city)
            targeted.append(f"https://kemlu.go.id/{web_sub}/id/pages/karir")
            insta_handles = CITIES_MAPPING.get(city, {}).get("insta", [f"kbri.{city}", f"kbri{city}", f"indonesiain{city}"])
            for handle in insta_handles:
                targeted.append(f"https://www.instagram.com/{handle}/")
                
    if targeted:
        print(f"🎯 Targeted scan resolved from keyword for: {[url for url in targeted]}")
        return targeted

    # 2. Build default fallback portals using top 20 major perwakilans
    top_cities = [
        "singapore", "kualalumpur", "london", "canberra", "sydney", "washington", "tokyo",
        "seoul", "riyadh", "jeddah", "bangkok", "berlin", "paris", "thehague", "melbourne",
        "perth", "penang", "johorbahru", "cairo", "beijing"
    ]
    fallback_portals = []
    for city in top_cities:
        web_sub = CITIES_MAPPING.get(city, {}).get("web", city)
        fallback_portals.append(f"https://kemlu.go.id/{web_sub}/id/pages/karir")
        insta_handle = CITIES_MAPPING.get(city, {}).get("insta", [f"kbri.{city}"])[0]
        fallback_portals.append(f"https://www.instagram.com/{insta_handle}/")
        
    try:
        # Search site:kemlu.go.id OR site:instagram.com for embassy/consulate openings
        query = f"(site:kemlu.go.id OR site:instagram.com) (KBRI OR KJRI) {keyword}"
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded_query}&df=m"
        
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
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
                    # Filter for official MoFA subdomains or Instagram links and avoid duplicate pages
                    if ("kemlu.go.id" in actual_url or "instagram.com" in actual_url) and actual_url not in links:
                        if "instagram.com" in actual_url:
                            if not any(term in actual_url.lower() for term in ["/developer", "/about", "/directory", "/explore"]):
                                links.append(actual_url)
                        elif any(term in actual_url.lower() for term in ["/pages/", "/karir", "/career", "/lowongan", "/berita", "/news"]):
                            links.append(actual_url)
                            
        return links[:8] if links else fallback_portals
    except Exception:
        print("ℹ️ Search engine query unavailable (standard network/ISP block on search scraper).")
        print("💡 Proceeding directly with preloaded global Indonesian Embassy & Consulate career portals and Instagram profiles...")
        return fallback_portals

def fetch_instagram_post(shortcode: str, session_id: str) -> str:
    """Queries Instagram's public JSON API for a post shortcode.
    """
    api_url = f"https://www.instagram.com/p/{shortcode}/?__a=1&__d=dis"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    if session_id:
        headers['Cookie'] = f'sessionid={session_id}'
        
    try:
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            
        # Parse post caption from JSON response
        items = data.get("items", [])
        if items:
            caption_text = items[0].get("caption", {}).get("text", "")
            return f"Instagram Post ({shortcode}) Caption:\n\n{caption_text}"
            
        # Alternative graphql schema if items is empty
        graphql = data.get("graphql", {}).get("shortcode_media", {})
        if graphql:
            edges = graphql.get("edge_media_to_caption", {}).get("edges", [])
            if edges:
                caption_text = edges[0].get('node', {}).get('text', '')
                return f"Instagram Post ({shortcode}) Caption:\n\n{caption_text}"
                
        return "Instagram JSON fetched, but no caption text was found."
    except Exception as e:
        if not session_id:
            return (
                f"Error fetching Instagram post {shortcode}: {str(e)}\n"
                f"⚠️ WARNING: Instagram requests require authentication cookies. "
                f"Please add INSTAGRAM_SESSION_ID to your .env file."
            )
        return f"Error fetching Instagram post {shortcode} with session ID: {str(e)}"

def fetch_instagram_profile(username: str, session_id: str) -> str:
    """Queries Instagram's web profile info API to get recent post captions.
    """
    api_url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={username}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'X-IG-App-ID': '936619743392459'
    }
    if session_id:
        headers['Cookie'] = f'sessionid={session_id}'
        
    try:
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            
        # Extract captions of the most recent posts
        user_data = data.get("data", {}).get("user", {})
        if not user_data:
            return f"Instagram profile '{username}' not found or returned empty data."
            
        timeline = user_data.get("edge_owner_to_timeline_media", {}).get("edges", [])
        if not timeline:
            return f"Instagram profile '{username}' has no public posts."
            
        captions = []
        for i, edge in enumerate(timeline[:5]): # Limit to first 5 posts for length control
            node = edge.get("node", {})
            shortcode = node.get("shortcode", "")
            edges = node.get("edge_media_to_caption", {}).get("edges", [])
            caption = edges[0].get("node", {}).get("text", "") if edges else ""
            captions.append(f"--- Post {i+1} (Shortcode: {shortcode}) ---\n{caption}")
            
        profile_info = f"Instagram Profile: @{username}\nFull Name: {user_data.get('full_name')}\n\n"
        return profile_info + "\n\n".join(captions)
    except Exception as e:
        if not session_id:
            return (
                f"Error fetching Instagram profile {username}: {str(e)}\n"
                f"⚠️ WARNING: Instagram requests require authentication cookies. "
                f"Please add INSTAGRAM_SESSION_ID to your .env file."
            )
        return f"Error fetching Instagram profile {username} with session ID: {str(e)}"

def scrape_instagram_url(url: str) -> str:
    """Parses Instagram URL and delegates to post or profile scraping handlers.
    """
    session_id = os.getenv("INSTAGRAM_SESSION_ID", "").strip()
    
    # Try parsing post/reel shortcode (e.g. /p/C8o7U4hSa4Q/ or /reel/C8o7U4hSa4Q/)
    post_match = re.search(r'/(?:p|reel)/([A-Za-z0-9_-]+)', url)
    if post_match:
        shortcode = post_match.group(1)
        return fetch_instagram_post(shortcode, session_id)
        
    # Try parsing profile handle (e.g. https://www.instagram.com/kbri.singapura/)
    profile_match = re.search(r'instagram\.com/([A-Za-z0-9_\.]+)/?$', url.rstrip('/'))
    if profile_match:
        username = profile_match.group(1)
        if username not in ["p", "reel", "explore", "stories", "direct"]:
            return fetch_instagram_profile(username, session_id)
            
    return f"Instagram URL '{url}' format not recognized or unsupported."

def scrape_kbri_portal(url: str) -> str:
    """Scrapes raw text content from an Indonesian Embassy (KBRI) career portal URL or Instagram page.
    """
    if "instagram.com" in url:
        return scrape_instagram_url(url)
        
    try:
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
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
