from sqlalchemy import Column, Integer, String, DateTime, JSON, Text, Boolean
from sqlalchemy.sql import func
from datetime import datetime

from app.core.database import Base

class User(Base):
    __tablename__ = 'users'
    
    user_id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=True)
    preferences = Column(JSON, default={})
    demographic_info = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)


class Item(Base):
    __tablename__ = 'items'
    
    item_id = Column(String, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text, nullable=True)
    metadata = Column(JSON, default={})
    category = Column(String, index=True)
    tags = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Interaction(Base):
    __tablename__ = 'interactions'
    
    interaction_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer)
    item_id = Column(String)
    event_type = Column(String)
    event_time = Column(DateTime(timezone=True))
    session_id = Column(String)
    duration_seconds = Column(Integer, default=0)
    position = Column(Integer, nullable=True)
    
    __table_args__ = (
        Index('idx_user_event_time', 'user_id', 'event_time'),
        Index('idx_item_event_time', 'item_id', 'event_time')
    )


class Recommendation(Base):
    __tablename__ = 'recommendations'
    
    recommendation_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer)
    item_id = Column(String)
    model_version = Column(String)
    score = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_recommendations_user_created', 'user_id', 'created_at')
    )
