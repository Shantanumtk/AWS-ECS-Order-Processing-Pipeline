# Order Processing System

A serverless order processing system built with AWS services and FastAPI.

## Architecture

```
Client → API Gateway → Lambda (Create/Get Order) → RDS PostgreSQL
                              ↓
                            SQS Queue
                              ↓
                        ECS Fargate (Processor)
                              ↓
                        SNS Notifications
```

## AWS Services (10 Total)

1. API Gateway - REST endpoints
2. Lambda (x2) - Serverless functions
3. SQS - Order queue
4. SNS - Notifications
5. ECS Fargate - Order processor
6. RDS PostgreSQL - Database
7. ECR - Container registry
8. VPC - Network isolation
9. IAM - Permissions
10. CloudWatch - Logging

## Quick Start

### 1. Configure Terraform
```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values
```

### 2. Deploy Infrastructure
```bash
terraform init
terraform apply
```

### 3. Build & Deploy Applications
```bash
cd scripts
./deploy.sh
```

## API Endpoints

### Create Order
```bash
POST /orders
{
  "customer_email": "customer@example.com",
  "customer_name": "John Doe",
  "items": [
    {"product_name": "Widget", "quantity": 2, "unit_price": 29.99}
  ]
}
```

### Get Order
```bash
GET /orders/{order_id}
```

### List Orders
```bash
GET /orders?status=PENDING&limit=10
```

## Order Statuses

PENDING → PROCESSING → PAYMENT_CONFIRMED → FULFILLED → COMPLETED
                ↓              ↓
           CANCELLED    PAYMENT_FAILED
