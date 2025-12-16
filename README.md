# 🛒 Order Processing System

A production-ready, serverless order processing system built with AWS services and FastAPI. This system demonstrates event-driven architecture with real-time order tracking and email notifications.

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [AWS Services Used](#aws-services-used)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [API Reference](#api-reference)
- [Order Lifecycle](#order-lifecycle)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Deployment](#deployment)
- [Testing](#testing)
- [Monitoring & Logs](#monitoring--logs)
- [Cleanup](#cleanup)
- [Troubleshooting](#troubleshooting)

## Overview

This system provides a complete order management solution with the following capabilities:

- RESTful API for order creation and retrieval
- Asynchronous order processing using message queues
- Real-time email notifications at each order stage
- Persistent storage with PostgreSQL
- Auto-scaling based on demand
- Infrastructure as Code using Terraform

## Architecture

```
┌─────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Client    │────▶│   API Gateway   │────▶│  Lambda         │
│  (Postman)  │     │   (HTTP API)    │     │  (Create Order) │
└─────────────┘     └─────────────────┘     └────────┬────────┘
                                                     │
                            ┌────────────────────────┼────────────────────────┐
                            │                        │                        │
                            ▼                        ▼                        │
                    ┌───────────────┐        ┌───────────────┐               │
                    │      RDS      │        │      SQS      │               │
                    │  (PostgreSQL) │        │  (Order Queue)│               │
                    └───────────────┘        └───────┬───────┘               │
                            ▲                        │                        │
                            │                        ▼                        │
                            │                ┌───────────────┐               │
                            │                │  ECS Fargate  │               │
                            │                │  (Processor)  │               │
                            │                └───────┬───────┘               │
                            │                        │                        │
                            └────────────────────────┤                        │
                                                     │                        │
                                                     ▼                        │
                                             ┌───────────────┐               │
                                             │      SNS      │               │
                                             │ (Notifications)│               │
                                             └───────┬───────┘               │
                                                     │                        │
                                                     ▼                        │
                                             ┌───────────────┐               │
                                             │    Email      │               │
                                             │  Notification │               │
                                             └───────────────┘               │
                                                                              │
┌─────────────┐     ┌─────────────────┐     ┌─────────────────┐              │
│   Client    │────▶│   API Gateway   │────▶│     Lambda      │──────────────┘
│  (Postman)  │     │   (HTTP API)    │     │ (Get Order)     │
└─────────────┘     └─────────────────┘     └─────────────────┘
```

## AWS Services Used

| # | Service | Purpose |
|---|---------|---------|
| 1 | **API Gateway** | HTTP API endpoints for REST interface |
| 2 | **Lambda (Create Order)** | Serverless function to create orders |
| 3 | **Lambda (Get Order)** | Serverless function to retrieve orders |
| 4 | **SQS** | Message queue for async order processing |
| 5 | **SNS** | Email notifications for order updates |
| 6 | **ECS Fargate** | Container-based order processor |
| 7 | **RDS PostgreSQL** | Relational database for order storage |
| 8 | **ECR** | Container image registry |
| 9 | **VPC** | Network isolation and security |
| 10 | **IAM** | Access control and permissions |

**Additional:** CloudWatch (logging), NAT Gateway (outbound connectivity)

## Features

- ✅ RESTful API with FastAPI
- ✅ Serverless Lambda functions with container images
- ✅ Asynchronous processing with SQS
- ✅ Real-time email notifications with order details
- ✅ PostgreSQL database with automatic schema creation
- ✅ Auto-scaling ECS service
- ✅ Dead letter queue for failed messages
- ✅ Infrastructure as Code (Terraform)
- ✅ CI/CD ready deployment scripts

## Prerequisites

- **AWS CLI** configured with appropriate credentials
- **Terraform** >= 1.0
- **Docker** installed and running
- **curl** or **Postman** for API testing

## Quick Start

### 1. Clone and Configure

```bash
cd order-processing-system/terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`:
```hcl
aws_region         = "us-east-1"
environment        = "dev"
db_username        = "dbadmin"
db_password        = "YourSecurePassword123!"
notification_email = "your-email@example.com"
```

### 2. Deploy Everything

```bash
cd ../scripts
chmod +x full-deploy.sh
./full-deploy.sh
```

This script will:
- Create ECR repositories
- Build and push Docker images
- Deploy all AWS infrastructure
- Output your API endpoint

### 3. Confirm SNS Subscription

Check your email and confirm the AWS SNS subscription to receive order notifications.

## API Reference

**Base URL:** `https://{api-id}.execute-api.{region}.amazonaws.com/dev`

### Create Order

```http
POST /orders
Content-Type: application/json

{
    "customer_email": "customer@example.com",
    "customer_name": "John Doe",
    "items": [
        {
            "product_name": "Wireless Headphones",
            "quantity": 1,
            "unit_price": 99.99
        },
        {
            "product_name": "USB-C Cable",
            "quantity": 2,
            "unit_price": 12.99
        }
    ]
}
```

**Response:**
```json
{
    "order_id": "550e8400-e29b-41d4-a716-446655440000",
    "customer_email": "customer@example.com",
    "customer_name": "John Doe",
    "total_amount": 125.97,
    "status": "PENDING",
    "items": [...],
    "created_at": "2025-12-15T23:31:32.217442",
    "message": "Order created successfully and queued for processing"
}
```

### Get Order by ID

```http
GET /orders/{order_id}
```

**Response:**
```json
{
    "order_id": "550e8400-e29b-41d4-a716-446655440000",
    "customer_email": "customer@example.com",
    "customer_name": "John Doe",
    "total_amount": 125.97,
    "status": "COMPLETED",
    "items": [...],
    "status_history": [
        {"status": "COMPLETED", "message": "Order completed successfully", "created_at": "..."},
        {"status": "FULFILLED", "message": "Order has been fulfilled", "created_at": "..."},
        {"status": "PAYMENT_CONFIRMED", "message": "Payment processed successfully", "created_at": "..."},
        {"status": "PROCESSING", "message": "Order processing started", "created_at": "..."},
        {"status": "PENDING", "message": "Order created and queued for processing", "created_at": "..."}
    ],
    "created_at": "2025-12-15T23:31:32.217442",
    "updated_at": "2025-12-15T23:31:35.624084"
}
```

### List Orders

```http
GET /orders?limit=10&offset=0&status=COMPLETED&customer_email=customer@example.com
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `limit` | int | Max results (1-100, default: 50) |
| `offset` | int | Skip results for pagination |
| `status` | string | Filter by order status |
| `customer_email` | string | Filter by customer email |

## Order Lifecycle

```
PENDING ──────▶ PROCESSING ──────▶ PAYMENT_CONFIRMED ──────▶ FULFILLED ──────▶ COMPLETED
                    │                      │
                    ▼                      ▼
               CANCELLED            PAYMENT_FAILED
```

| Status | Description |
|--------|-------------|
| `PENDING` | Order created, waiting in queue |
| `PROCESSING` | Order picked up by processor |
| `PAYMENT_CONFIRMED` | Payment successfully processed |
| `PAYMENT_FAILED` | Payment processing failed |
| `FULFILLED` | Order packed and shipped |
| `COMPLETED` | Order delivered successfully |
| `CANCELLED` | Order cancelled |

## Project Structure

```
order-processing-system/
├── database/
│   └── init.sql                 # Database schema
├── ecs-processor/
│   ├── app/
│   │   ├── main.py              # SQS consumer and orchestrator
│   │   ├── processor.py         # Order processing logic
│   │   └── notifier.py          # SNS email notifications
│   ├── Dockerfile
│   └── requirements.txt
├── lambdas/
│   ├── create-order/
│   │   ├── handler.py           # Create order endpoint
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   └── get-order-status/
│       ├── handler.py           # Get/List orders endpoint
│       ├── Dockerfile
│       └── requirements.txt
├── scripts/
│   ├── deploy.sh                # Incremental deployment
│   └── full-deploy.sh           # Full deployment from scratch
├── terraform/
│   ├── main.tf                  # Provider configuration
│   ├── variables.tf             # Input variables
│   ├── outputs.tf               # Output values
│   ├── vpc.tf                   # VPC, subnets, security groups
│   ├── rds.tf                   # PostgreSQL database
│   ├── sqs.tf                   # Order queue and DLQ
│   ├── sns.tf                   # Notification topic
│   ├── ecr.tf                   # Container registries
│   ├── ecs.tf                   # Fargate cluster and service
│   ├── lambda.tf                # Lambda functions
│   ├── api-gateway.tf           # HTTP API
│   ├── iam.tf                   # IAM roles and policies
│   └── terraform.tfvars         # Configuration values
└── README.md
```

## Configuration

### Terraform Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `aws_region` | AWS region | `us-east-1` |
| `environment` | Environment name | `dev` |
| `project_name` | Project name prefix | `order-processing` |
| `db_name` | Database name | `orderdb` |
| `db_username` | Database username | `dbadmin` |
| `db_password` | Database password | *Required* |
| `db_instance_class` | RDS instance type | `db.t3.micro` |
| `ecs_cpu` | ECS task CPU units | `256` |
| `ecs_memory` | ECS task memory (MB) | `512` |
| `ecs_desired_count` | Number of ECS tasks | `1` |
| `notification_email` | Email for notifications | `""` |

## Deployment

### Full Deployment (First Time)

```bash
cd scripts
./full-deploy.sh
```

### Incremental Deployment (Updates)

```bash
cd scripts
./deploy.sh
```

### Manual Terraform Commands

```bash
cd terraform

# Initialize
terraform init

# Preview changes
terraform plan

# Apply changes
terraform apply

# Destroy infrastructure
terraform destroy
```

## Testing

### Using cURL

```bash
# Create order
curl -X POST https://YOUR_API_URL/dev/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customer_email": "test@example.com",
    "customer_name": "Test User",
    "items": [{"product_name": "Test Item", "quantity": 1, "unit_price": 29.99}]
  }'

# Get order
curl https://YOUR_API_URL/dev/orders/{order_id}

# List orders
curl "https://YOUR_API_URL/dev/orders?limit=10"
```

### Using Postman

Import the collection or manually create requests:

1. **Create Order:** POST to `/orders` with JSON body
2. **Get Order:** GET to `/orders/{order_id}`
3. **List Orders:** GET to `/orders` with optional query params

## Monitoring & Logs

### Lambda Logs

```bash
# Create Order Lambda
aws logs tail /aws/lambda/order-processing-create-order --follow

# Get Order Lambda
aws logs tail /aws/lambda/order-processing-get-order-status --follow
```

### ECS Processor Logs

```bash
aws logs tail /ecs/order-processing-order-processor --follow
```

### API Gateway Logs

```bash
aws logs tail /aws/apigateway/order-processing --follow
```

### ECS Service Status

```bash
aws ecs describe-services \
  --cluster order-processing-cluster \
  --services order-processing-order-processor \
  --query 'services[0].{status:status,running:runningCount,desired:desiredCount}'
```

## Cleanup

To avoid ongoing AWS charges, destroy all resources:

```bash
cd terraform
terraform destroy
```

This will remove:
- API Gateway
- Lambda functions
- ECS cluster and service
- RDS database
- SQS queues
- SNS topic
- ECR repositories
- VPC and networking
- All associated IAM roles

## Troubleshooting

### Common Issues

**1. "Not Found" error on API calls**
- Ensure the path includes the stage: `/dev/orders`
- Verify API Gateway routes: `aws apigatewayv2 get-routes --api-id YOUR_API_ID`

**2. Lambda image manifest error**
- Add `--provenance=false` to Docker build commands
- Rebuild and push images

**3. ECS task not starting**
- Check ECS logs for errors
- Verify security groups allow outbound traffic
- Ensure NAT Gateway is configured

**4. Database connection errors**
- Verify RDS security group allows Lambda/ECS access
- Check credentials in environment variables

**5. No email notifications**
- Confirm SNS subscription in your email
- Check SNS topic permissions

### Debug Commands

```bash
# Check Lambda configuration
aws lambda get-function --function-name order-processing-create-order

# Check SQS queue
aws sqs get-queue-attributes --queue-url YOUR_QUEUE_URL --attribute-names All

# Check ECS task definition
aws ecs describe-task-definition --task-definition order-processing-order-processor
```

---

## License

This project is for educational purposes.

## Author

Built as a demonstration of AWS serverless architecture and event-driven design patterns.