import httpx
import re
import datetime
from bs4 import BeautifulSoup
from src.database import get_db, save_hackathons, init_db

def clean_prize(prize_html):
    """Extracts text from Devpost HTML-formatted prize amount."""
    if not prize_html:
        return "N/A"
    text = BeautifulSoup(prize_html, "html.parser").get_text()
    return text.strip()

def parse_deadline(date_range_str):
    """
    Parses deadline from Devpost submission period date range string.
    Example formats:
    - "May 05 - Jun 11, 2026" -> datetime(2026, 6, 11)
    - "Jun 11, 2026" -> datetime(2026, 6, 11)
    """
    if not date_range_str:
        return None
    
    try:
        parts = re.split(r'[-–—]', date_range_str)
        end_date_str = parts[-1].strip()
        
        current_year = datetime.datetime.now().year
        if not re.search(r'\d{4}', end_date_str):
            end_date_str = f"{end_date_str}, {current_year}"
            
        for fmt in ("%b %d, %Y", "%B %d, %Y", "%d %b, %Y", "%d %B, %Y"):
            try:
                return datetime.datetime.strptime(end_date_str, fmt)
            except ValueError:
                continue
                
    except Exception as e:
        print(f"Error parsing date '{date_range_str}': {e}")
        
    return None

def extract_deadline_from_hackathon(h):
    """
    Tries multiple sources to extract deadline from hackathon object.
    Returns (deadline_dt, deadline_raw_str) tuple.
    """
    # Try primary field: submission_period_dates
    date_range_str = h.get("submission_period_dates")
    if date_range_str:
        deadline_dt = parse_deadline(date_range_str)
        if deadline_dt:
            return deadline_dt, date_range_str
    
    # Fallback: try end_date field
    end_date = h.get("end_date")
    if end_date:
        try:
            if isinstance(end_date, str):
                # Try parsing ISO format
                deadline_dt = datetime.datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                return deadline_dt, end_date
        except:
            pass
    
    # Fallback: try submission_end_date
    submission_end = h.get("submission_end_date")
    if submission_end:
        deadline_dt = parse_deadline(submission_end)
        if deadline_dt:
            return deadline_dt, submission_end
    
    # If no deadline found, return None for both
    return None, date_range_str or "N/A"

def scrape_devpost(max_pages=5):
    """
    Scrapes active/upcoming hackathons from Devpost API.
    Returns the list of processed hackathons.
    """
    url = "https://devpost.com/api/hackathons"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    
    scraped_hackathons = []
    
    # We want open & upcoming hackathons
    params = {
        "challenge_type": "all",
        "status[]": ["open", "upcoming"],
        "page": 1
    }
    
    try:
        for page in range(1, max_pages + 1):
            params["page"] = page
            print(f"Scraping page {page} of {max_pages}...")
            
            response = httpx.get(url, headers=headers, params=params, follow_redirects=True, timeout=20)
            if response.status_code != 200:
                print(f"Failed to fetch page {page}. Status: {response.status_code}")
                break
                
            data = response.json()
            hackathons_list = data.get("hackathons", [])
            if not hackathons_list:
                print(f"No hackathons found on page {page}.")
                break
                
            for h in hackathons_list:
                # Basic fields
                title = h.get("title", "Untitled Hackathon")
                hackathon_url = h.get("url")
                if not hackathon_url:
                    continue
                
                # Extract themes/tags
                tags = [theme.get("name") for theme in h.get("themes", []) if theme.get("name")]
                
                # Clean prize pool
                prize_pool = clean_prize(h.get("prize_amount"))
                
                # Extract deadline (tries multiple sources)
                deadline_dt, deadline_raw = extract_deadline_from_hackathon(h)
                
                # Extract eligibility/location
                location_info = h.get("displayed_location", {})
                location = location_info.get("location", "Online")
                eligibility = f"Open to all ({location})"
                if h.get("invite_only"):
                    eligibility = "Invite Only"
                
                # Structure hackathon document
                hackathon_doc = {
                    "title": title,
                    "url": hackathon_url,
                    "tags": tags,
                    "prize_pool": prize_pool,
                    "deadline_raw": deadline_raw,
                    "deadline": deadline_dt,  # Stores as BSON datetime in MongoDB
                    "eligibility": eligibility,
                    "organization": h.get("organization_name", "Unknown Organizers"),
                    "thumbnail_url": h.get("thumbnail_url") or "",
                    "scraped_at": datetime.datetime.now()
                }
                
                scraped_hackathons.append(hackathon_doc)
                
            # If we fetched fewer hackathons than per_page, we've reached the end
            meta = data.get("meta", {})
            per_page = meta.get("per_page", 9)
            if len(hackathons_list) < per_page:
                break
                
        # Save to database
        if scraped_hackathons:
            count = save_hackathons(scraped_hackathons)
            print(f"Successfully scraped and upserted {count} hackathons to MongoDB Atlas.")
        else:
            print("No hackathons scraped.")
            
    except Exception as e:
        print(f"Scraper error: {e}")
        
    return scraped_hackathons

if __name__ == "__main__":
    # Test script locally
    try:
        init_db()
        scrape_devpost(max_pages=2)
    except Exception as e:
        print(f"Test run failed: {e}")
