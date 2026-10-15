from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, avg, max as spark_max, current_timestamp, unix_timestamp
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_user_features(spark, interactions_df, users_df):
    """Create user-level aggregated features"""
    
    logger.info("Creating user features...")
    
    # Basic aggregations
    user_stats = interactions_df.groupBy("user_id").agg(
        count("*").alias("total_interactions"),
        avg("duration_seconds").alias("avg_session_duration"),
        spark_max("duration_seconds").alias("max_session_duration"),
        count(distinct="item_id").alias("unique_items_interacted")
    )
    
    # Temporal features
    user_stats = user_stats.withColumn(
        "last_interaction_timestamp",
        spark_max(col("event_time"))
    )
    
    # Genre preferences
    genre_prefs = interactions_df.join(
        users_df.select("user_id", "favorite_genre"),
        "user_id"
    ).groupBy("user_id").pivot("favorite_genre").count()
    
    # Combine all features
    user_features = user_stats.join(genre_prefs, "user_id", "left")
    user_features = user_features.fillna({
        "total_interactions": 0,
        "avg_session_duration": 0,
        "unique_items_interacted": 0
    })
    
    logger.info(f"Created features for {user_features.count()} users")
    return user_features


def create_item_features(spark, interactions_df, items_df):
    """Create item-level features"""
    
    logger.info("Creating item features...")
    
    # Popularity features
    item_stats = interactions_df.groupBy("item_id").agg(
        count("*").alias("total_views"),
        avg("rating").alias("avg_rating"),
        spark_max("event_time").alias("last_viewed"),
        count(distinct="user_id").alias("unique_viewers")
    )
    
    # Recent activity (last 7 days)
    cutoff_date = datetime.now() - timedelta(days=7)
    recent_activity = interactions_df.filter(
        interactions_df.event_time >= cutoff_date
    ).groupBy("item_id").count().withColumnRenamed("count", "recent_views_7d")
    
    # Join and fill missing values
    item_features = item_stats.join(recent_activity, "item_id", "outer")
    item_features = item_features.fillna(0)
    
    logger.info(f"Created features for {item_features.count()} items")
    return item_features


def main():
    """Main Spark job execution"""
    
    spark = SparkSession.builder         .appName("FeatureEngineeringJob")         .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.1")         .getOrCreate()
    
    try:
        logger.info("Starting feature engineering job...")
        
        # Read Kafka topic
        raw_events_df = spark.readStream             .format("kafka")             .option("kafka.bootstrap.servers", "localhost:9092")             .option("subscribe", "rec_events.user_events")             .load()
        
        # Parse Kafka message
        events_df = raw_events_df.selectExpr(
            "CAST(key AS STRING) as user_id",
            "CAST(value AS STRING) as value"
        )
        
        from pyspark.sql.functions import from_json, to_json, struct
        from pyspark.sql.types import StructType, StringType
        
        # For batch processing, read from parquet
        interactions_df = spark.read.parquet("/data/interactions")
        
        # Load pre-existing dataframes
        users_df = spark.read.table("recommendation_db.users")
        items_df = spark.read.table("recommendation_db.items")
        
        # Generate features
        user_features = create_user_features(spark, interactions_df, users_df)
        item_features = create_item_features(spark, interactions_df, items_df)
        
        # Write to feature store
        user_features.write.mode("overwrite").parquet("/data/user_features")
        item_features.write.mode("overwrite").parquet("/data/item_features")
        
        logger.info("Feature engineering completed successfully!")
        
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
