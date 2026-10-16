# Deployment Guide

## Development Deployment

### Local Setup
```bash
# Start all services
docker-compose up -d

# Run database migrations
docker-compose exec backend python -m app.core.database.migrate

# Seed sample data
docker-compose exec backend python -m ml.inference.seed_data

# Access services
echo "Frontend: http://localhost:3000"
echo "Backend API: http://localhost:8000/docs"
echo "Qdrant: http://localhost:6333"
echo "MLflow: http://localhost:5000"
```

## Production Deployment (AWS)

### Step 1: Infrastructure Provisioning
```bash
cd terraform/aws
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

### Step 2: Kubernetes Deployment
```bash
kubectl apply -f ../kubernetes/deployments/namespace.yaml
kubectl apply -f ../kubernetes/services/database.yaml
kubectl apply -f ../kubernetes/deployments/backend-deployment.yaml
kubectl apply -f ../kubernetes/ingress/application-ingress.yaml
```

### Step 3: Monitoring Setup
```bash
helm install prometheus stable/prometheus-operator --namespace monitoring
helm install grafana stable/grafana --namespace monitoring
kubectl apply -f monitoring/grafana/dashboards/
```

## CI/CD Pipeline

GitHub Actions workflow for automated deployment:
- Test → Build Docker images → Push to ECR → Deploy to K8s

## Security Best Practices

- Use AWS Secrets Manager for credentials
- Implement network policies
- Enable TLS for all communication
- Regular security audits

## Performance Optimization

### Horizontal Pod Autoscaler
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: rec-engine-backend
  minReplicas: 5
  maxReplicas: 50
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        averageUtilization: 70
```

### Database Optimization
```sql
CREATE INDEX idx_interactions_user_time ON interactions(user_id, event_time DESC);
CREATE INDEX idx_interactions_item_time ON interactions(item_id, event_time DESC);
```

## Troubleshooting

Common issues and solutions:
- High latency: Check pod resources and query performance
- Memory leaks: Monitor memory usage over time
- Kafka lag: Check consumer group offsets
