from typing import Dict, List, Optional
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
import logging
import mlflow
import mlflow.pytorch
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TwoTowerModel(nn.Module):
    """Two-Tower Neural Network for Recommendation"""
    
    def __init__(self, user_feature_dim: int, item_feature_dim: int, 
                 hidden_dim: int = 256, embedding_dim: int = 128):
        super().__init__()
        
        # User Tower
        self.user_tower = nn.Sequential(
            nn.Linear(user_feature_dim, hidden_dim),
            nn.ReLU(),
            nn.BatchNorm1d(hidden_dim),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.BatchNorm1d(hidden_dim // 2),
            nn.Linear(hidden_dim // 2, embedding_dim)
        )
        
        # Item Tower
        self.item_tower = nn.Sequential(
            nn.Linear(item_feature_dim, hidden_dim),
            nn.ReLU(),
            nn.BatchNorm1d(hidden_dim),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.BatchNorm1d(hidden_dim // 2),
            nn.Linear(hidden_dim // 2, embedding_dim)
        )
        
        self._initialize_weights()
    
    def forward(self, user_features: torch.Tensor, 
                item_features: torch.Tensor) -> tuple:
        user_embedding = self.user_tower(user_features)
        item_embedding = self.item_tower(item_features)
        
        # L2 normalize
        user_embedding = nn.functional.normalize(user_embedding, p=2, dim=1)
        item_embedding = nn.functional.normalize(item_embedding, p=2, dim=1)
        
        return user_embedding, item_embedding
    
    def _initialize_weights(self):
        for module in [self.user_tower, self.item_tower]:
            for name, param in module.named_parameters():
                if param.dim() > 1:
                    nn.init.xavier_uniform_(param)


def contrastive_loss(user_emb: torch.Tensor, item_emb: torch.Tensor, 
                    temperature: float = 0.07) -> torch.Tensor:
    """InfoNCE loss for two-tower networks"""
    batch_size = user_emb.size(0)
    
    # Compute similarities
    labels = torch.arange(batch_size).to(user_emb.device)
    similarities = torch.matmul(user_emb, item_emb.T) / temperature
    
    loss = nn.functional.cross_entropy(similarities, labels)
    return loss


class TrainingPipeline:
    """End-to-end ML training pipeline"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.model = None
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        
        # Initialize MLflow
        mlflow.set_tracking_uri(config.get("mlflow_uri", "http://localhost:5000"))
    
    def prepare_data(self, interactions_df: pd.DataFrame, 
                    users_df: pd.DataFrame, items_df: pd.DataFrame) -> tuple:
        """Prepare training data from raw DataFrames"""
        
        logger.info("Preparing training data...")
        
        # Merge interactions with user and item features
        merged = interactions_df.merge(users_df, on='user_id', how='left')
        merged = merged.merge(items_df, on='item_id', how='left')
        
        # Filter positive samples (e.g., watched or clicked)
        positive_mask = merged['event_type'].isin(['watch', 'click'])
        positive_samples = merged[positive_mask].copy()
        
        # Negative sampling
        negative_samples = []
        for _, row in positive_samples.iterrows():
            neg_item = items_df.sample(n=1).iloc[0]
            neg_row = row.copy()
            neg_row['item_id'] = neg_item['item_id']
            neg_row['event_type'] = 'negative'
            negative_samples.append(neg_row)
        
        negative_df = pd.DataFrame(negative_samples)
        combined = pd.concat([positive_samples, negative_df], ignore_index=True)
        
        # Encode categorical features
        combined['category_encoded'] = self.label_encoder.fit_transform(
            combined['category'].fillna('unknown')
        )
        
        # Prepare feature columns
        feature_cols = ['watch_count', 'avg_session_time', 'popularity_rank', 
                       'category_encoded', 'age_encoded']
        
        X_user = combined[[col for col in feature_cols if col.startswith('user_')]].values
        X_item = combined[[col for col in feature_cols if not col.startswith('user_')]].values
        y = (combined['event_type'] == 'positive').astype(int).values
        
        # Split data
        X_user_train, X_user_test, X_item_train, X_item_test, y_train, y_test =             train_test_split(X_user, X_item, y, test_size=0.2, random_state=42)
        
        # Scale features
        X_user_train = self.scaler.fit_transform(X_user_train)
        X_user_test = self.scaler.transform(X_user_test)
        X_item_train = self.scaler.fit_transform(X_item_train)
        X_item_test = self.scaler.transform(X_item_test)
        
        logger.info(f"Training set: {len(y_train)}, Test set: {len(y_test)}")
        
        return X_user_train, X_item_train, y_train, X_user_test, X_item_test, y_test
    
    def train(self, X_user_train: np.ndarray, X_item_train: np.ndarray,
             y_train: np.ndarray, X_user_val: np.ndarray, X_item_val: np.ndarray,
             y_val: np.ndarray) -> Dict:
        """Train the recommendation model"""
        
        logger.info("Starting model training...")
        
        # Convert to tensors
        X_user_train_t = torch.tensor(X_user_train, dtype=torch.float32)
        X_item_train_t = torch.tensor(X_item_train, dtype=torch.float32)
        y_train_t = torch.tensor(y_train, dtype=torch.float32)
        
        X_user_val_t = torch.tensor(X_user_val, dtype=torch.float32)
        X_item_val_t = torch.tensor(X_item_val, dtype=torch.float32)
        y_val_t = torch.tensor(y_val, dtype=torch.float32)
        
        # Create dataloaders
        train_dataset = TensorDataset(X_user_train_t, X_item_train_t, y_train_t)
        val_dataset = TensorDataset(X_user_val_t, X_item_val_t, y_val_t)
        
        train_loader = DataLoader(train_dataset, batch_size=256, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=256, shuffle=False)
        
        # Initialize model
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = TwoTowerModel(
            user_feature_dim=X_user_train.shape[1],
            item_feature_dim=X_item_train.shape[1],
            hidden_dim=self.config.get('hidden_dim', 256),
            embedding_dim=self.config.get('embedding_dim', 128)
        ).to(device)
        
        # Loss and optimizer
        criterion = contrastive_loss
        optimizer = optim.AdamW(self.model.parameters(), lr=0.001, weight_decay=0.01)
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', patience=5)
        
        # Training loop
        best_val_loss = float('inf')
        epochs = self.config.get('epochs', 50)
        
        mlflow.start_run()
        mlflow.log_params({
            "learning_rate": 0.001,
            "batch_size": 256,
            "hidden_dim": self.config.get('hidden_dim', 256),
            "embedding_dim": self.config.get('embedding_dim', 128),
            "epochs": epochs
        })
        
        for epoch in range(epochs):
            # Training
            self.model.train()
            train_loss = 0
            
            for user_batch, item_batch, labels_batch in train_loader:
                user_batch, item_batch = user_batch.to(device), item_batch.to(device)
                
                optimizer.zero_grad()
                user_emb, item_emb = self.model(user_batch, item_batch)
                loss = contrastive_loss(user_emb, item_emb)
                
                loss.backward()
                optimizer.step()
                
                train_loss += loss.item()
            
            train_loss /= len(train_loader)
            
            # Validation
            self.model.eval()
            val_loss = 0
            
            with torch.no_grad():
                for user_batch, item_batch, labels_batch in val_loader:
                    user_batch, item_batch = user_batch.to(device), item_batch.to(device)
                    
                    user_emb, item_emb = self.model(user_batch, item_batch)
                    loss = contrastive_loss(user_emb, item_emb)
                    val_loss += loss.item()
            
            val_loss /= len(val_loader)
            scheduler.step(val_loss)
            
            logger.info(f"Epoch {epoch+1}/{epochs} - Train Loss: {train_loss:.4f}, Val Loss: {val_loss:.4f}")
            
            # Log metrics
            mlflow.log_metric("train_loss", train_loss, step=epoch)
            mlflow.log_metric("val_loss", val_loss, step=epoch)
            
            # Save best model
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                torch.save(self.model.state_dict(), 'best_model.pth')
                logger.info(f"New best model with val_loss: {val_loss:.4f}")
        
        # Log final metrics
        mlflow.log_metric("best_val_loss", best_val_loss)
        
        # Register model
        model_uri = mlflow.pytorch.log_model(self.model, "two_tower_model").model_uri
        mlflow.register_model(model_uri, "two_tower_retrieval")
        
        run_id = mlflow.active_run().info.run_id
        mlflow.end_run()
        
        logger.info(f"Training completed! Run ID: {run_id}")
        
        return {
            "final_train_loss": train_loss,
            "final_val_loss": val_loss,
            "best_val_loss": best_val_loss,
            "run_id": run_id
        }
    
    def evaluate(self, X_user_test: np.ndarray, X_item_test: np.ndarray,
                y_test: np.ndarray) -> Dict:
        """Evaluate model performance"""
        
        self.model.eval()
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Load best model
        if self.model is None:
            self.model = TwoTowerModel(
                user_feature_dim=X_user_test.shape[1],
                item_feature_dim=X_item_test.shape[1]
            )
        
        self.model.load_state_dict(torch.load('best_model.pth', map_location=device))
        self.model.to(device)
        
        with torch.no_grad():
            user_emb, item_emb = self.model(
                torch.tensor(X_user_test, dtype=torch.float32).to(device),
                torch.tensor(X_item_test, dtype=torch.float32).to(device)
            )
            
            # Calculate accuracy
            predictions = torch.matmul(user_emb, item_emb.T) > 0
            y_test_tensor = torch.tensor(y_test, dtype=torch.float32).to(device)
            
            accuracy = (predictions.flatten() == y_test_tensor).float().mean().item()
        
        return {"test_accuracy": accuracy}


# Example usage
if __name__ == "__main__":
    config = {
        "mlflow_uri": "http://localhost:5000",
        "hidden_dim": 256,
        "embedding_dim": 128,
        "epochs": 50
    }
    
    pipeline = TrainingPipeline(config)
    # Note: This would be called with actual data in production
