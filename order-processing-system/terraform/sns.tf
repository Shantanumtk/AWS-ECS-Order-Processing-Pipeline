resource "aws_sns_topic" "order_events" {
  name = "${var.project_name}-order-events"
  tags = { Name = "${var.project_name}-order-events" }
}

resource "aws_sns_topic_subscription" "email" {
  count     = var.notification_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.order_events.arn
  protocol  = "email"
  endpoint  = var.notification_email
}

/*
resource "aws_sns_topic_subscription" "sms" {
  count     = var.notification_phone != "" ? 1 : 0
  topic_arn = aws_sns_topic.order_events.arn
  protocol  = "sms"
  endpoint  = var.notification_phone
}
*/
resource "aws_sns_topic_policy" "order_events_policy" {
  arn = aws_sns_topic.order_events.arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sns:Publish"
      Resource  = aws_sns_topic.order_events.arn
    }]
  })
}

resource "aws_ssm_parameter" "sns_topic_arn" {
  name  = "/${var.project_name}/${var.environment}/sns/topic-arn"
  type  = "String"
  value = aws_sns_topic.order_events.arn
}
