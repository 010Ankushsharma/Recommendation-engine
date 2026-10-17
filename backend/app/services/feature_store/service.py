import json
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime, timedelta
import redis
import yaml

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FeatureStoreService:
    """Feast-style feature store implementation"""
    
    def __init__(self):
        self.redis_url = "redis://localhost:6379"
        self.online_store = None
        self.offline_store = None
        self._initialize()
    
    def _initialize(self):
        """Initialize feature store connections"""
        try:
            # Initialize Redis for online store
            self.online_store = redis.Redis.from_url(
                self.redis_url,
                decode_responses=True
            )
            
            # Test connection
            self.online_store.ping()
            logger.info("Feature Store initialized successfully")
        except Exception as e:
            logger.warning(f"Could not initialize feature store: {e}")
            self.online_store = None
    
    async def get_online_features(
        self, 
        entity_type: str, 
        entity_ids: List[str], 
        feature_names: List[str]
    ) -> Dict[str, Dict[str, float]]:
        """Get real-time features from online store"""
        
        if not self.online_store:
            return {entity_id: {} for entity_id in entity_ids}
        
        results = {}
        
        for entity_id in entity_ids:
            key = f"{entity_type}:{entity_id}:features"
            cached_features = self.online_store.get(key)
            
            if cached_features:
                features = json.loads(cached_features)
                filtered = {k: v for k, v in features.items() if k in feature_names}
                results[entity_id] = filtered
            else:
                results[entity_id] = {}
        
        return results
    
    async def update_online_features(
        self, 
        entity_type: str, 
        entity_id: str, 
        features: Dict[str, Any],
        ttl: int = 300
    ):
        """Update features in online store with TTL"""
        
        if not self.online_store:
            return
        
        try:
            key = f"{entity_type}:{entity_id}:features"
            
            # Get existing features
            existing_key = self.online_store.get(key)
            if existing_key:
                existing_features = json.loads(existing_key)
                existing_features.update(features)
                features = existing_features
            
            # Store with TTL
            self.online_store.setex(
                key, 
                ttl, 
                json.dumps(features)
            )
            
            logger.debug(f"Updated features for {entity_type}:{entity_id}")
        except Exception as e:
            logger.error(f"Error updating features: {e}")
    
    async def get_batch_features(
        self, 
        entity_type: str, 
        entity_ids: List[str], 
        feature_view_name: str
    ) -> List[Dict[str, Any]]:
        """Get batch features from offline store (simulated)"""
        
        # In production, this would read from Parquet files in S3
        # Here we simulate feature generation
        
        results = []
        
        for entity_id in entity_ids:
            features = {
                "entity_id": entity_id,
                "timestamp": datetime.now().isoformat()
            }
            
            # Simulate feature values based on entity_id hash
            hash_val = hash(entity_id) % 1000
            
            if entity_type == "user":
                features.update({
                    "watch_count": hash_val % 100,
                    "avg_session_time": 15.5 + (hash_val % 100),
                    "favorite_genre": ["Action", "Sci-Fi"][hash_val % 2],
                    "engagement_score": round(0.5 + (hash_val / 1000), 3),
                    "last_active_hours_ago": 1 + (hash_val % 24)
                })
            elif entity_type == "item":
                features.update({
                    "popularity_rank": hash_val % 1000,
                    "total_views": hash_val * 1000,
                    "avg_rating": 3.5 + (hash_val % 50) / 50,
                    "recency_score": round(0.8 - (hash_val % 100) / 200, 3),
                    "category_votes": hash_val % 10
                })
            
            results.append(features)
        
        return results
    
    async def calculate_feature_stats(
        self, 
        entity_type: str, 
        feature_name: str,
        window_days: int = 7
    ) -> Dict[str, float]:
        """Calculate feature statistics over time window"""
        
        # Simulated statistics
        import random
        random.seed(hash(entity_type + feature_name))
        
        return {
            "mean": round(random.uniform(10, 100), 2),
            "std": round(random.uniform(5, 20), 2),
            "min": round(random.uniform(1, 10), 2),
            "max": round(random.uniform(100, 500), 2),
            "null_count": random.randint(0, 10)
        }
    
    def invalidate_entity_cache(self, entity_type: str, entity_id: str):
        """Invalidate cached features for an entity"""
        
        if not self.online_store:
            return
        
        key = f"{entity_type}:{entity_id}:features"
        self.online_store.delete(key)
        logger.debug(f"Invalidated cache for {entity_type}:{entity_id}")


# Singleton instance
_feature_store = None

def get_feature_store():
    global _feature_store
    if _feature_store is None:
        _feature_store = FeatureStoreService()
    return _feature_store
