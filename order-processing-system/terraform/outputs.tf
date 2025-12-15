output "api_gateway_url" {
  description = "API Gateway URL"
  value       = "${aws_apigatewayv2_api.main.api_endpoint}/${var.environment}"
}

output "api_endpoints" {
  description = "API Endpoints"
  value = {
    create_order     = "POST ${aws_apigatewayv2_api.main.api_endpoint}/${var.environment}/orders"
    get_order_status = "GET ${aws_apigatewayv2_api.main.api_endpoint}/${var.environment}/orders/{order_id}"
    list_orders      = "GET ${aws_apigatewayv2_api.main.api_endpoint}/${var.environment}/orders"
  }
}

output "ecr_repositories" {
  description = "ECR Repository URLs"
  value = {
    create_order_lambda     = aws_ecr_repository.create_order_lambda.repository_url
    get_order_status_lambda = aws_ecr_repository.get_order_status_lambda.repository_url
    order_processor         = aws_ecr_repository.order_processor.repository_url
  }
}

output "rds_endpoint" {
  description = "RDS Endpoint"
  value       = aws_db_instance.main.endpoint
}

output "sqs_queue_url" {
  description = "SQS Queue URL"
  value       = aws_sqs_queue.order_queue.url
}

output "sns_topic_arn" {
  description = "SNS Topic ARN"
  value       = aws_sns_topic.order_events.arn
}

output "ecs_cluster_name" {
  description = "ECS Cluster Name"
  value       = aws_ecs_cluster.main.name
}
