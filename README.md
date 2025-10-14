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