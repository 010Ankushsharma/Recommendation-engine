# System Design Document

## High-Level Design Principles

### 1. Microservices Architecture
Each component is independently deployable and scalable:
- Candidate Generation Service
- Ranking Service
- Feature Store Service
- Embedding Service
- Event Processing Service

### 2. Event-Driven Architecture
Asynchronous processing using Apache Kafka:
- Decouples components
- Enables real-time processing
- Provides audit trail
- Supports replay capability

### 3. Multi-Layer Caching Strategy
- L1: In-memory cache (local to service)
- L2: Distributed cache (Redis cluster)
- L3: CDN for static assets

## Detailed Component Design

### 2.1 API Gateway
**Responsibilities:**
- Route requests to appropriate services
- Authentication and authorization
- Rate limiting and throttling
- Request/response transformation
- Load balancing

**Implementation:**
```python
class APIGateway:
    def __init__(self):
        self.rate_limiter = TokenBucketRateLimiter(max_requests=1000)
        self.auth_provider = JWTAuthProvider()
        self.load_balancer = RoundRobinLB()
    
    async def handle_request(self, request):
        if not self.rate_limiter.allow(request.client_ip):
            return Response(status=429)
        
        if not await self.auth_provider.validate(request.token):
            return Response(status=401)
        
        route = self._route_request(request.path)
        return await self.load_balancer.route(route, request)
```

### 2.2 Candidate Generation Service
**Design Patterns:**
- Factory pattern for different algorithms
- Strategy pattern for algorithm switching
- Async processing for scalability

**Algorithms:**
1. **Collaborative Filtering (ALS)**
   ```python
   class ALSRecommender:
       def __init__(self, rank=50, iterations=20):
           self.model = AlternatingLeastSquares(
               factors=rank,
               regularization=0.01,
               iterations=iterations
           )
       
       def fit(self, interactions_df):
           # Convert to sparse matrix
           self.model.fit(interactions_df.tocsr())
       
       def recommend(self, user_id, num_items=50):
           ratings = self.model.recommend(
               user_id,
               self.item_items,
               N=num_items,
               filter_already_liked=True
           )
           return ratings
   ```

2. **Content-Based Filtering**
   ```python
   class ContentBasedRecommender:
       def __init__(self, vector_store):
           self.vector_store = vector_store
       
       def recommend(self, user_embedding, exclude_ids=None):
           query = self.vector_store.build_query(user_embedding)
           return self.vector_store.search(query, top_k=50)
   ```

3. **Two-Tower Retrieval**
   ```python
   class TwoTowerRetrieval:
       def __init__(self):
           self.user_tower = nn.Sequential(
               nn.Linear(feature_dim, 256),
               nn.ReLU(),
               nn.Linear(256, 128)
           )
           self.item_tower = nn.Sequential(
               nn.Linear(feature_dim, 256),
               nn.ReLU(),
               nn.Linear(256, 128)
           )
       
       def forward(self, user_features, item_features):
           user_emb = self.user_tower(user_features)
           item_emb = self.item_tower(item_features)
           return user_emb, item_emb
   ```

### 2.3 Ranking Service
**Deep Learning Models:**

**DeepFM Model:**
```python
class DeepFM(nn.Module):
    def __init__(self, fm_feature_dim, dnn_feature_dim, embed_dim):
        super().__init__()
        
        # FM component for 2nd-order feature interaction
        self.fm_layer = FMLayer(num_fields=fm_feature_dim)
        
        # DNN component for higher-order interactions
        self.dnn = nn.Sequential(
            nn.Embedding(dnn_feature_dim, embed_dim),
            nn.Flatten(),
            nn.Linear(embed_dim * num_categories, 512),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, 1)
        )
    
    def forward(self, input_data):
        fm_output = self.fm_layer(input_data['fm_features'])
        dnn_output = self.dnn(input_data['dnn_features'])
        return torch.sigmoid(fm_output + dnn_output).squeeze()
```

**Training Strategy:**
- Loss function: BCELoss with label smoothing
- Optimizer: AdamW with learning rate scheduling
- Regularization: Dropout, L2 regularization
- Early stopping based on validation AUC

### 2.4 Feature Store (Feast Integration)
**Feature Definition:**
```python
from feast import FeatureRepo, FeatureView, Entity, Feature, ValueType

# Define entities
user_entity = Entity(
    name="user_id",
    value_type=ValueType.INT64,
    description="User unique identifier"
)

item_entity = Entity(
    name="item_id",
    value_type=ValueType.STRING,
    description="Item unique identifier"
)

# Define feature views
user_feature_view = FeatureView(
    name="user_features",
    entities=["user_id"],
    features=[
        Feature(name="watch_count", dtype=ValueType.INT64),
        Feature(name="avg_session_time", dtype=ValueType.FLOAT),
        Feature(name="favorite_genre", dtype=ValueType.STRING),
        Feature(name="engagement_score", dtype=ValueType.FLOAT),
    ],
    stream=StreamSource(topic="user_events"),
    ttl=timedelta(hours=1),
    offline_store=parquet_store,
    online_store=redis_store
)
```

### 2.5 Embedding Service (Qdrant)
**Embedding Storage:**
```python
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Distance, VectorParams

class EmbeddingService:
    def __init__(self, url, collection_name):
        self.client = QdrantClient(url=url)
        self.collection = collection_name
        
        # Create collection
        vector_size = 512
        distance = Distance.COSINE
        
        self.client.create_collection(
            collection_name=self.collection,
            vectors_config=VectorParams(size=vector_size, distance=distance),
            hnsw_config=HnswConfigDiff(m=64, ef_construct=100)
        )
    
    def upsert_user_embedding(self, user_id, embedding):
        point = PointStruct(
            id=user_id,
            vector=embedding.tolist(),
            payload={"user_id": str(user_id)}
        )
        self.client.upsert(collection_name=self.collection, points=[point])
    
    def find_similar_users(self, query_embedding, limit=10):
        results = self.client.search(
            collection_name=self.collection,
            query_vector=query_embedding,
            limit=limit
        )
        return results
```

### 2.6 Real-Time Event Processing
**Kafka Consumer Implementation:**
```python
from kafka import KafkaConsumer
from json import loads

class EventConsumer:
    def __init__(self, bootstrap_servers, topic, group_id):
        self.consumer = KafkaConsumer(
            bootstrap_servers=bootstrap_servers,
            auto_offset_reset='earliest',
            enable_auto_commit=False,
            consumer_group_id=group_id,
            value_deserializer=lambda x: loads(x.decode('utf-8'))
        )
        self.topic = topic
    
    def consume_events(self):
        for message in self.consumer:
            event = message.value
            
            # Process event
            if event['type'] == 'click':
                await self.handle_click(event)
            elif event['type'] == 'watch':
                await self.handle_watch(event)
            
            # Commit offset
            self.consumer.commit(message)
    
    async def handle_click(self, event):
        # Update user profile
        # Trigger candidate refresh
        # Update session state
        pass
```

## Database Schema Design

### PostgreSQL Tables
```sql
-- Users table
CREATE TABLE users (
    user_id BIGINT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    preferences JSONB,
    demographic_info JSONB
);

-- Items table
CREATE TABLE items (
    item_id VARCHAR(255) PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB,
    category VARCHAR(100),
    tags TEXT[]
);

-- Interactions table
CREATE TABLE interactions (
    interaction_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id),
    item_id VARCHAR(255) REFERENCES items(item_id),
    event_type VARCHAR(50) NOT NULL, -- click, watch, like, skip
    event_time TIMESTAMP NOT NULL,
    session_id VARCHAR(255),
    duration_seconds INTEGER,
    position INTEGER
);

-- Recommendations table
CREATE TABLE recommendations (
    recommendation_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id),
    item_id VARCHAR(255) REFERENCES items(item_id),
    model_version VARCHAR(100),
    score FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Feature store snapshots
CREATE TABLE feature_snapshots (
    snapshot_id BIGSERIAL PRIMARY KEY,
    entity_type VARCHAR(50),
    entity_id VARCHAR(255),
    features JSONB,
    timestamp TIMESTAMP,
    version INTEGER
);
```

## Performance Optimization Strategies

### 1. Query Optimization
- Indexes on frequently queried columns
- Materialized views for complex aggregations
- Connection pooling

### 2. Caching Strategies
```python
class CachedFeatureStore:
    def __init__(self, redis_client, ttl=300):
        self.redis = redis_client
        self.ttl = ttl
    
    def get_feature(self, key):
        cached = self.redis.get(key)
        if cached:
            return json.loads(cached)
        
        feature = self._fetch_from_source(key)
        self.redis.setex(key, self.ttl, json.dumps(feature))
        return feature
```

### 3. Asynchronous Processing
- Use async/await for I/O operations
- Background tasks for non-critical updates
- Message queues for decoupling

## Fault Tolerance

### Circuit Breaker Pattern
```python
from tenacity import retry, stop_after_attempt, wait_fixed

class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_time=300):
        self.failures = 0
        self.failure_threshold = failure_threshold
        self.recovery_time = recovery_time
        self.last_failure_time = None
        self.state = "CLOSED"
    
    def call(self, func, *args, **kwargs):
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_time:
                self.state = "HALF_OPEN"
            else:
                raise Exception("Circuit breaker is open")
        
        try:
            result = func(*args, **kwargs)
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise e
    
    def on_success(self):
        self.failures = 0
        self.state = "CLOSED"
    
    def on_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        
        if self.failures >= self.failure_threshold:
            self.state = "OPEN"
```
