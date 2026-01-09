# OmniSource Chatbot 

![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688)
![Streamlit](https://img.shields.io/badge/Streamlit-1.25%2B-FF4B4B)
![LangGraph](https://img.shields.io/badge/LangGraph-Agentic-orange)
<img width="1023" height="791" alt="architecture" src="https://github.com/user-attachments/assets/bd13daff-8f7a-40d2-8a11-3b434b642590" />

**OmniSource** is an intelligent, multi-source chatbot designed to bridge the gap between unstructured data (PDF documents) and structured data (Excel/CSV spreadsheets). 

By leveraging **LangGraph** for agent orchestration and **Google Gemini** for reasoning, OmniSource dynamically routes user queries to the most appropriate retrieval engine generating SQL queries for spreadsheet analysis or performing semantic vector searches for document retrieval all within a seamless conversational interface.

---
<img width="1918" height="1016" alt="3" src="https://github.com/user-attachments/assets/8c0ce3a1-8be8-444e-948d-bd08b3d10352" />
<img width="1918" height="1021" alt="4" src="https://github.com/user-attachments/assets/bb7c1442-ad85-4335-923a-4c67b3712886" />

---


## Key Features

* **Intelligent Router Agent:** Automatically classifies user intent to route queries to the Excel Agent (SQL), PDF Retriever (Vector Search), or both.
* **Conversational Interface:** Maintains multi-turn context, allowing for follow-up questions and natural dialogue flow.
* **Precise Citations:** Every answer includes exact source references (e.g., *"PDF: omnisource_1.pdf, page 42"* or *"Excel: social_listening table"*).
* **Analytics Dashboard:** A built-in dashboard to track query volume, source usage distribution, response times, and user satisfaction.
* **Feedback Loop:** Integrated thumbs-up/down mechanism to collect user feedback for continuous improvement.
* **Multi-Modal Data Handling:** Seamlessly processes 1000+ page PDFs and complex CSV datasets simultaneously.

---

## System Architecture

OmniSource relies on a decoupled architecture with a FastAPI backend serving a Streamlit frontend. The core logic is powered by a **LangGraph** state machine.

### High-Level Data Flow

1.  **User Input:** Captured via Streamlit.
2.  **Routing:** The **Router Agent** analyzes the query.
3.  **Retrieval:**
    * *Structured Data:* The **Excel Agent** converts natural language to SQL and queries the SQLite database.
    * *Unstructured Data:* The **PDF Retriever** performs semantic search against the ChromaDB vector index.
4.  **Synthesis:** The **Answer Generator** combines retrieved context and generates a response with citations.
5.  **Logging:** Metadata and performance metrics are logged to the Analytics DB.

---

## Tech Stack

| Component | Technology | Description |
| :--- | :--- | :--- |
| **LLM** | Google Gemini 2.5 Flash | Core reasoning and text generation |
| **Orchestration** | LangGraph | State machine and agent workflow management |
| **Backend** | FastAPI | High-performance API server |
| **Frontend** | Streamlit | Interactive UI for Chat and Analytics |
| **Vector Store** | ChromaDB | Embeddings storage for PDF retrieval |
| **SQL Store** | SQLite | Relational storage for CSV/Excel data |
| **Data Processing** | Pandas / LangChain | Data ingestion, chunking, and manipulation |

---

## Project Structure

```bash
Omnisource_Chatbot/
├── backend/                    # FastAPI backend application
│   ├── __init__.py
│   ├── main.py                 # App entry point & API endpoints
│   ├── graph.py                # LangGraph agent orchestration & logic
│   ├── llm.py                  # Gemini API wrapper
│   ├── db.py                   # Database connection managers
│   ├── pdf_ingestion.py        # ChromaDB & PDF processing
│   ├── excel_ingestion.py      # SQLite & CSV processing
│   └── models.py               # Pydantic data models
├── frontend/                   # Streamlit frontend application
│   └── app.py                  # UI logic
├── Data/                       # Source files
│   ├── omnisource_1.pdf        
│   └── social-listening.csv    
├── db/                         # Persisted databases 
│   ├── excel.db                
│   └── analytics.db             
├── chroma_pdfs/                # Vector store 
├── requirements.txt            # Python dependencies
└── .env                        # Environment variables
```

## Installation & Setup

### Prerequisites
* **Python 3.9** or higher
* A **Google gemini API Key** (for Gemini) (Get this from AI studio)

### 1. Clone the Repository
```bash
git clone 
cd OmniSource_Chatbot
```
### 2. Create a Virtual Environment
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate
```
## 3. Install Dependencies
```bash
pip install -r requirements.txt
```
## 4. Configuration
Create a .env file in the root directory:

```bash

# .env file
GEMINI_API_KEY=your_google_gemini_api_key_here
GEMINI_MODEL_NAME=gemini-2.5-flash
OMNISOURCE_BACKEND_URL=http://localhost:8000
```
## 5. Running the Application
You will need to run the backend and frontend in separate terminals.

**Terminal 1:** Backend (FastAPI)
This will start the server and automatically ingest data from the Data/ folder upon startup.
```Bash
python -m uvicorn backend.main:app --reload --port 8000
#The API will be available at http://localhost:8000

```

**Terminal 2:** Frontend (Streamlit)
```Bash
streamlit run frontend/app.py
#The UI will open automatically in your browser at http://localhost:8501
```

# Thank you for checking out the project! Loads of love and blessings your way <3
