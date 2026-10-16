# ML Pipeline Documentation

## Pipeline Overview

The ML pipeline consists of several stages:

1. **Data Ingestion**: Collect raw events from Kafka
2. **Feature Engineering**: Transform raw data into features
3. **Model Training**: Train multiple models with experiments
4. **Model Evaluation**: Validate models against metrics
5. **Model Deployment**: Register and deploy best models
6. **Online Inference**: Serve predictions in production

## Data Pipeline

### Raw Event Collection
```python
class EventCollector:
    def __init__(self, config):
        self.consumer = KafkaConsumer(
            topics=config.topics,
            bootstrap_servers=config.brokers,
            value_deserializer=lambda m: json.loads(m.decode('utf-8'))
        )
        self.output_path = config.output_path
    
    def collect_and_save(self):
        for message in self.consumer:
            event = message.value
            self._process_event(event)
```

### Feature Engineering Pipeline
```python
from pyspark.sql import SparkSession

class FeatureEngineeringPipeline:
    def build_user_features(self, interactions_df, users_df):
        """Generate user-level features"""
        
        user_stats = interactions_df.groupBy('user_id').agg(
            F.count('item_id').alias('watch_count'),
            F.avg('duration').alias('avg_session_time')
        )
        
        return user_stats
```

## Model Architectures

### Two-Tower Network
```python
import torch
import torch.nn as nn

class TwoTowerNetwork(nn.Module):
    def __init__(self, user_feature_dim, item_feature_dim, hidden_dim, output_dim=512):
        super().__init__()
        
        self.user_tower = nn.Sequential(
            nn.Linear(user_feature_dim, hidden_dim),
            nn.ReLU(),
            nn.BatchNorm1d(hidden_dim),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, output_dim)
        )
        
        self.item_tower = nn.Sequential(
            nn.Linear(item_feature_dim, hidden_dim),
            nn.ReLU(),
            nn.BatchNorm1d(hidden_dim),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, output_dim)
        )
    
    def forward(self, user_features, item_features):
        user_embeddings = self.user_tower(user_features)
        item_embeddings = self.item_tower(item_features)
        
        user_embeddings = F.normalize(user_embeddings, p=2, dim=1)
        item_embeddings = F.normalize(item_embeddings, p=2, dim=1)
        
        return user_embeddings, item_embeddings

def contrastive_loss(user_embs, item_embs, temperature=0.07):
    labels = torch.arange(len(user_embs)).to(user_embs.device)
    pos_sim = torch.sum(user_embs * item_embs, dim=1) / temperature
    neg_sim = torch.matmul(user_embs, item_embs.T) / temperature
    loss = torch.nn.functional.cross_entropy(neg_sim, labels)
    return loss
```

### DeepFM Model
```python
class DeepFM(nn.Module):
    def __init__(self, fm_input_dim, dnn_input_dims, embed_dim, dnn_layers):
        super().__init__()
        
        self.fm_linear = nn.Linear(fm_input_dim, 1)
        self.fm_interaction = FMInteractionLayer(fm_input_dim)
        
        dnn_dims = [dnn_input_dim] + dnn_layers
        dnn_modules = []
        for i in range(len(dnn_dims) - 1):
            dnn_modules.extend([
                nn.Linear(dnn_dims[i], dnn_dims[i+1]),
                nn.ReLU(),
                nn.Dropout(0.2)
            ])
        self.dnn = nn.Sequential(*dnn_modules)
        self.dnn_output = nn.Linear(dnn_dims[-1], 1)
    
    def forward(self, fm_features, dnn_categoricals):
        linear_output = self.fm_linear(fm_features)
        fm_interaction = self.fm_interaction(dnn_categoricals)
        fm_output = linear_output + fm_interaction.flatten(start_dim=1)
        
        embedded = [self.embeddings[f'field_{i}'](cat) 
                   for i, cat in enumerate(dnn_categoricals)]
        flattened = torch.cat(embedded, dim=1)
        dnn_output = self.dnn(flattened)
        dnn_output = self.dnn_output(dnn_output)
        
        output = torch.sigmoid(fm_output + dnn_output)
        return output.squeeze()
```

## Evaluation Metrics
```python
class RecMetrics:
    @staticmethod
    def precision_at_k(relevant, predicted, k):
        cutoff = min(k, len(predicted))
        hits = sum(1 for item in predicted[:cutoff] if item in relevant)
        return hits / cutoff
    
    @staticmethod
    def recall_at_k(relevant, predicted, k):
        cutoff = min(k, len(predicted))
        hits = sum(1 for item in predicted[:cutoff] if item in relevant)
        return hits / len(relevant)
    
    @staticmethod
    def ndcg_at_k(relevant, predicted, k):
        cutoff = min(k, len(predicted))
        dcg = sum([
            2.0 / np.log2(i + 2) 
            for i, item in enumerate(predicted[:cutoff]) 
            if item in relevant
        ])
        ideal_dcg = sum([
            2.0 / np.log2(i + 2) 
            for i in range(min(len(relevant), k))
        ])
        return dcg / ideal_dcg if ideal_dcg > 0 else 0
```

## Model Registry
```python
from mlflow.tracking import MlflowClient

class ModelRegistry:
    def __init__(self):
        self.client = MlflowClient(tracking_uri=os.getenv('MLFLOW_TRACKING_URI'))
    
    def register_model(self, model_uri, model_name, stage='Staging'):
        model_version = self.client.register_model(model_uri, model_name)
        self.client.transition_model_version_stage(
            name=model_name,
            version=model_version.version,
            stage=stage
        )
        return model_version
    
    def get_latest_model(self, model_name, stage='Production'):
        latest = self.client.search_model_versions(
            f"name='{model_name}'",
            order_by=["version_number DESC"]
        )
        for mv in latest:
            if mv.current_stage == stage:
                return mv
```
