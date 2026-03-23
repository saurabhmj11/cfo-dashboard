<div align="center">
  <img src="https://img.shields.io/badge/Next.js-16.1-black?style=for-the-badge&logo=next.js&logoColor=white" alt="Next.js" />
  <img src="https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/PostgreSQL-13-336791?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/RabbitMQ-3-FF6600?style=for-the-badge&logo=rabbitmq&logoColor=white" alt="RabbitMQ" />
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker" />
  <img src="https://img.shields.io/badge/Gemini-AI-8E75B2?style=for-the-badge&logo=google&logoColor=white" alt="Gemini AI" />
  
  <br />
  <h1>🚀 AI Financial Analyst Platform</h1>
  <p>An enterprise-grade, microservice-based AI platform providing predictive analytics, real-time market data, and automated financial insights.</p>
</div>

<br />

## 🌟 Executive Summary

This platform is a comprehensive **AI Financial Analyst** designed for scale and resilience. Utilizing a microservices architecture bridged by RabbitMQ and powered by advanced **Gemini AI** capabilities, the system ingests, processes, and generates deep financial intelligence. The seamless, fluid frontend is built with **Next.js 16**, ensuring a world-class enterprise user experience.

---

## 🏗️ Architecture

The system is decoupled into specialized microservices, with **Paperclip v0.3.1** serving as the high-level orchestration control plane for governance and budget management.

```mermaid
graph TD
    User([👨‍💼 User]) ---|UI/Tasks| PC(📎 Paperclip Control Plane)
    PC ===|Orchestration| Adapter(🐍 Python Adapter)
    Adapter ---|Queue Tasks| Broker((🐇 RabbitMQ Broker))
    
    subgraph Autonomous Workforce
        Broker --- Detective(🕵️ Detective Agent)
        Broker --- Forecaster(📈 Forecaster Agent)
        Broker --- Advisor(👔 Advisor Agent)
    end
    
    Detective --- Analytics(🧮 Analytics Engine)
    Forecaster --- AI(🤖 Gemini AI Orchestrator)
    Advisor --- AI
    
    API_Gateway(⚡ FastAPI Gateway) --- DB[(🐘 PostgreSQL Store)]
    Analytics --- DB
    AI --- DB
```

---

## ✨ Key Capabilities

🚀 **Autonomous Workforce:** Multi-agent collaboration (Detective, Forecaster, Advisor) with native budget caps and heartbeat monitoring.  
📉 **Shadow CFO Trust Engine:** Automatic confidence penalties for sparse or volatile data to ensure AI reliability.  
📎 **Paperclip Governance:** Enterprise-grade orchestration using the v0.3.1 Plugin architecture for task checkouts and audit trails.  
📊 **Deterministic Analytics:** High-performance risk calculation engines for VaR, Sharpe Ratio, and portfolio scoring.  
🐳 **Fully Containerized:** One-click deployment with Docker and PowerShell bootstrapping.

---

## 🛠️ Technology Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Control Plane** | Paperclip v0.3.1 | Agent orchestration & budget governance |
| **Frontend** | React 19, Next.js 16 | Highly responsive, enterprise-grade UI |
| **API Gateway** | Python, FastAPI | High-concurrency routing & state management |
| **AI Orchestrator** | Google Gemini API | Advanced reasoning & NLP extraction |
| **Analytics Engine**| Python, Pandas | Heavy parallel computation of risk metrics |
| **Message Broker**| RabbitMQ | Asynchronous task decoupling |
| **Database** | PostgreSQL 13 | Durable, acid-compliant data persistence |

---

## 🚀 Getting Started

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop) installed.
- Google Gemini API Key.

### Quick Setup (One-Click Autonomous Mode)

1. **Configure Environment**
   Set your keys and Paperclip IDs in `.env`:
   ```env
   GEMINI_API_KEY=your_key
   PAPERCLIP_COMPANY_ID=your_id
   ```

2. **Boot the System**
   Run the unified bootstrap script from PowerShell:
   ```powershell
   .\scripts\bootstrap_system.ps1
   ```

3. **Access**
   - **Frontend UI:** [http://localhost:3000](http://localhost:3000)
   - **Paperclip Control Plane:** [http://localhost:3100](http://localhost:3100)
   - **API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 📈 System Monitoring

To ensure robust observability in a production-like environment, critical services emit structured logs. 
Monitor real-time task ingestion rates and AI token latency directly through the **RabbitMQ Management Portal** and Docker standard outputs.

## 📄 License

This project is licensed under the MIT License.
