# QueueMind AI – Intelligent IT Helpdesk Management System

QueueMind AI is an enterprise-grade, multi-tenant IT helpdesk platform that orchestrates incident reporting, intelligent ticket classification, priority prediction, semantic duplicate detection, and structure-aware RAG-powered troubleshooting for support engineers.

---

## 1. Architecture & Technology Stack

### Frontend
- **Framework:** React 19 + TypeScript + Vite
- **Styling:** Tailwind CSS (v4)
- **Routing:** React Router v7
- **Icons & Visuals:** Lucide React, Recharts
- **HTTP Client:** Axios (configured with central base URL and interceptors)

### Backend
- **Framework:** FastAPI (Python 3.13+)
- **Data Validation:** Pydantic v2 & Pydantic Settings
- **ORM & Migrations:** SQLAlchemy 2.0 & Alembic
- **Database Driver:** PyMySQL & Cryptography (MySQL 8.0+)
- **API Standards:** OpenAPI / Swagger interactive documentation

### Future AI / ML Engine (Planned Phase 2+)
- **Classification & Priority Prediction:** Scikit-learn & Sentence Transformers
- **Vector Search & Duplication Engine:** Qdrant Vector Database
- **Local / Configurable LLM Inference:** Ollama (Qwen 2.5 / Llama 3)
- **Contextual Knowledge Retrieval:** Structure-aware RAG over organizational documents and resolution logs

---

## 2. Project Directory Structure

```
QueueMind-AI/
│
├── frontend/                     # React + TypeScript + Vite Client Application
│   ├── public/                   # Static browser assets and favicon
│   ├── src/
│   │   ├── assets/               # Brand imagery and vector graphics
│   │   ├── components/           # Reusable UI components (Navbar, Footer, etc.)
│   │   │   └── common/
│   │   ├── context/              # React context providers for shared state
│   │   ├── hooks/                # Custom hooks (e.g., useHealthCheck)
│   │   ├── layouts/              # Shell layout wrappers (RootLayout)
│   │   ├── pages/                # Route pages (LandingPage)
│   │   ├── routes/               # React Router configuration
│   │   ├── services/             # Axios API client and endpoint services
│   │   ├── types/                # TypeScript interface declarations
│   │   └── utils/                # Configuration constants and helper utilities
│   ├── index.html                # Vite HTML entry point
│   ├── package.json              # Frontend dependencies and npm scripts
│   ├── tsconfig.json             # TypeScript project references
│   ├── tsconfig.app.json         # Client TypeScript compiler settings
│   └── vite.config.ts            # Vite bundler, alias, and Tailwind configuration
│
├── backend/                      # FastAPI Python Application
│   ├── app/
│   │   ├── ai/                   # AI/ML subsystems (classification, RAG, duplicate detection)
│   │   ├── api/                  # API routers
│   │   │   └── v1/               # Version 1 router tree
│   │   │       └── endpoints/    # Individual controllers (health, etc.)
│   │   ├── core/                 # App configuration (Pydantic Settings) & security
│   │   ├── database/             # SQLAlchemy engine, session maker, Declarative Base
│   │   ├── models/               # SQLAlchemy ORM models (Tenants, Tickets, Users)
│   │   ├── schemas/              # Pydantic schemas for request/response serialization
│   │   ├── services/             # Domain business logic layer
│   │   └── main.py               # FastAPI application entrypoint, CORS, and lifespans
│   ├── tests/                    # Backend automated tests (Pytest)
│   ├── requirements.txt          # Python dependencies
│   └── .env.example              # Environment variables template
│
├── docs/                         # Architecture and technical documentation
│   └── architecture.md           # System architecture overview
├── .gitignore                    # Git ignore specifications
└── README.md                     # Project overview and run guide
```

---

## 3. Installation & Setup Instructions

### Prerequisites
- **Node.js:** v18.0.0+ (Tested with v22+)
- **npm:** v9.0.0+ (Tested with v10+)
- **Python:** 3.10+ (Tested with 3.13)
- **MySQL Server:** (For future database phases)

---

### Backend Setup

1. **Navigate to the backend directory:**
   ```bash
   cd backend
   ```

2. **Create a Python virtual environment:**
   - On Windows (PowerShell):
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```
   - On Linux / macOS:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

3. **Install backend dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   ```bash
   cp .env.example .env
   ```
   *(Update `.env` with your local database credentials if needed. Default values will work for initial health check.)*

5. **Run backend unit and integration tests:**
   ```bash
   pytest
   ```

6. **Start the FastAPI development server:**
   ```bash
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```
   The backend API will be accessible at:
   - **Health Check Endpoint:** [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)
   - **Interactive Swagger Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
   - **ReDoc Documentation:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

### Frontend Setup

1. **Navigate to the frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install frontend dependencies:**
   ```bash
   npm install
   ```

3. **Build the frontend (verify TypeScript and Tailwind compilation):**
   ```bash
   npm run build
   ```

4. **Start the Vite development server:**
   ```bash
   npm run dev
   ```
   The frontend application will be accessible at:
   - **Web UI:** [http://localhost:5173](http://localhost:5173)

---

## 4. Phase 1 Verification Checklist

- [x] Vite + React 19 + TypeScript frontend scaffolding
- [x] Tailwind CSS v4 styling with `@tailwindcss/vite`
- [x] React Router setup with clean SaaS layout
- [x] Axios service configured with custom interceptors and base URL
- [x] FastAPI application with lifespan management and CORS middleware
- [x] Health-check endpoint at `/api/v1/health`
- [x] Live frontend health check verification against backend
- [x] SQLAlchemy Base and Session pooling configured
- [x] Pytest suite testing root and healthcheck endpoints
- [x] Environment variable management via `.env.example`
- [x] Comprehensive root `.gitignore`
