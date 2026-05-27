<div align="center">

# Agentic HR Onboarding System

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Gemini](https://img.shields.io/badge/Gemini_2.5_Flash-AI_Core-4285F4?style=flat-square&logo=google&logoColor=white)](https://ai.google.dev)
[![Neon PostgreSQL](https://img.shields.io/badge/Neon_PostgreSQL-Cloud_Database-003545?style=flat-square&logo=postgresql&logoColor=white)](https://neon.tech)
[![CSS3](https://img.shields.io/badge/Vanilla_CSS-Premium_Design-1572B6?style=flat-square&logo=css3&logoColor=white)]()
[![Hosted on Render](https://img.shields.io/badge/Render-Backend_Live-46E3B7?style=flat-square&logo=render&logoColor=black)](https://render.com)
[![Hosted on Netlify](https://img.shields.io/badge/Netlify-Frontend_Live-00C7B7?style=flat-square&logo=netlify&logoColor=white)](https://netlify.com)

<br/>

An autonomous, email-native AI agent that conducts end-to-end candidate onboarding. The system processes email communications, extracts structured data, prompts candidates for missing information, maintains conversation state, and coordinates follow-ups without human intervention.

[Getting Started](#getting-started) · [System Architecture](#system-architecture) · [Connection Resilience](#connection-resilience) · [Engineering Highlights](#engineering-highlights)

</div>

---

## Production Engineering Highlights

Unlike prototype AI tools that run solely in local environments, this system is designed to handle production-tier constraints, ephemeral cloud hosting, and database rate limits:

*   **Self-Healing Auto-Wake Queue:** Because the backend is hosted on Render's free tier, the container hibernates after 15 minutes of inactivity. To prevent connection drops or visual hangs, the frontend implements a parallel 2-second connection monitor. If the server is sleeping, it alerts the user with an elegant warm-up banner and initiates a 10-attempt exponential backoff retry strategy.
*   **Resource-Optimized Background Threading:** Background Gmail IMAP polling is configured to run at 15-second intervals rather than a aggressive loop. This preserves container CPU usage and respects Neon PostgreSQL database connection pooling boundaries.
*   **Ephemere State Preservation:** While the container is hibernating, incoming candidate replies are queued safely as unseen messages in Gmail. Once an HTTP request wakes the server, the FastAPI lifespan context automatically resumes the background thread, processing all queued responses in a single batch.
*   **Bespoke Vanilla CSS Architecture:** The dashboard bypasses generic CSS frameworks in favor of custom HSL-tailored tokens, responsive glassmorphic interfaces, sticky-header table viewports with custom scrollbars, and a `#brandHome` reset trigger that synchronizes state across the application.
*   **Cloud PostgreSQL Integration:** Database architecture has been migrated from local SQLite to serverless Neon PostgreSQL to ensure persistent, concurrent storage that survives container rebuilds.

---

## System Flow

```mermaid
sequenceDiagram
    participant HR as HR Dashboard (Netlify)
    participant API as FastAPI Server (Render)
    participant SMTP as SMTP (Gmail)
    participant IMAP as IMAP Listener (15s Loop)
    participant AI as Gemini 2.5 Flash
    participant MEM as Thread Memory (JSON)
    participant DB as Neon PostgreSQL

    HR->>API: POST /api/initiate (candidate email)
    API->>SMTP: Send welcome onboarding email
    SMTP-->>Candidate: Welcome email sent
    
    Note over API,IMAP: Server hibernates after 15 mins of HTTP inactivity
    Candidate-->>SMTP: Candidate replies (marked UNSEEN in inbox)
    
    HR->>API: Wake up server (Auto-Wake Queue handles cold start)
    API->>IMAP: Lifespan initiates background listener
    IMAP->>IMAP: Detects UNSEEN email (polled every 15s)
    
    IMAP->>MEM: Load conversation state
    IMAP->>AI: Full thread context + candidate response
    AI->>AI: Extract fields (Name, Email, Qualification, DOB, Location)

    alt Data Incomplete
        AI->>SMTP: Reply asking for missing fields
        MEM->>MEM: Update local JSON thread memory
    else Data Complete (Pydantic validated)
        AI->>DB: Persist candidate to PostgreSQL
        AI->>SMTP: Send onboarding completion email
        MEM->>MEM: Mark thread as COMPLETED
    end

    alt No Candidate Response
        MEM->>IMAP: Trigger escalating reminders (5, 10, 20 mins)
        IMAP->>SMTP: Dispatch reminder email
    end

    alt Post-Onboarding Inquiry
        Candidate-->>IMAP: Conversational question (e.g., "What documents do I need?")
        IMAP->>AI: AI Q&A Mode
        AI->>SMTP: Direct contextual answer email
    end
```

---

## Connection Resilience

To mitigate serverless cold-start latency, the frontend utilizes an asynchronous retry queue with a parallel wake-up threshold. This ensures the user is informed of the backend state within 2 seconds instead of seeing a frozen application:

```javascript
// Connection queue handles pending TCP sockets during container boot
const alertTimeout = setTimeout(() => {
    if (warmUpAlert) {
        warmUpAlert.classList.remove("d-none");
        alertText.innerHTML = `Deployed on Render's Free tier. The server automatically sleeps during inactivity. <br><strong>Initiating server wake-up...</strong> Please allow 30-50 seconds for the container to start.`;
    }
}, 2000);

try {
    const res = await fetchWithRetry(API, {}, 10, 5000); // Polling queue up to 10 attempts
    clearTimeout(alertTimeout);
    warmUpAlert.classList.add("d-none");
    // Render dashboard components
} catch (error) {
    clearTimeout(alertTimeout);
    showToast("Failed to connect to the server: " + error.message, "danger");
}
```

---

## Architecture and Design Decisions

### Key Decisions

| Decision | Choice | Rationale |
|---|---|---|
| **Database Engine** | Neon PostgreSQL | Cloud-managed relational database. Ensures data persistency across ephemeral Render container environments. |
| **UX Resilience** | Auto-Wake Fallback | Parallel monitor handles long cold starts, preventing standard browser timeouts and freezing. |
| **IMAP Polling** | 15-Second Windows | Drastically reduces background thread overhead, keeping resources within free tier boundaries while maintaining responsiveness. |
| **State Management** | JSON Ephemeral Memory | Files are maintained with a 24-hour TTL to prevent DB bloat from abandoned onboarding drafts. |
| **AI Validation** | Pydantic v2 Parsing | Gemini outputs are never trusted directly. Pydantic serves as a strict typing boundary for qualifications, Indian cities, and past birth dates. |

---

## Project Structure

```
Employee-OnBoarding-System/
│
├── backend/
│   ├── main.py               # FastAPI app config with lifespan background listener managers
│   ├── database.py           # Cloud Neon PostgreSQL connection pooling & SQLAlchemy sessions
│   ├── models.py             # Relational schema mappings
│   ├── schema.py             # Pydantic validation rules and format normalizers
│   ├── email_listener.py     # Background IMAP scanning thread and reminder state scheduler
│   └── routers/
│       ├── employee.py       # Candidate REST API handlers (CRUD endpoints)
│       └── email_agent.py    # Conversation state initiator and AI parser controls
│
└── frontend/
    ├── index.html            # Admin dashboard UI
    ├── script.js             # Asynchronous DOM rendering, retry queues, and search hooks
    └── style.css             # Style tokens, flex grids, and sticky scroll behaviors
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- A Gmail account with an App Password configured
- A Google Gemini API Key
- A cloud PostgreSQL connection string

### 1. Clone the Repository

```bash
git clone https://github.com/GitbyShantanu/Employee-OnBoading-System.git
cd Employee-OnBoading-System
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Environment Configuration

Create a `.env` file within the `backend/` directory:

```env
DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require
GOOGLE_API_KEY=your_gemini_api_key_here
EMAIL_USER=your_gmail_address@gmail.com
EMAIL_APP_PASSWORD=your_16_char_app_password
```

### 4. Boot the Server

```bash
cd backend
uvicorn main:app --reload
```

---

## Developer Profile

Developed by **[Shantanu](https://github.com/GitbyShantanu)**, a backend and AI systems developer building production-grade software workflows.

This project is a core feature of the **ShanTech** portfolio, demonstrating robust asynchronous architectures and AI integration patterns.