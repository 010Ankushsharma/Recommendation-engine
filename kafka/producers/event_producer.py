from kafka import KafkaProducer
from kafka.errors import KafkaTimeoutError
from typing import Dict, Any
import json
import logging
import time
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EventProducer:
    """Kafka event producer for user interactions"""
    
    def __init__(self):
        bootstrap_servers = os.getenv(
            "KAFKA_BOOTSTRAP_SERVERS", 
            "localhost:9092"
        )
        
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,
            retries=3,
            acks='all',
            compression_type='gzip'
        )
        
        self.topics = {
            "click": "rec_events.clicks",
            "watch": "rec_events.watches",
            "impression": "rec_events.impressions",
            "feedback": "rec_events.feedback"
        }
        
        logger.info("Event Producer initialized")
    
    async def send_event(self, event_type: str, event_data: Dict[str, Any]):
        """Send event to appropriate topic"""
        
        try:
            topic = self.topics.get(event_type, "rec_events.generic")
            
            future = self.producer.send(
                topic=topic,
                key=event_data.get("user_id", "").encode('utf-8'),
                value=event_data
            )
            
            # Get result with timeout
            record_metadata = future.get(timeout=10)
            
            logger.debug(
                f"Event sent - Topic: {record_metadata.topic}, "
                f"Partition: {record_metadata.partition}, "
                f"Offset: {record_metadata.offset}"
            )
            
        except KafkaTimeoutError as e:
            logger.error(f"Kafka timeout error: {e}")
        except Exception as e:
            logger.error(f"Failed to send event: {e}")
    
    async def send_batch_events(self, events: list):
        """Send multiple events efficiently"""
        
        futures = []
        
        for event in events:
            event_type = event.get("type", "generic")
            topic = self.topics.get(event_type, "rec_events.generic")
            
            future = self.producer.send(
                topic=topic,
                key=str(event.get("user_id", "")).encode('utf-8'),
                value=event
            )
            futures.append(future)
        
        # Wait for all to complete
        results = []
        for future in futures:
            try:
                record_metadata = future.get(timeout=10)
                results.append(record_metadata)
            except Exception as e:
                logger.error(f"Failed to send batch event: {e}")
                results.append(None)
        
        return results
    
    def close(self):
        """Close producer connection"""
        self.producer.flush()
        self.producer.close()


# Singleton instance
_producer = None

def get_event_producer():
    global _producer
    if _producer is None:
        _producer = EventProducer()
    return _producer
