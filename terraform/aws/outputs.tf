output "eks_cluster_name" {
  value = aws_eks_cluster.main.name
}

output "eks_cluster_endpoint" {
  value = aws_eks_cluster.main.endpoint
}

output "eks_cluster_certificate_authority_data" {
  value     = aws_eks_cluster.main.certificate_authority[0].data
  sensitive = true
}

output "rds_cluster_endpoint" {
  value = aws_rds_cluster.main.endpoint
}

output "elasticache_primary_endpoint" {
  value = aws_elasticache_replication_group.main.primary_endpoint_address
}

output "elasticache_reader_endpoints" {
  value = aws_elasticache_replication_group.main.reader_endpoints
}
