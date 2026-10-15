variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "development"
}

variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}

variable "backend_replicas" {
  description = "Number of backend service replicas"
  type        = number
  default     = 5
}

variable "min_replicas" {
  description = "Minimum replicas for HPA"
  type        = number
  default     = 2
}

variable "max_replicas" {
  description = "Maximum replicas for HPA"
  type        = number
  default     = 50
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.serverless"
}

variable "redis_node_type" {
  description = "ElastiCache node type"
  type        = string
  default     = "cache.r5.large"
}
