resource "aws_sqs_queue" "order_queue" {
  name                       = "${var.project_name}-order-queue"
  delay_seconds              = 0
  max_message_size           = 262144
  message_retention_seconds  = 1209600
  receive_wait_time_seconds  = 20
  visibility_timeout_seconds = 300

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.order_dlq.arn
    maxReceiveCount     = 3
  })

  tags = { Name = "${var.project_name}-order-queue" }
}

resource "aws_sqs_queue" "order_dlq" {
  name                      = "${var.project_name}-order-dlq"
  message_retention_seconds = 1209600
  tags                      = { Name = "${var.project_name}-order-dlq" }
}

resource "aws_sqs_queue_policy" "order_queue_policy" {
  queue_url = aws_sqs_queue.order_queue.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sqs:SendMessage"
      Resource  = aws_sqs_queue.order_queue.arn
    }]
  })
}

resource "aws_ssm_parameter" "sqs_queue_url" {
  name  = "/${var.project_name}/${var.environment}/sqs/queue-url"
  type  = "String"
  value = aws_sqs_queue.order_queue.url
}
