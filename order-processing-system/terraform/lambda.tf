resource "aws_cloudwatch_log_group" "create_order_lambda" {
  name              = "/aws/lambda/${var.project_name}-create-order"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "get_order_status_lambda" {
  name              = "/aws/lambda/${var.project_name}-get-order-status"
  retention_in_days = 7
}

resource "aws_lambda_function" "create_order" {
  function_name = "${var.project_name}-create-order"
  role          = aws_iam_role.lambda_exec.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.create_order_lambda.repository_url}:latest"
  timeout       = 30
  memory_size   = 256

  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      DB_HOST       = aws_db_instance.main.address
      DB_NAME       = var.db_name
      DB_USERNAME   = var.db_username
      DB_PASSWORD   = var.db_password
      SQS_QUEUE_URL = aws_sqs_queue.order_queue.url
      ENVIRONMENT   = var.environment
    }
  }

  depends_on = [aws_cloudwatch_log_group.create_order_lambda, aws_ecr_repository.create_order_lambda]
  lifecycle { ignore_changes = [image_uri] }
}

resource "aws_lambda_function" "get_order_status" {
  function_name = "${var.project_name}-get-order-status"
  role          = aws_iam_role.lambda_exec.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.get_order_status_lambda.repository_url}:latest"
  timeout       = 30
  memory_size   = 256

  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      DB_HOST     = aws_db_instance.main.address
      DB_NAME     = var.db_name
      DB_USERNAME = var.db_username
      DB_PASSWORD = var.db_password
      ENVIRONMENT = var.environment
    }
  }

  depends_on = [aws_cloudwatch_log_group.get_order_status_lambda, aws_ecr_repository.get_order_status_lambda]
  lifecycle { ignore_changes = [image_uri] }
}

resource "aws_lambda_permission" "create_order_apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.create_order.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

resource "aws_lambda_permission" "get_order_status_apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_order_status.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}
