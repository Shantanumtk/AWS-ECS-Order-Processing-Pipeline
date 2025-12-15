resource "aws_ecr_repository" "create_order_lambda" {
  name                 = "${var.project_name}/create-order-lambda"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration { scan_on_push = true }
  tags = { Name = "${var.project_name}-create-order-lambda" }
}

resource "aws_ecr_repository" "get_order_status_lambda" {
  name                 = "${var.project_name}/get-order-status-lambda"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration { scan_on_push = true }
  tags = { Name = "${var.project_name}-get-order-status-lambda" }
}

resource "aws_ecr_repository" "order_processor" {
  name                 = "${var.project_name}/order-processor"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration { scan_on_push = true }
  tags = { Name = "${var.project_name}-order-processor" }
}

resource "aws_ecr_lifecycle_policy" "cleanup" {
  for_each   = toset([aws_ecr_repository.create_order_lambda.name, aws_ecr_repository.get_order_status_lambda.name, aws_ecr_repository.order_processor.name])
  repository = each.value

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 5 images"
      selection    = { tagStatus = "any", countType = "imageCountMoreThan", countNumber = 5 }
      action       = { type = "expire" }
    }]
  })
}
