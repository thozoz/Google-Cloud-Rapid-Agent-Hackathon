import datetime
import re
from bs4 import BeautifulSoup

def clean_prize(prize_html):
    if not prize_html:
        return "N/A"
    text = BeautifulSoup(prize_html, "html.parser").get_text()
    return text.strip()

def parse_deadline(date_range_str):
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

# Test inputs
test_prizes = [
    "$<span data-currency-value>60,000</span>",
    "€<span data-currency-value>5,000</span>",
    "N/A"
]

test_dates = [
    "May 05 - Jun 11, 2026",
    "Oct 12, 2025",
    "Jan 1 - Feb 28",
    "25 Dec, 2026"
]

print("=== PRIZE CLEANING TEST ===")
for p in test_prizes:
    print(f"Raw: {p} => Cleaned: {clean_prize(p)}")

print("\n=== DEADLINE DATE PARSING TEST ===")
for d in test_dates:
    parsed = parse_deadline(d)
    print(f"Raw: {d} => Parsed: {parsed.strftime('%Y-%m-%d') if parsed else 'Failed'}")
