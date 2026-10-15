variable "region" {
  default = "us-east-1"
}

provider "aws" {
  region = var.region
}

# VPC
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "rec-engine-vpc"
  }
}

# Internet Gateway
resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "rec-engine-igw"
  }
}

# Public Subnets
resource "aws_subnet" "public_1" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = "${var.region}a"
  
  map_public_ip_on_launch = true

  tags = {
    Name = "rec-engine-public-1"
  }
}

resource "aws_subnet" "public_2" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = "${var.region}b"
  
  map_public_ip_on_launch = true

  tags = {
    Name = "rec-engine-public-2"
  }
}

# Private Subnets
resource "aws_subnet" "private_1" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.10.0/24"
  availability_zone = "${var.region}a"

  tags = {
    Name = "rec-engine-private-1"
  }
}

resource "aws_subnet" "private_2" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.11.0/24"
  availability_zone = "${var.region}b"

  tags = {
    Name = "rec-engine-private-2"
  }
}

# EKS Cluster
resource "aws_eks_cluster" "main" {
  name     = "rec-engine-cluster"
  role_arn = aws_iam_role.eks_role.arn
  version  = "1.28"

  vpc_config {
    subnet_ids = [
      aws_subnet.private_1.id,
      aws_subnet.private_2.id
    ]
  }

  depends_on = [
    aws_iam_role_policy_attachment.eks_cluster_policy
  ]
}

# IAM Role for EKS
resource "aws_iam_role" "eks_role" {
  name = "rec-engine-eks-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "eks.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "eks_cluster_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
  role       = aws_iam_role.eks_role.name
}

# RDS PostgreSQL
resource "aws_db_subnet_group" "main" {
  name       = "rec-engine-db-subnet-group"
  subnet_ids = [aws_subnet.private_1.id, aws_subnet.private_2.id]
}

resource "aws_security_group" "db_sg" {
  name        = "rec-engine-db-sg"
  description = "Security group for RDS"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.eks_sg.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "rec-engine-db-sg"
  }
}

resource "aws_rds_cluster" "main" {
  cluster_identifier      = "rec-engine-cluster"
  engine                  = "aurora-postgresql"
  engine_mode             = "provisioned"
  engine_version          = "14.7"
  database_name           = "recommendation_db"
  master_username         = "recengine"
  skip_final_snapshot     = true
  deletion_protection     = false

  db_subnet_group_name = aws_db_subnet_group.main.name

  vpc_security_group_ids = [aws_security_group.db_sg.id]

  serverlessv2_scaling_configuration {
    min_capacity = 0.5
    max_capacity = 8
  }
}

resource "aws_rds_cluster_instance" "primary" {
  identifier        = "rec-engine-primary"
  cluster_identifier = aws_rds_cluster.main.id
  instance_class    = "db.serverless"
  engine            = "aurora-postgresql"
  engine_version    = aws_rds_cluster.main.engine_version
  
  publicly_accessible = false
}

# ElastiCache Redis
resource "aws_security_group" "cache_sg" {
  name        = "rec-engine-cache-sg"
  description = "Security group for Redis"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.eks_sg.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "rec-engine-cache-sg"
  }
}

resource "aws_elasticache_replication_group" "main" {
  replication_group_id       = "rec-engine-redis"
  description                = "Redis cluster for feature store"
  engine                     = "redis"
  engine_version             = "6.x"
  node_type                  = "cache.r5.large"
  num_cache_nodes            = 3
  port                       = 6379
  parameter_group_name       = "default.redis6.x"
  security_group_ids         = [aws_security_group.cache_sg.id]
  subnet_group_name          = aws_db_subnet_group.main.name
  
  transit_encryption_enabled = true
  at_rest_encryption_enabled = true
  
  auto_minor_version_upgrade = true
}

# Output values
output "eks_cluster_endpoint" {
  value = aws_eks_cluster.main.endpoint
}

output "eks_cluster_name" {
  value = aws_eks_cluster.main.name
}

output "rds_cluster_endpoint" {
  value = aws_rds_cluster.main.endpoint
}

output "elasticache_endpoint" {
  value = aws_elasticache_replication_group.main.node_address[0]
}
