import pytest
from unittest.mock import Mock, patch, AsyncMock
from app.services.ml.inference_service import InferenceService, RecommendationResult
import numpy as np
import torch

@pytest.fixture
def inference_service():
    service = InferenceService()
    return service

class TestInferenceService:
    
    @pytest.mark.asyncio
    async def test_initialization(self, inference_service):
        """Test service initialization"""
        with patch.object(inference_service, '_load_models'):
            await inference_service.initialize()
            
            assert inference_service.initialized is True
            assert inference_service.models is not None
    
    @pytest.mark.asyncio
    async def test_get_user_embedding_success(self, inference_service):
        """Test successful user embedding retrieval"""
        mock_result = [Mock()]
        mock_result[0].vector = list(np.random.randn(512))
        
        with patch.object(inference_service.qdrant_client, 'get', return_value=mock_result):
            embedding = await inference_service._get_user_embedding(user_id=123)
            
            assert isinstance(embedding, np.ndarray)
            assert len(embedding) == 512
    
    @pytest.mark.asyncio
    async def test_get_user_embedding_failure(self, inference_service):
        """Test fallback when embedding retrieval fails"""
        with patch.object(inference_service.qdrant_client, 'get', side_effect=Exception("Failed")):
            embedding = await inference_service._get_user_embedding(user_id=999)
            
            assert isinstance(embedding, np.ndarray)
    
    @pytest.mark.asyncio
    async def test_generate_candidates_success(self, inference_service):
        """Test candidate generation via vector search"""
        mock_hits = [Mock(id=f"item_{i}") for i in range(5)]
        
        with patch.object(inference_service.qdrant_client, 'search', return_value=mock_hits):
            candidates = await inference_service._generate_candidates(
                user_embedding=np.random.randn(512),
                k=5
            )
            
            assert len(candidates) == 5
            assert all(isinstance(item, str) for item in candidates)
    
    @pytest.mark.asyncio
    async def test_rank_candidates(self, inference_service):
        """Test candidate ranking"""
        candidates = ["item_1", "item_2", "item_3"]
        
        results = await inference_service._rank_candidates(
            user_id=123,
            candidates=candidates,
            context=None
        )
        
        assert len(results) == 3
        assert all(isinstance(r, RecommendationResult) for r in results)
        assert all(0.0 <= r.score <= 1.0 for r in results)
    
    @pytest.mark.asyncio
    async def test_fallback_recommendations(self, inference_service):
        """Test fallback recommendation generation"""
        results = inference_service._get_fallback_recommendations(num_results=5)
        
        assert len(results) == 5
        assert all(r.item_id.startswith("fallback_") for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
