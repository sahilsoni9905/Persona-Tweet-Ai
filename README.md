# Persona Tweet

> An AI system that learns your exact Twitter writing style and automates posting, mention replies, and feed engagement — running 24/7 with zero ongoing API read costs.

---

## Demo

[![Persona Tweet — Full Demo](assets/demo_thumbnail.svg)](https://www.youtube.com/watch?v=zOGfuBoqnOc)

> Click to watch the full walkthrough on YouTube.

---

## Screenshots

**Generate tab — AI generates tweets in your voice, scored by style match. Reply to any tweet by pasting the text.**

![Generate Tab](assets/Screenshot%202026-07-05%20014013.png)

**Schedule tab — Auto-Post, Auto-Reply, and Feed Reply (browser automation) all controllable from UI.**

![Schedule Tab](assets/Screenshot%202026-07-05%20014023.png)

**History tab — Every post and feed reply logged with status badges.**

![History Tab](assets/Screenshot%202026-07-05%20014035.png)

---

## What It Does

Persona Tweet has **3 automation modules**, all driven by the same AI pipeline built on your personal tweet history.

### Module 1 — Auto Post
Generates original tweets that sound like you wrote them and posts on a schedule.

- Pulls style examples from your tweet corpus (ChromaDB vector search)
- Generates 3 candidates via LLM (Groq / Anthropic)
- Scores each with a trained Logistic Regression classifier
- Picks the best match; retries with corrective feedback if needed
- Posts via Twitter API v2 or saves as draft

### Module 2 — Mention Reply
When someone @mentions you, auto-replies in your reply voice — trained on how you've actually responded to people before.

- Fetches new @mentions via Tweepy
- Retrieves your most similar **past reply tweets** from ChromaDB (`source="reply"`)
- LLM uses those as few-shot examples: "here's how you've replied to similar things"
- Posts threaded reply; falls back to `@username` tweet on 403

### Module 3 — Feed Reply (Browser Automation)
Replies to tweets on your home feed even when nobody mentioned you. Zero API read cost.

- One-time login via Edge browser → session saved as cookies
- Headless browser reads your feed on a schedule
- AI generates a reply, types it with human-like keystroke delays, posts it
- Max 3 replies/cycle · Max 8/day · Active 9am–11pm · 30% random skip

---

## AI Pipeline

```
Your Twitter Archive
     │
     ├── Original posts → ChromaDB  source="own"     (style corpus)
     └── Your replies   → ChromaDB  source="reply"   (reply behaviour corpus)
                │
         KMeans clustering (4 topic groups)
                │
         New tweet / mention / feed tweet arrives
                │
         Embed → ChromaDB similarity search
                │
         6 most relevant examples retrieved
                │
         LLM prompt (Groq — Llama 3.3 70B)
                │
         Generated tweet / reply
                │
         Style Scorer (LogReg on TF-IDF) → 0.0–1.0
                │
         Post / Draft / Retry with feedback
```

| Component | Role |
|---|---|
| `sentence-transformers` all-MiniLM-L6-v2 | Embeds tweets into 384-dim vectors |
| ChromaDB | Local vector store — similarity search over your corpus |
| KMeans (k=4) | Clusters your tweets into topic groups |
| Logistic Regression | Style scorer — "does this sound like you?" |
| Groq Llama 3.3 70B | LLM for generation (fast, cheap, tweet-length quality) |
| Playwright + Edge | Browser automation for feed replies — zero API cost |
| APScheduler | Background scheduler for all 3 modules |
| Tweepy v2 | Twitter API writes (free tier: 1,500/month) |

---

## What You Need Before Starting

### 1. Twitter Archive (your own tweets)

1. Go to **X.com → Settings → Your Account → Download an archive**
2. Wait for the email (can take a few hours)
3. Extract the zip → place the extracted folder inside `backend/my_twitter_data/`

```
backend/
  my_twitter_data/
    twitter-2026-06-26-abc123.../     ← your extracted archive folder
      data/
        tweets.js                     ← this is what gets imported
```

The system parses this to build your personal style corpus.

---

### 2. LLM API Key (pick one)

| Provider | Where to get | Cost |
|---|---|---|
| **Groq** (recommended) | [console.groq.com](https://console.groq.com) | Free tier available |
| Anthropic | [console.anthropic.com](https://console.anthropic.com) | Pay per use |

Set `USE_MOCK_LLM=false` and `LLM_PROVIDER=groq` in `.env` for real generation.

---

### 3. Twitter Developer App (for Module 1 + 2 only)

> Module 3 (Feed Reply) uses browser automation — **no Twitter API needed**.

1. Go to [developer.twitter.com](https://developer.twitter.com) → Create a new app
2. Under **App Settings → User authentication settings**, set:
   - Permissions: **Read and Write**
   - Type of App: Web App
3. Copy these 5 values into `.env`:

```
TWITTER_API_KEY=
TWITTER_API_SECRET=
TWITTER_ACCESS_TOKEN=       # regenerate AFTER setting Read+Write permission
TWITTER_ACCESS_SECRET=
TWITTER_BEARER_TOKEN=
TWITTER_USER_ID=            # your numeric Twitter ID (e.g. 1834852205746438147)
```

> **Finding your Twitter User ID:** Go to [tweeterid.com](https://tweeterid.com) and enter your @username.

> **Important:** Regenerate your Access Token *after* enabling Read+Write permission, or posting will fail with 403.

---

## Setup & Run

### Install
```bash
cd backend
pip install -r requirements.txt
playwright install msedge
```

### Configure
```bash
# Create .env from example
copy .env.example .env
# Fill in your API keys
```

Minimum `.env` for full functionality:
```env
POST_MODE=draft                   # start safe — switch to live when ready
LLM_PROVIDER=groq
USE_MOCK_LLM=false
GROQ_API_KEY=your_groq_key

TWITTER_API_KEY=...
TWITTER_API_SECRET=...
TWITTER_ACCESS_TOKEN=...
TWITTER_ACCESS_SECRET=...
TWITTER_BEARER_TOKEN=...
TWITTER_USER_ID=your_numeric_id
```

### Start Backend
```bash
cd backend
python -m uvicorn app:app --host 0.0.0.0 --port 8801 --reload
```

### Open Frontend
Open `frontend/index.html` in your browser (or use VS Code Live Server).

---

## First-Time Setup Flow

```
1. Corpus tab
   → "Import from my_twitter_data/" button
   → Imports your tweets, builds ChromaDB, trains scorer

2. Schedule tab → Feed Reply card
   → "Open Twitter Login" (one time only)
   → Log in with username + password (not Google OAuth)
   → Session saved — never need to log in again

3. Generate tab
   → "Generate tweets" to test your style is captured correctly

4. Schedule tab
   → Start Auto-Post (Module 1)
   → Start Feed Reply (Module 3)

5. Settings tab
   → Change POST_MODE from draft → live when you're confident
```

---

## Safety & Cost

| | Detail |
|---|---|
| Default mode | `draft` — logs everything, never actually posts |
| Twitter API cost | Write-only — no paid reads. Free tier: 1,500 tweets/month |
| Feed reply limits | Max 3/cycle, max 8/day, 9am–11pm only, 30% random skip |
| Bot detection | Keystroke delays (40–90ms/char), human-like pauses, AutomationControlled flag disabled |
| Credentials | `.env` and `my_twitter_data/` are gitignored — never committed |

---

## Tech Stack

| Layer | Tools |
|---|---|
| Backend | Python, FastAPI, APScheduler |
| ML / NLP | sentence-transformers, scikit-learn, ChromaDB |
| LLM | Groq (Llama 3.3 70B) / Anthropic Claude |
| Browser automation | Playwright (Microsoft Edge) |
| Twitter API | Tweepy v2 |
| Frontend | HTML, CSS, Vanilla JS — GitHub dark theme |

---

## Project Structure

```
twitter_post_generator/
├── backend/
│   ├── app.py                    # FastAPI entry point
│   ├── config.py                 # Env vars, paths, POST_MODE
│   ├── routes/
│   │   ├── tweets.py             # Archive import, corpus management
│   │   ├── generate.py           # Tweet + reply generation
│   │   ├── scheduler.py          # Auto-post / mention-reply / feed-reply jobs
│   │   ├── style.py              # Manual post + reference tweet management
│   │   ├── history.py            # Post history log
│   │   └── browser.py            # Playwright session login endpoints
│   ├── services/
│   │   ├── generator.py          # run_generate(), run_generate_reply()
│   │   ├── style_index.py        # ChromaDB operations
│   │   ├── scorer.py             # LogReg scorer train + inference
│   │   ├── llm.py                # LLM interface (Mock / Groq / Anthropic)
│   │   ├── poster.py             # Tweepy post + draft/live mode
│   │   ├── browser.py            # Playwright session management
│   │   └── feed_replier.py       # Feed reply cycle (browser automation)
│   └── utils/
│       ├── archive.py            # Parse tweets.js → posts + replies
│       └── history.py            # History log helpers
├── frontend/
│   ├── index.html                # 5-tab UI
│   ├── style.css                 # GitHub dark theme
│   └── script.js                 # API wiring + scheduler controls
├── notebooks/
│   └── eda_and_clustering.ipynb  # Tweet corpus EDA
├── INTERVIEW_AI_EXPLAINER.md     # Deep-dive: every AI component explained with examples
└── README.md
```
