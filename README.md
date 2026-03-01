# ReAlign AI - Backend API

**Bridging Design Assumptions with Site Reality**

FastAPI-powered backend for an AI-driven generative design and autonomous construction site execution system. Designed for the CreateTech 2026 Hackathon - Problem Statement 3.

---

## 📋 Problem Statement

**Challenge:** Construction projects experience significant gaps between design assumptions and actual site conditions, causing:
- Rework and delays
- Cost overruns
- Resource inefficiencies
- Disconnected tool ecosystems

**Solution:** A dynamic engineering system that continuously recalibrates designs based on real-time sensor data and predictive simulations.

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────┐
│            REALIGN AI - BACKEND SERVICES                │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────────────────────────────────────┐      │
│  │         FastAPI REST API Gateway              │      │
│  │   (Authentication, Authorization, CORS)       │      │
│  └──────────────────────────────────────────────┘      │
│              ↓        ↓        ↓        ↓               │
│         ┌────────┬────────┬──────────┬──────┐           │
│         │  Auth  │Designer│   Site   │Models│           │
│         │ Router │ Router │ Router   │      │           │
│         └────────┴────────┴──────────┴──────┘           │
│              ↓        ↓        ↓        ↓               │
│  ┌────────────────────────────────────────────────┐     │
│  │         Business Logic & AI Modules             │     │
│  │ • Layout Retrieval    • Optimization Engine     │     │
│  │ • Cost Prediction     • Sensor Integration      │     │
│  │ • Generative Design   • Real-time Recalibration│     │
│  └────────────────────────────────────────────────┘     │
│              ↓                                           │
│  ┌────────────────────────────────────────────────┐     │
│  │      PostgreSQL Database Layer                  │     │
│  │  • Users & Authentication  • Projects          │     │
│  │  • Layouts & Designs       • Issues & Feedback │     │
│  └────────────────────────────────────────────────┘     │
│              ↓                                           │
│  ┌────────────────────────────────────────────────┐     │
│  │     AI/ML Models & Data Processing              │     │
│  │  • ResNet18 embeddings  • VAE generative model │     │
│  │  • SLSQP Optimization   • Constraint solver    │     │
│  └────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────┘
```

---

## 🎯 Key Features

### ✅ Multi-Role Access Control
- **Design Engineers:** Create projects, propose designs, optimize layouts
- **Site Engineers:** Monitor real-time site conditions, report issues, execute changes
- **Admin:** System management and oversight
- **JWT-based authentication** with refresh tokens

### ✅ Intelligent Design Optimization
- **Multi-constraint solver:** Balances cost, timeline, area, and safety
- **Layout Retrieval:** Query similar layouts from 571+ layout database using:
  - Area-based similarity
  - Embedding-based similarity (ResNet18 features)
- **Generative Design:** VAE-based model generates novel layout variations

### ✅ Real-Time Monitoring & Adaptation
- **Sensor Integration:** Environmental, structural, and resource sensors
- **Anomaly Detection:** Automatic triggering of design recalibration
- **Continuous Feedback Loop:** Sensors → Optimization → Layout → Execution

### ✅ Cost & Timeline Prediction
- Predicts construction costs based on area and constraints
- Estimates project timeline realistically
- Tracks actual vs. predicted metrics

### ✅ Project & Issue Management
- Create and manage construction projects
- Track design issues and resolutions
- Monitor project status in real-time
- Approve/reject layout designs

---

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- PostgreSQL 12+
- pip

### Installation

```bash
# 1. Create virtual environment
python -m venv venv

# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up environment variables
cp .env.example .env
# Edit .env with your database credentials and JWT secret
```

### Environment Variables (.env)
```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/realign_ai

# JWT
SECRET_KEY=your-super-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS
ALLOWED_ORIGINS=http://localhost:3000,https://yourdomain.com

# Environment
DEBUG=False
```

### Running the Server

```bash
# Development server (with auto-reload)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Production server
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

The API will be available at:
- **API Base:** `http://localhost:8000`
- **Interactive Docs:** `http://localhost:8000/docs` (Swagger UI)
- **Alternative Docs:** `http://localhost:8000/redoc` (ReDoc)

---


## 🔧 AI/ML Modules (in root directory)

These core modules handle the intelligent aspects:

### `extract_embeddings.py`
- Extracts visual features from 571 layout images using ResNet18
- Generates `layout_embeddings.npy` and `layout_areas.npy`
- Run once after adding new layout images

### `layout_retrieval.py`
- Queries similar layouts from the database
- Uses both embedding-based and area-based similarity
- Returns top matches with confidence scores

### `adaptive.py`
- **Multi-constraint optimization engine**
- Balances: Cost, Timeline, Area, Safety, Risk
- Uses SLSQP and Differential Evolution algorithms
- Automatically adapts designs to site constraints

### `predictor.py`
- Predicts construction costs based on area
- Estimates project timeline
- Upgradeable to advanced ML models

### `generative_design.py`
- Variational Autoencoder (VAE) for layout generation
- Generates novel designs, variations, and interpolations
- Constraint-guided generation

### `sensor_simulator.py` & `realtime_recalibration.py`
- Simulates IoT sensor networks on construction sites
- Monitors 4 categories: Environmental, Structural, Resources, Workforce
- Automatically triggers design recalibration on anomalies

---

## 🔐 Security Features

- **JWT Authentication** with access and refresh tokens
- **Role-Based Access Control (RBAC):** Design Engineer, Site Engineer, Admin
- **Password Hashing:** Using bcrypt (via passlib)
- **CORS Configuration:** Restricted to allowed origins
- **Rate Limiting Middleware:** Prevents abuse
- **Security Headers:** XSS, CSRF, and clickjacking protection

---

## 💾 Database Schema

### Key Tables
- **users:** User accounts with roles and credentials
- **projects:** Construction projects with metadata
- **layouts:** Layout designs with embeddings and metadata
- **issues:** Site-reported issues and resolutions
- **approvals:** Design approval/rejection history

---


## 📈 System Capabilities

| Feature | Status | Notes |
|---------|--------|-------|
| User Authentication | ✅ Complete | JWT-based with roles |
| Project Management | ✅ Complete | CRUD operations |
| Layout Retrieval | ✅ Complete | 571+ layouts, embedding-based |
| Cost Prediction | ✅ Complete | Area-based, upgradeable |
| Multi-Constraint Optimization | ✅ Complete | SLSQP + Diff Evolution |
| Generative Design (VAE) | ✅ Complete | Novel design generation |
| Real-time Recalibration | ✅ Complete | Sensor-triggered adaptation |
| REST API | ✅ Complete | Full Swagger documentation |

---

## 🤝 Contributing

To contribute to the backend:

1. Create a feature branch
2. Add tests for new features
3. Ensure all endpoints are documented
4. Follow PEP 8 style guide
5. Update this README if adding new modules

---

## 📝 License

CreateTech 2026 Hackathon Project


**Made with ❤️ for CreateTech 2026 Hackathon - Problem Statement 3: AI-Driven Generative Design & Autonomous Construction Site Execution**
