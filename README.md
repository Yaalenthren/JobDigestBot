# 🚀 DevOps Job Digest

A GitHub Actions bot that scrapes DevOps & Cloud engineering jobs daily and sends them straight to your inbox every morning at **6:00 AM Sri Lanka time**.

## 📋 What it does

- Scrapes **RemoteOK**, **WeWorkRemotely**, **Remotive**, **Himalayas**, and **LinkedIn**
- Filters for DevOps, Cloud, SRE, Platform, and Kubernetes roles
- Deduplicates listings
- Sends a beautiful HTML digest email with one-click apply links
- Runs automatically every day — zero effort from you

---

## ⚙️ Setup (5 minutes)

### Step 1 — Fork or create this repo on GitHub
Push all these files to a new GitHub repo (can be private).

### Step 2 — Get a Gmail App Password
Gmail requires an **App Password** (not your regular password) for SMTP:

1. Go to your Google Account → **Security**
2. Enable **2-Step Verification** if not already done
3. Go to **Security → App Passwords**
4. Select app: **Mail** → Select device: **Other** → type `JobDigestBot`
5. Copy the 16-character password generated

### Step 3 — Add GitHub Secrets
In your GitHub repo → **Settings → Secrets and variables → Actions → New repository secret**

Add these 3 secrets:

| Secret Name | Value |
|---|---|
| `RECIPIENT_EMAIL` | Your personal email (where you want to receive jobs) |
| `SENDER_EMAIL` | The Gmail address you're sending from |
| `SENDER_APP_PASSWORD` | The 16-char App Password from Step 2 |

### Step 4 — Enable GitHub Actions
Go to your repo → **Actions tab** → Click **"I understand my workflows, go ahead and enable them"**

### Step 5 — Test it immediately
Go to **Actions → Daily DevOps Job Digest → Run workflow** to trigger a manual run and verify your email arrives.

---

## 📁 Project Structure

```
devops-job-digest/
├── .github/
│   └── workflows/
│       └── daily_digest.yml    # GitHub Actions schedule
├── scripts/
│   └── job_digest.py           # Main scraper + email sender
├── requirements.txt
└── README.md
```

---

## 🕕 Schedule
The workflow runs at `00:30 UTC` which is **6:00 AM Sri Lanka time (UTC+5:30)**.

To change the time, edit `.github/workflows/daily_digest.yml`:
```yaml
- cron: '30 0 * * *'   # minute hour * * *  (UTC)
```

---

## 📬 Email Preview

The digest email includes:
- Job title, company, and location
- Source badge (RemoteOK, Remotive, etc.)
- Skill tags
- Direct **"View & Apply →"** button per job

---

## 🔧 Customization

In `scripts/job_digest.py`, you can adjust:
- `KEYWORDS` list — add or remove job titles
- Scraper functions — add new job boards
- Email template — modify the HTML design

---

## 💡 Why GitHub Actions?
- **Free** — GitHub gives 2,000 minutes/month on free accounts
- **No server needed** — fully managed
- **Reliable** — runs even if your PC is off
- **Great for your DevOps resume** — shows CI/CD pipeline knowledge
