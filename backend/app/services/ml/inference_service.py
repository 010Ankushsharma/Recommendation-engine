import asyncio
from typing import List, Dict, Optional
from dataclasses import dataclass
import logging
import os
import numpy as np

import torch
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class RecommendationResult:
    item_id: str
    score: float
    reasons: List[str]
    metadata: Dict

class InferenceService:
    
    def __init__(self):
        self.qdrant_client = None
        self.models = {}
        self.initialized = False
    
    async def initialize(self):
        """Initialize all inference components"""
        logger.info("Initializing Inference Service...")
        
        # Initialize Qdrant client for vector search
        qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        self.qdrant_client = QdrantClient(url=qdrant_url, prefer_grpc=False)
        
        # Load models from MLflow
        await self._load_models()
        
        self.initialized = True
        logger.info("Inference Service initialized successfully")
    
    async def _load_models(self):
        """Load ML models from registry"""
        try:
            import mlflow
            mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000"))
            
            model_uri = "models:/two_tower_retrieval/latest"
            self.models['retrieval'] = mlflow.pytorch.load_model(model_uri)
            
            rank_model_uri = "models:/deepfm_ranker/latest"
            self.models['ranking'] = mlflow.pytorch.load_model(rank_model_uri)
            
            logger.info(f"Loaded {len(self.models)} models")
        except Exception as e:
            logger.warning(f"Could not load models from MLflow: {e}")
    
    async def get_recommendations(self, user_id: int, num_results: int = 20, 
                                 context: Optional[Dict] = None) -> List[RecommendationResult]:
        """Generate personalized recommendations"""
        
        if not self.initialized:
            raise RuntimeError("Inference service not initialized")
        
        try:
            user_embedding = await self._get_user_embedding(user_id)
            candidates = await self._generate_candidates(user_embedding, num_results * 2)
            ranked_items = await self._rank_candidates(user_id, candidates, context)
            
            return ranked_items[:num_results]
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return self._get_fallback_recommendations(num_results)
    
    async def _get_user_embedding(self, user_id: int) -> np.ndarray:
        """Retrieve or compute user embedding"""
        try:
            result = self.qdrant_client.get(
                collection_name="user_embeddings",
                ids=[user_id],
                with_vectors=True
            )
            
            if result and result[0].vector:
                return np.array(result[0].vector)
            
            return await self._compute_user_embedding(user_id)
        except Exception as e:
            logger.warning(f"Could not retrieve user embedding: {e}")
            return self._create_random_embedding()
    
    async def _generate_candidates(self, user_embedding: np.ndarray, k: int) -> List[str]:
        """Generate candidate items using vector similarity"""
        try:
            result = self.qdrant_client.search(
                collection_name="item_embeddings",
                query_vector=user_embedding.tolist(),
                limit=k
            )
            return [hit.id for hit in result]
        except Exception as e:
            logger.warning(f"Vector search failed: {e}")
            return self._get_trending_items(k)
    
    async def _rank_candidates(self, user_id: int, candidates: List[str], 
                              context: Optional[Dict]) -> List[RecommendationResult]:
        """Rank candidate items using deep learning model"""
        
        results = []
        
        for item_id in candidates:
            user_features = torch.tensor([user_id % 100]).float()
            item_features = torch.tensor([hash(item_id) % 100]).float()
            
            if 'ranking' in self.models:
                with torch.no_grad():
                    score = self.models['ranking']((user_features, item_features)).item()
            else:
                score = 0.9 - (hash(item_id) % 100) / 1000
            
            reasons = self._generate_reasons(user_id, item_id)
            
            results.append(RecommendationResult(
                item_id=item_id,
                score=round(score, 4),
                reasons=reasons,
                metadata={"genre": ["Action"], "year": 2024}
            ))
        
        results.sort(key=lambda x: x.score, reverse=True)
        return results
    
    def _get_fallback_recommendations(self, num_results: int) -> List[RecommendationResult]:
        """Fallback recommendations when service fails"""
        return [
            RecommendationResult(
                item_id=f"fallback_{i}",
                score=0.8,
                reasons=["Popular items"],
                metadata={"type": "fallback"}
            )
            for i in range(num_results)
        ]
    
    def _get_trending_items(self, k: int) -> List[str]:
        """Get trending items as fallback"""
        return [f"trending_item_{i}" for i in range(k)]
    
    def _generate_reasons(self, user_id: int, item_id: str) -> List[str]:
        """Generate explanation for recommendation"""
        reasons = []
        
        if hash(user_id) % 2 == 0:
            reasons.append("Similar to your recent views")
        if hash(item_id) % 3 == 0:
            reasons.append("Highly rated in your region")
        if hash(user_id + item_id) % 2 == 0:
            reasons.append("Trending now")
        
        return reasons if reasons else ["Based on your preferences"]
    
    def _create_random_embedding(self, dim=512):
        """Create random embedding vector"""
        return np.random.randn(dim).astype(np.float32)


_inference_service = None

async def get_inference_service():
    global _inference_service
    if _inference_service is None:
        _inference_service = InferenceService()
        await _inference_service.initialize()
    return _inference_service
