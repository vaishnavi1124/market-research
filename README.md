
# 🧠 Market Research & Sentiment Analysis System

This project is an AI-powered **Market Research Automation System** that integrates multiple APIs and services
(Google Serper, Gemini LLM, Tavily, Pinecone, MySQL, and SMTP) to automate data collection, sentiment analysis,
and report generation.

---

## 🏗️ Architecture Overview

```
                        ┌────────────────────────────┐
                        │        Frontend (UI)       │
                        │   React / Vite (Port 5173) │
                        └─────────────┬──────────────┘
                                      │  REST / JSON
                                      ▼
                        ┌────────────────────────────┐
                        │        Backend API         │
                        │   FastAPI / Flask (Python) │
                        └─────────────┬──────────────┘
                                      │
             ┌────────────────────────┼────────────────────────┐
             │                        │                        │
             ▼                        ▼                        ▼
 ┌────────────────────┐     ┌────────────────────┐     ┌────────────────────┐
 │   Google Serper     │     │   Gemini LLM API   │     │   Tavily API       │
 │(Web Search Engine)  │     │(Text Analysis,     │     │(Market Insights)   │
 │  SERPER_BASE_URL     │     │ Summarization)     │     │  TAVILY_API_KEY    │
 └────────────────────┘     └────────────────────┘     └────────────────────┘
             │                        │
             ▼                        ▼
 ┌────────────────────────────────────────────────────┐
 │                Pinecone Vector DB                  │
 │  • Stores embeddings for text/sentiment analysis   │
 │  • Fast semantic search (similarity queries)       │
 └────────────────────────────────────────────────────┘
                                      │
                                      ▼
                        ┌────────────────────────────┐
                        │        MySQL Database      │
                        │ Stores structured results  │
                        │   (market_research DB)     │
                        └────────────────────────────┘
                                      │
                                      ▼
                        ┌────────────────────────────┐
                        │        SMTP Server         │
                        │ Email notifications (O365) │
                        └────────────────────────────┘
```

---

## ⚙️ Environment Variables

```env
ERPER_API_KEY=**************ec106ba4f10
SERPER_BASE_URL=https://google.serper.dev/search
GEMINI_API_KEY=**************FxGWAnI
LLM_MODEL=gemini/gemini-2.5-flash
PINECONE_API_KEY=**************ExWvEYPCRynnQb8Cz8pxPiV
PINECONE_INDEX_NAME=sentiment-index
PINECONE_INDEX_HOST=https://sentiment-index-x1942q1.svc.aped-4627-b74a.pinecone.io
PINECONE_ENV=us-west1-gcp

DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=root
DB_NAME=market_research

TAVILY_API_KEY=**************JpbSK

AUTH_HASH_SCHEME=argon2
JWT_ISSUER=mr-backend
JWT_LEEWAY_SECONDS=30

COOKIE_SECURE=false
COOKIE_SAMESITE=Lax
CORS_ORIGIN=http://localhost:5173/

SMTP_SERVER=smtp.office365.com
SMTP_PORT=587
SMTP_USERNAME=sales@genintel.in
SMTP_PASSWORD=**************501

CREWAI_TRACING_ENABLED=true
```

---

## 🚀 How It Works

1. **Frontend (React)** – User submits a query (e.g., "AI startup market sentiment 2025").  
2. **Backend (FastAPI)** – Fetches data using Google Serper & Tavily APIs.  
3. **Gemini LLM** – Performs NLP summarization and sentiment tagging.  
4. **Pinecone Vector DB** – Stores text embeddings for similarity searches.  
5. **MySQL** – Saves structured summaries and market insights.  
6. **SMTP (Office365)** – Sends report via email to user.

---

## 🧠 Workflow Example

- **Input:** “Market sentiment of electric vehicles in 2025”  
- **Process:**  
  1. Google & Tavily APIs gather live data.  
  2. Gemini LLM summarizes and classifies sentiment.  
  3. Embeddings stored in Pinecone.  
  4. Summary saved in MySQL.  
  5. Email notification sent via SMTP.

---

## 🔒 Security

- Uses Argon2 for password hashing.  
- JWT-based secure authentication.  
- CORS restricted to `localhost:5173`.  
- Environment keys are masked and stored in `.env`.

---

## 🧩 Setup Instructions

```bash
# Clone the repository
git clone <your_repo_url>
cd <your_project_folder>

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Create .env file with above variables

# Run server
uvicorn app.main:app --reload
```

---

## 📈 Future Enhancements

- Add AI-powered visualization dashboard  
- Integrate more LLM providers (Claude / GPT-5)  
- Implement analytics and report scheduling  

---

© 2025 GenIntel | Market Research Automation
