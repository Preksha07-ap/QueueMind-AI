# QueueMind AI - System Architecture & Foundation Design

## 1. Overview

**QueueMind AI** is an intelligent IT Helpdesk Management System designed for modern enterprise support operations. The platform introduces intelligent automation across complaint ingestion, duplicate ticket detection, priority prediction, team routing, and automated troubleshooting using structure-aware Retrieval-Augmented Generation (RAG).

---

## 2. Architectural Layers

### Frontend (Presentation Layer)
- **Framework:** React 19 + TypeScript + Vite
- **Styling:** Tailwind CSS (v4) with modern dark/light SaaS design tokens
- **Routing:** React Router v7 (`createBrowserRouter`)
- **State & Context:** React Context API (`AppContext`)
- **HTTP Client:** Axios configured with base URL, timeout, and interceptors
- **Icons & Data Visualization:** Lucide React, Recharts

### Backend (Application & Domain Layer)
- **Framework:** FastAPI (Python 3.13+)
- **Validation & Serialization:** Pydantic v2 & Pydantic Settings
- **API Standards:** RESTful OpenAPI / Swagger documentation (`/docs`, `/redoc`)
- **CORS Management:** Dynamic CORS middleware supporting development and production origins
- **Testing:** Pytest + TestClient + Asyncio

### Persistence (Database & Migration Layer)
- **Database Engine:** MySQL 8.0+
- **ORM:** SQLAlchemy 2.0 (Declarative Base & connection pooling)
- **Migrations:** Alembic (database schema evolution)
- **Connection Driver:** PyMySQL with cryptography

### Future AI / ML Subsystem (Phase 2+)
- **Classification & Priority:** Scikit-learn & Sentence Transformers
- **Vector Search:** Qdrant vector database for semantic similarity and duplicate detection
- **Troubleshooting & Resolution RAG:** Ollama running local/configurable LLMs (Qwen 2.5 / Llama 3) with organizational documents, runbooks, and previous resolution embeddings.

---

## 3. Directory Layout & Module Responsibilities

### Frontend Structure (`/frontend`)
```
frontend/
├── src/
│   ├── assets/        # Static imagery, branding SVGs, and graphics
│   ├── components/    # Reusable UI elements (Navbar, Footer, Modals, Badges)
│   ├── context/       # React context providers for application-wide state
│   ├── hooks/         # Custom React hooks (e.g., useHealthCheck)
│   ├── layouts/       # Structural shell wrappers (RootLayout, AuthLayout, DashboardLayout)
│   ├── pages/         # Page-level route views (LandingPage, future TicketDashboard)
│   ├── routes/        # Router configuration and protected route guards
│   ├── services/      # API communication clients and HTTP abstraction layer
│   ├── types/         # TypeScript interfaces, types, and API response contracts
│   └── utils/         # Helper functions, constants, formatting, and date utilities
├── public/            # Static public assets (favicon.svg, manifest)
├── vite.config.ts     # Vite bundler, plugin, and path alias configuration
└── tsconfig.json      # TypeScript compiler configuration
```

### Backend Structure (`/backend`)
```
backend/
├── app/
│   ├── ai/            # AI/ML logic: classification, RAG retrieval, duplicate detector
│   ├── api/           # API router tree (v1 endpoints, health check, ticket routes)
│   │   └── v1/        # Version 1 API routes
│   │       └── endpoints/
│   ├── core/          # Application configuration (pydantic-settings), security, constants
│   ├── database/      # SQLAlchemy session manager, connection pool, and Declarative Base
│   ├── models/        # SQLAlchemy ORM models (Tenant, User, Ticket, KnowledgeDocument)
│   ├── schemas/       # Pydantic data schemas for request validation & response formatting
│   ├── services/      # Domain business logic isolated from HTTP routing
│   └── main.py        # FastAPI ASGI entrypoint, middleware, lifespan, router registry
├── tests/             # Automated test suite (Pytest, endpoint integration tests)
├── requirements.txt   # Backend Python dependency specifications
└── .env.example       # Template for environment-specific secrets & configurations
```

---

## 4. Multi-Tenancy Architecture Principles

QueueMind AI is architected from day one for multi-tenancy:
1. **Tenant Isolation:** Every organization has an isolated namespace (`org_id` / `tenant_id`) attached to users, tickets, and knowledge bases.
2. **Context-Aware RAG:** Vector collections in Qdrant will be partitioned or filtered by `tenant_id`, ensuring organizational documents and ticket histories never bleed across tenants.
3. **Role-Based Access Control (RBAC):** Organization Admin, Help Desk Operator, Support Engineer, and Employee End-User tiers.
