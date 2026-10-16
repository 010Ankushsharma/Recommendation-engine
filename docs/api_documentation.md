# API Documentation

## Base URL
```
Production: https://api.recommendation-engine.com/v1
Development: http://localhost:8000/v1
```

## Authentication
All API requests require a JWT token in the Authorization header:
```
Authorization: Bearer <your_jwt_token>
```

## Endpoints

### 1. Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-15T10:30:00Z",
  "services": {
    "database": "connected",
    "redis": "connected",
    "kafka": "connected",
    "qdrant": "connected",
    "mlflow": "connected"
  }
}
```

### 2. Get Recommendations
```http
POST /recommend
```

**Request Body:**
```json
{
  "user_id": 12345,
  "context": {
    "device_type": "mobile",
    "location": {"country": "US", "city": "San Francisco"},
    "time_of_day": "evening",
    "session_id": "session_abc123"
  },
  "num_results": 20,
  "filters": {
    "exclude_categories": ["adult"],
    "min_rating": 4.0
  },
  "strategy": "personalized"
}
```

**Response:**
```json
{
  "recommendations": [
    {
      "item_id": "movie_001",
      "title": "Inception",
      "score": 0.95,
      "reasons": ["Similar to your recent watches", "Highly rated in your region"],
      "metadata": {
        "genre": ["Sci-Fi", "Action"],
        "year": 2010,
        "duration": 148
      },
      "embeddings_available": true
    }
  ],
  "explanation": {
    "top_factors": [
      {"factor": "watch_history", "weight": 0.6},
      {"factor": "collaborative_filtering", "weight": 0.3}
    ],
    "model_version": "v2.3.1",
    "latency_ms": 45
  },
  "request_id": "req_abc123xyz"
}
```

### 3. Rank Candidates
```http
POST /rank
```

**Request Body:**
```json
{
  "user_id": 12345,
  "candidate_items": [
    {"item_id": "movie_001", "preliminary_score": 0.9},
    {"item_id": "movie_002", "preliminary_score": 0.85}
  ],
  "context": {
    "device_type": "desktop",
    "current_page": "home"
  }
}
```

### 4. Candidate Generation
```http
POST /candidate-generation
```

### 5. User & Item APIs
```http
GET /users/{user_id}
GET /items/{item_id}
```

### 6. Feedback & Events
```http
POST /feedback
POST /events
```

### 7. A/B Testing
```http
POST /ab-test/assign
```

## Error Responses
```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "User ID is required",
    "details": {"field": "user_id", "issue": "missing_required_field"},
    "request_id": "req_error123"
  }
}
```

## Rate Limiting
- Standard: 1000 requests/minute per user
- Response headers: X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset
