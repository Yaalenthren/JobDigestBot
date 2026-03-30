"""
DevOps Job Digest - Daily Job Scraper & Email Sender
Scrapes LinkedIn, RemoteOK, and We Work Remotely for DevOps/Cloud jobs
and sends a daily digest email.
"""

import os
import json
import smtplib
import requests
from datetime import datetime, date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from bs4 import BeautifulSoup
import time
import re

# ── Config from GitHub Secrets ──────────────────────────────────────────────
RECIPIENT_EMAIL = os.environ["RECIPIENT_EMAIL"]       # your personal email
SENDER_EMAIL    = os.environ["SENDER_EMAIL"]          # Gmail you're sending from
SENDER_PASSWORD = os.environ["SENDER_APP_PASSWORD"]   # Gmail App Password

# ── Job Search Config ────────────────────────────────────────────────────────
KEYWORDS = [
    "devops engineer",
    "cloud engineer",
    "site reliability engineer",
    "platform engineer",
    "kubernetes engineer",
    "aws engineer",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

today = date.today().strftime("%B %d, %Y")

# ── Senior keywords — filter these OUT ───────────────────────────────────────
SENIOR_KEYWORDS = [
    "senior", "sr.", "sr ", "lead", "principal", "staff", "manager",
    "director", "head of", "vp ", "vice president", "architect",
    "5+ years", "6+ years", "7+ years", "8+ years", "10+ years",
    "5 years", "6 years", "7 years", "8 years", "10 years",
]

# ── Region-restricted keywords — filter these OUT ────────────────────────────
REGION_RESTRICTED = [
    "only", "must be based", "must reside", "must live",
    "us only", "uk only", "eu only", "usa only", "canada only",
    "australia only", "germany only", "france only",
    "united states only", "north america only", "europe only",
    "authorized to work in", "eligible to work in",
    "right to work in", "visa sponsorship not",
    "no sponsorship", "we do not sponsor",
    "residents of", "citizens only", "permanent resident",
]

# ── Worldwide-friendly keywords — always keep these ──────────────────────────
WORLDWIDE_KEYWORDS = [
    "worldwide", "global", "anywhere", "fully remote", "work from anywhere",
    "all countries", "international", "remote worldwide", "100% remote",
]

def is_entry_level(title, tags=""):
    """Returns True if the job is NOT a senior role."""
    text = (title + " " + tags).lower()
    for kw in SENIOR_KEYWORDS:
        if kw in text:
            return False
    return True

def is_worldwide_remote(location, description=""):
    """
    Returns True if the job is open to candidates worldwide.
    - Rejects jobs that mention region restrictions
    - Keeps jobs that say worldwide/global/anywhere
    - Keeps jobs with vague locations like 'Remote' or 'Worldwide'
    """
    text = (location + " " + description).lower()

    # If explicitly worldwide — always keep
    for kw in WORLDWIDE_KEYWORDS:
        if kw in text:
            return True

    # If region restricted — reject
    for kw in REGION_RESTRICTED:
        if kw in text:
            return False

    # If location is just "Remote" or empty — assume worldwide, keep it
    vague = ["remote", "worldwide", "global", "", "work from home", "wfh"]
    if location.lower().strip() in vague:
        return True

    # If it mentions a specific country alone — likely restricted
    specific_countries = [
        "united states", "united kingdom", "australia", "canada",
        "germany", "france", "netherlands", "singapore", "india",
        "new zealand", "ireland", "sweden", "denmark", "norway",
    ]
    for country in specific_countries:
        if country in text and "worldwide" not in text and "global" not in text:
            return False

    return True


# ── Scrapers ─────────────────────────────────────────────────────────────────

def scrape_remoteok():
    """Scrape RemoteOK for DevOps/Cloud jobs."""
    jobs = []
    try:
        url = "https://remoteok.com/api"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        data = resp.json()

        devops_tags = {"devops", "aws", "kubernetes", "cloud", "terraform", "docker",
                       "gcp", "azure", "sre", "platform", "ci/cd", "infrastructure"}

        for item in data[1:]:  # first item is metadata
            if not isinstance(item, dict):
                continue
            tags = set(t.lower() for t in item.get("tags", []))
            title = item.get("position", "").lower()

            if (tags & devops_tags or any(k in title for k in ["devops", "cloud", "sre", "platform", "infra"])) and is_entry_level(item.get("position", ""), ", ".join(item.get("tags", []))) and is_worldwide_remote("Remote"):
                jobs.append({
                    "title":   item.get("position", "N/A"),
                    "company": item.get("company", "N/A"),
                    "location": "Remote",
                    "url":     item.get("url", f"https://remoteok.com/l/{item.get('id', '')}"),
                    "source":  "RemoteOK",
                    "tags":    ", ".join(item.get("tags", [])[:5]),
                    "date":    item.get("date", "")[:10] if item.get("date") else "",
                })
        print(f"[RemoteOK] Found {len(jobs)} jobs")
    except Exception as e:
        print(f"[RemoteOK] Error: {e}")
    return jobs[:15]


def scrape_weworkremotely():
    """Scrape We Work Remotely DevOps section."""
    jobs = []
    urls = [
        "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss",
        "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss",
    ]
    for url in urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(resp.content, "xml")
            items = soup.find_all("item")

            for item in items[:10]:
                title = item.find("title")
                link  = item.find("link")
                region = item.find("region")

                if not title or not link:
                    continue

                title_text = title.get_text(strip=True)
                title_text = re.sub(r'<!\[CDATA\[|\]\]>', '', title_text).strip()

                if not is_entry_level(title_text):
                    continue

                location_text = region.get_text(strip=True) if region else "Remote"
                if not is_worldwide_remote(location_text):
                    continue

                jobs.append({
                    "title":    title_text,
                    "company":  "See listing",
                    "location": location_text,
                    "url":      link.next_sibling.strip() if link.next_sibling else link.get_text(strip=True),
                    "source":   "WeWorkRemotely",
                    "tags":     "",
                    "date":     "",
                })
        except Exception as e:
            print(f"[WWR] Error: {e}")
    print(f"[WeWorkRemotely] Found {len(jobs)} jobs")
    return jobs[:15]


def scrape_linkedin_rss():
    """Use LinkedIn job search RSS feeds."""
    jobs = []
    searches = [
        ("junior+devops+engineer", "worldwide"),
        ("entry+level+cloud+engineer", "worldwide"),
        ("junior+kubernetes+engineer", "worldwide"),
        ("devops+engineer", "sri+lanka"),
    ]
    for keyword, location in searches:
        try:
            # f_E=2 = Entry level, f_WT=2 = Remote, f_TPR=r86400 = past 24hrs
            url = (
                f"https://www.linkedin.com/jobs/search/?keywords={keyword}"
                f"&location={location}&f_TPR=r86400&f_WT=2&f_E=2"
            )
            jobs.append({
                "title":    keyword.replace("+", " ").title(),
                "company":  "Multiple companies",
                "location": location.replace("+", " ").title(),
                "url":      url,
                "source":   "LinkedIn Search",
                "tags":     "devops, cloud",
                "date":     "",
            })
        except Exception as e:
            print(f"[LinkedIn] Error: {e}")
    print(f"[LinkedIn] Generated {len(jobs)} search links")
    return jobs


def scrape_jobspy_style():
    """Direct job board API calls via jobspy-compatible endpoints."""
    jobs = []

    # Himalayas (DevOps remote jobs)
    try:
        url = "https://himalayas.app/jobs/api?q=devops&limit=10"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        data = resp.json()
        for item in data.get("jobs", []):
            if not is_entry_level(item.get("title", ""), ", ".join(item.get("skills", []))):
                continue
            if not is_worldwide_remote(item.get("location", "Remote")):
                continue
            jobs.append({
                "title":    item.get("title", "N/A"),
                "company":  item.get("company", {}).get("name", "N/A"),
                "location": item.get("location", "Remote"),
                "url":      item.get("applicationLink") or item.get("url", "#"),
                "source":   "Himalayas",
                "tags":     ", ".join(item.get("skills", [])[:4]),
                "date":     item.get("createdAt", "")[:10],
            })
    except Exception as e:
        print(f"[Himalayas] Error: {e}")

    # Remotive
    try:
        url = "https://remotive.com/api/remote-jobs?category=devops-sysadmin&limit=10"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        data = resp.json()
        for item in data.get("jobs", []):
            if not is_entry_level(item.get("title", ""), item.get("tags", "")):
                continue
            if not is_worldwide_remote(item.get("candidate_required_location", "Worldwide")):
                continue
            jobs.append({
                "location": item.get("candidate_required_location", "Worldwide"),
                "url":      item.get("url", "#"),
                "source":   "Remotive",
                "tags":     item.get("tags", ""),
                "date":     item.get("publication_date", "")[:10],
            })
    except Exception as e:
        print(f"[Remotive] Error: {e}")

    print(f"[Other boards] Found {len(jobs)} jobs")
    return jobs[:15]


# ── Dedup ─────────────────────────────────────────────────────────────────────

def deduplicate(jobs):
    seen = set()
    unique = []
    for job in jobs:
        key = (job["title"].lower().strip(), job["company"].lower().strip())
        if key not in seen:
            seen.add(key)
            unique.append(job)
    return unique


# ── Email Builder ─────────────────────────────────────────────────────────────

def build_email_html(jobs):
    source_colors = {
        "RemoteOK":       "#00b894",
        "WeWorkRemotely": "#0984e3",
        "LinkedIn Search":"#0077b5",
        "Himalayas":      "#6c5ce7",
        "Remotive":       "#e17055",
    }

    job_cards = ""
    for job in jobs:
        color = source_colors.get(job["source"], "#636e72")
        tags_html = ""
        if job.get("tags"):
            tag_list = [t.strip() for t in str(job["tags"]).split(",") if t.strip()][:4]
            tags_html = "".join(
                f'<span style="background:#f0f4ff;color:#3d6af0;padding:2px 8px;'
                f'border-radius:999px;font-size:11px;margin-right:4px;">{t}</span>'
                for t in tag_list
            )

        job_cards += f"""
        <div style="background:#ffffff;border:1px solid #e8ecf0;border-radius:12px;
                    padding:20px;margin-bottom:16px;border-left:4px solid {color};">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;">
            <div style="flex:1;">
              <h3 style="margin:0 0 4px;font-size:16px;color:#1a1a2e;font-weight:600;">
                {job['title']}
              </h3>
              <p style="margin:0 0 8px;color:#636e72;font-size:13px;">
                🏢 {job['company']} &nbsp;|&nbsp; 📍 {job['location']}
                {f"&nbsp;|&nbsp; 📅 {job['date']}" if job.get('date') else ""}
              </p>
              <div style="margin-bottom:10px;">{tags_html}</div>
            </div>
            <div style="margin-left:16px;">
              <span style="background:{color};color:#fff;padding:2px 10px;
                           border-radius:999px;font-size:11px;">{job['source']}</span>
            </div>
          </div>
          <a href="{job['url']}"
             style="display:inline-block;background:{color};color:#fff;
                    padding:8px 20px;border-radius:8px;text-decoration:none;
                    font-size:13px;font-weight:600;">
            View &amp; Apply →
          </a>
        </div>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"></head>
    <body style="margin:0;padding:0;background:#f5f7fa;font-family:'Segoe UI',Arial,sans-serif;">
      <div style="max-width:680px;margin:30px auto;background:#f5f7fa;padding:0 16px 40px;">

        <!-- Header -->
        <div style="background:linear-gradient(135deg,#1a1a2e 0%,#16213e 60%,#0f3460 100%);
                    border-radius:16px;padding:36px 32px;margin-bottom:24px;text-align:center;">
          <div style="font-size:32px;margin-bottom:8px;">🚀</div>
          <h1 style="color:#fff;margin:0 0 8px;font-size:26px;font-weight:700;letter-spacing:-0.5px;">
            Daily DevOps Job Digest
          </h1>
          <p style="color:#a8b2d8;margin:0;font-size:14px;">{today}</p>
          <div style="margin-top:16px;background:rgba(255,255,255,0.1);
                      border-radius:8px;padding:10px 20px;display:inline-block;">
            <span style="color:#64ffda;font-size:22px;font-weight:700;">{len(jobs)}</span>
            <span style="color:#a8b2d8;font-size:14px;margin-left:6px;">new opportunities found</span>
          </div>
        </div>

        <!-- Jobs -->
        <div style="margin-bottom:24px;">
          {job_cards}
        </div>

        <!-- Footer -->
        <div style="text-align:center;padding:20px;color:#b2bec3;font-size:12px;">
          <p style="margin:0 0 4px;">🤖 Auto-generated by your DevOps Job Digest bot</p>
          <p style="margin:0;">Sources: RemoteOK · WeWorkRemotely · LinkedIn · Himalayas · Remotive</p>
        </div>

      </div>
    </body>
    </html>
    """


def send_email(html_body, job_count):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🚀 {job_count} DevOps Jobs Found — {today}"
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = RECIPIENT_EMAIL

    msg.attach(MIMEText("Your daily DevOps job digest. Please view in an HTML-capable email client.", "plain"))
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())

    print(f"✅ Email sent to {RECIPIENT_EMAIL} with {job_count} jobs")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"\n{'='*50}")
    print(f"  DevOps Job Digest — {today}")
    print(f"{'='*50}\n")

    all_jobs = []
    all_jobs.extend(scrape_remoteok())
    time.sleep(2)
    all_jobs.extend(scrape_weworkremotely())
    time.sleep(2)
    all_jobs.extend(scrape_jobspy_style())
    time.sleep(1)
    all_jobs.extend(scrape_linkedin_rss())

    unique_jobs = deduplicate(all_jobs)
    print(f"\n📋 Total unique jobs: {len(unique_jobs)}")

    if not unique_jobs:
        print("⚠️  No jobs found today. Skipping email.")
        return

    html = build_email_html(unique_jobs)
    send_email(html, len(unique_jobs))


if __name__ == "__main__":
    main()