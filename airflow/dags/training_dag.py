from airflow import DAG
from airflow.providers.slack.operators.slack_webhook import SlackWebhookOperator
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import logging

default_args = {
    'owner': 'data-team',
    'start_date': datetime(2024, 1, 1),
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'email_on_failure': True,
    'email': ['data-team@company.com'],
}

dag = DAG(
    'ml_training_pipeline',
    default_args=default_args,
    description='ML model training pipeline',
    schedule_interval='@daily',
    catchup=False,
    tags=['ml', 'training']
)

def run_feature_engineering():
    """Run feature engineering Spark job"""
    from pyspark.sql import SparkSession
    
    spark = SparkSession.builder         .appName("FeatureEngineering")         .getOrCreate()
    
    # Import and run feature engineering
    from spark.jobs.feature_engineering import main
    main()
    
    spark.stop()

def train_model():
    """Train recommendation models"""
    import sys
    sys.path.append('/app/ml/training')
    
    from pipeline import TrainingPipeline
    import pandas as pd
    
    # Load features
    user_features = pd.read_parquet('/data/user_features')
    item_features = pd.read_parquet('/data/item_features')
    interactions = pd.read_parquet('/data/interactions')
    
    # Initialize and run training
    config = {
        'mlflow_uri': 'http://mlflow:5000',
        'hidden_dim': 256,
        'embedding_dim': 128,
        'epochs': 50
    }
    
    pipeline = TrainingPipeline(config)
    X_user_train, X_item_train, y_train = prepare_data(interactions, user_features, item_features)
    results = pipeline.train(X_user_train, X_item_train, y_train)
    
    print(f"Training completed: {results}")

def evaluate_model():
    """Evaluate trained model"""
    import mlflow
    import pandas as pd
    from sklearn.metrics import precision_score, recall_score, roc_auc_score
    
    mlflow.set_tracking_uri("http://mlflow:5000")
    
    run_id = get_latest_run_id()
    test_results = load_test_data()
    
    metrics = {
        'precision': precision_score(test_results['y_true'], test_results['y_pred']),
        'recall': recall_score(test_results['y_true'], test_results['y_pred']),
        'auc_roc': roc_auc_score(test_results['y_true'], test_results['y_proba'])
    }
    
    mlflow.log_metrics(metrics)
    log_evaluation_to_db(metrics, run_id)
    
    return metrics

def deploy_model_if_better():
    """Deploy new model if it's better than current one"""
    from mlflow.tracking import MlflowClient
    
    client = MlflowClient(tracking_uri="http://mlflow:5000")
    
    # Get latest run
    runs = search_best_runs(num_results=1)
    best_run = runs[0]
    
    # Compare with production model
    prod_run = get_production_model()
    
    if best_run.auc > prod_run.auc + 0.01:  # 1% improvement threshold
        promote_to_staging(best_run.run_id)
        send_notification(f"New model ready for staging: {best_run.run_id}")
    else:
        send_notification(f"Model did not meet improvement threshold")

# Define tasks
task_feature_eng = PythonOperator(
    task_id='feature_engineering',
    python_callable=run_feature_engineering,
    dag=dag
)

task_train = PythonOperator(
    task_id='train_model',
    python_callable=train_model,
    dag=dag
)

task_evaluate = PythonOperator(
    task_id='evaluate_model',
    python_callable=evaluate_model,
    dag=dag
)

task_deploy = PythonOperator(
    task_id='deploy_if_better',
    python_callable=deploy_model_if_better,
    dag=dag
)

# Set task dependencies
task_feature_eng >> task_train >> task_evaluate >> task_deploy
