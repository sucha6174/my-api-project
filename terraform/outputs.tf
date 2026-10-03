output "api_url" {
  description = "The public HTTP URL of the Application Load Balancer"
  value       = "http://${aws_lb.api_lb.dns_name}"
}

output "ecr_repository_url" {
  description = "The container image repository URL in Amazon ECR"
  value       = aws_ecr_repository.api_repo.repository_url
}

output "rds_endpoint" {
  description = "The connection endpoint for the private RDS PostgreSQL instance"
  value       = aws_db_instance.api_db.endpoint
}

output "alb_dns_name" {
  description = "The canonical DNS name of the Application Load Balancer"
  value       = aws_lb.api_lb.dns_name
}
