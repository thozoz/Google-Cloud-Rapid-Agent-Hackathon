import os
import datetime
import httpx
from dotenv import load_dotenv
from src.database import get_tracked_hackathons

load_dotenv()

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

def check_deadlines_and_notify():
    """
    Scans tracked hackathons, identifies those with deadlines within 3 days,
    and dispatches structured notifications.
    """
    tracked_hacks = get_tracked_hackathons()
    if not tracked_hacks:
        print("No tracked hackathons found in database.")
        return []
        
    print(f"Checking deadlines for {len(tracked_hacks)} tracked hackathons...")
    
    now = datetime.datetime.now()
    reminded_hackathons = []
    
    for h in tracked_hacks:
        deadline = h.get("deadline")
        if not deadline:
            print(f"Skipping '{h['title']}' - No valid deadline timestamp.")
            continue
            
        # If deadline is stored as a string or parsed timestamp, ensure it is datetime
        if isinstance(deadline, str):
            try:
                deadline = datetime.datetime.fromisoformat(deadline)
            except ValueError:
                print(f"Could not parse ISO deadline string for '{h['title']}'")
                continue
                
        # Calculate days remaining
        # If the deadline date is at the start of that day (00:00:00), we can adjust or compare dates directly
        # Let's count days
        delta = deadline - now
        days_remaining = delta.days + 1  # Standard offset to capture current day remainder
        
        # Check if the deadline is between 0 and 3 days away
        if 0 <= days_remaining <= 3:
            title = h.get("title")
            url = h.get("url")
            prize = h.get("prize_pool", "N/A")
            score = h.get("match_score", "N/A")
            reason = h.get("match_reason", "No reason provided.")
            deadline_str = h.get("deadline_raw", "N/A")
            
            print(f"URGENT: '{title}' deadline is in {days_remaining} days! Triggering notification...")
            
            send_discord_notification(title, url, prize, score, reason, deadline_str, days_remaining)
            reminded_hackathons.append(h)
            
    print(f"Deadline check complete. Dispatched {len(reminded_hackathons)} reminders.")
    return reminded_hackathons

def send_discord_notification(title, url, prize, score, reason, deadline_str, days_remaining):
    """Sends a premium, beautifully-formatted embed notification to Discord webhook."""
    if not DISCORD_WEBHOOK_URL:
        print(f"[CONSOLE LOG - NO WEBHOOK] REMINDER: '{title}' is ending in {days_remaining} days! URL: {url}")
        return
        
    # Standard color (vibrant orange/red for urgency)
    color = 15548997 if days_remaining <= 1 else 16753920
    
    payload = {
        "username": "Hackathon Deadline Bot",
        "avatar_url": "https://d112y698adiu2z.cloudfront.net/photos/production/challenge_thumbnails/004/595/623/datas/medium_square.jpg",
        "embeds": [
            {
                "title": f"⏰ Deadline Approaching: {days_remaining} Days Left!",
                "description": f"Submit your project for **{title}** before it's too late!",
                "url": url,
                "color": color,
                "fields": [
                    {"name": "🏆 Prize Pool", "value": f"**{prize}**", "inline": True},
                    {"name": "⭐ Match Score", "value": f"**{score}/10**", "inline": True},
                    {"name": "📅 Submission Deadline", "value": f"`{deadline_str}`", "inline": False},
                    {"name": "🤖 AI Fit Reason", "value": f"*{reason}*", "inline": False}
                ],
                "footer": {
                    "text": "Hackathon Discovery & Tracking Agent • Autonomous Notification",
                    "icon_url": "https://img.icons8.com/color/48/google-logo.png"
                },
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
            }
        ]
    }
    
    try:
        response = httpx.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        if response.status_code == 204 or response.status_code == 200:
            print(f"Successfully sent Discord webhook reminder for '{title}'.")
        else:
            print(f"Failed to send Discord webhook. Status code: {response.status_code}, Body: {response.text}")
    except Exception as e:
        print(f"Error sending Discord webhook: {e}")

if __name__ == "__main__":
    # Test reminder script locally
    check_deadlines_and_notify()
