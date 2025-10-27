
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
SERPER_API_KEY=your_serperapi_key
SERPER_BASE_URL=https://google.serper.dev/search
GEMINI_API_KEY=your_gemini_key
LLM_MODEL=gemini/gemini-2.5-flash
PINECONE_API_KEY=your_pinecone_key
PINECONE_INDEX_NAME=your_pinecone_index_name
PINECONE_INDEX_HOST=your_pinecone_host
PINECONE_ENV=us-west1-gcp

DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_db_password
DB_NAME=your_db_name

TAVILY_API_KEY=your_tavily_key

AUTH_HASH_SCHEME=argon2
JWT_ISSUER=mr-backend
JWT_LEEWAY_SECONDS=30

COOKIE_SECURE=false
COOKIE_SAMESITE=Lax
CORS_ORIGIN=http://localhost:5173/

SMTP_SERVER=smtp.office365.com
SMTP_PORT=587
SMTP_USERNAME=your_email
SMTP_PASSWORD=ypur_email_password

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
=======
# AI-Powered Market Research Application

This is a full-stack application designed to conduct automated market research using an AI agent backend powered by CrewAI and a modern, responsive frontend built with React and Vite.

## ✨ Features

-   **AI Agent Backend**: Utilizes CrewAI to define and run autonomous agents for market analysis tasks.
-   **RESTful API**: A robust backend built with Python (likely FastAPI) to serve data and manage AI tasks.
-   **Interactive Frontend**: A dynamic user interface built with React and TypeScript for submitting research requests and viewing results.
-   **User Authentication**: Secure routes and user management.
-   **Real-time Interaction**: A chatbot-style interface for interacting with the research agents.

## 🛠️ Tech Stack

-   **Backend**: Python, CrewAI, FastAPI (or Flask), Uvicorn
-   **Frontend**: React, TypeScript, Vite, CSS
-   **Database**: (Specify your database, e.g., PostgreSQL, MongoDB, SQLite)

---

## 🚀 Getting Started

Follow these instructions to get a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

You need to have the following software installed on your system:

-   [Python 3.10+](https://www.python.org/downloads/)
-   [Node.js and npm](https://nodejs.org/en)
-   [Git](https://git-scm.com/)

### Installation

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/vaishnavi1124/market-research.git](https://github.com/vaishnavi1124/market-research.git)
    cd market-research
    ```

2.  **Setup the Backend:**
    ```bash
    # Navigate to the backend directory
    cd backend

    # Create a virtual environment
    python -m venv venv

    # Activate the virtual environment
    # On Windows:
    .\venv\Scripts\activate
    # On macOS/Linux:
    source venv/bin/activate

    # Install the required Python packages
    pip install -r requirements.txt

    # Create a .env file from the example
    # (You should create a .env.example file first)
    # and add your environment variables like API keys
    # Example .env file:
    # OPENAI_API_KEY="your_secret_api_key_here"
    # DATABASE_URL="your_database_connection_string"
    ```

3.  **Setup the Frontend:**
    ```bash
    # Navigate to the frontend directory from the root
    cd frontend

    # Install the required npm packages
    npm install

    # Create a .env file and add your frontend-specific
    # environment variables.
    # Example .env file:
    # VITE_API_BASE_URL="[http://127.0.0.1:8000](http://127.0.0.1:8000)"
    ```

---

## 🏃‍♂️ Running the Application

You need to run the backend and frontend servers in two separate terminals.

1.  **Run the Backend Server:**
    ```bash
    # In the /backend directory
    uvicorn main:app --reload
    ```
    The backend API will be available at `http://127.0.0.1:8000`.

2.  **Run the Frontend Development Server:**
    ```bash
    # In the /frontend directory
    npm run dev
    ```
    The frontend application will be available at `http://localhost:5173`. Open this URL in your web browser to use the application.

---

## 🤝 Contributing

Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

1.  Fork the Project
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4.  Push to the Branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request

## 📜 License

Distributed under the MIT License. See `LICENSE` for more information.
>>>>>>> 3ba2fe317276c6fd5c9bf0c0e40a1c2a3805665f
