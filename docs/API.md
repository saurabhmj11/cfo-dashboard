# API Documentation

## Base URL
```
http://localhost:8000
```

## Authentication

### Login
```http
POST /auth/token
Content-Type: application/x-www-form-urlencoded

username=demo&password=demo123
```

**Response:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 900
}
```

### Refresh Token
```http
POST /auth/refresh
Content-Type: application/json

{"refresh_token": "eyJ..."}
```

---

## Analysis

### Run Financial Analysis
```http
POST /api/v1/analysis/run
Authorization: Bearer {token}
Content-Type: application/json

{
  "dataset_id": 1,
  "context": "Analyze Q4 performance"
}
```

---

## Market Data

### Get Quote
```http
GET /api/v1/market/quote/AAPL
```

### Get Historical Data
```http
GET /api/v1/market/history/AAPL?period=1mo&interval=1d
```

---

## Search (RAG)

### Semantic Search
```http
POST /api/v1/search
Authorization: Bearer {token}

{"query": "What are total expenses?", "top_k": 5}
```

### Ask Question
```http
POST /api/v1/search/ask
Authorization: Bearer {token}

{"question": "What is the profit margin?"}
```

---

## Reports

### Export PDF/Excel
```http
POST /api/v1/reports/generate
Authorization: Bearer {token}

{
  "title": "Q4 Report",
  "format": "pdf",
  "analysis_data": {...}
}
```

---

## Rate Limits
- Standard: 60 req/min
- Strict (auth): 10 req/min
- Export: 5 req/min
