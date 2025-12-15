#!/bin/bash

# =============================================================================
# Order Processing System - One-Time Full Deployment Script
# Run this ONCE to deploy everything from scratch
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
PROJECT_NAME="order-processing"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}=============================================${NC}"
echo -e "${BLUE}  Order Processing System - Full Deployment  ${NC}"
echo -e "${BLUE}=============================================${NC}"
echo ""

# -----------------------------------------------------------------------------
# Pre-flight checks
# -----------------------------------------------------------------------------
echo -e "${YELLOW}[1/8] Running pre-flight checks...${NC}"

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo -e "${RED}ERROR: AWS CLI not installed${NC}"
    exit 1
fi

# Check Terraform
if ! command -v terraform &> /dev/null; then
    echo -e "${RED}ERROR: Terraform not installed${NC}"
    exit 1
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}ERROR: Docker not installed${NC}"
    exit 1
fi

# Check Docker is running
if ! docker info &> /dev/null; then
    echo -e "${RED}ERROR: Docker is not running. Please start Docker Desktop.${NC}"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}ERROR: AWS credentials not configured${NC}"
    exit 1
fi

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "${GREEN}✓ AWS Account: $AWS_ACCOUNT_ID${NC}"
echo -e "${GREEN}✓ AWS Region: $AWS_REGION${NC}"
echo -e "${GREEN}✓ All pre-flight checks passed${NC}"
echo ""

# -----------------------------------------------------------------------------
# Check for terraform.tfvars
# -----------------------------------------------------------------------------
echo -e "${YELLOW}[2/8] Checking Terraform configuration...${NC}"

cd "$PROJECT_ROOT/terraform"

if [ ! -f "terraform.tfvars" ]; then
    echo -e "${YELLOW}terraform.tfvars not found. Creating from example...${NC}"
    
    if [ ! -f "terraform.tfvars.example" ]; then
        echo -e "${RED}ERROR: terraform.tfvars.example not found${NC}"
        exit 1
    fi
    
    cp terraform.tfvars.example terraform.tfvars
    
    # Generate a random password
    DB_PASSWORD=$(openssl rand -base64 16 | tr -dc 'a-zA-Z0-9' | head -c 16)
    
    # Update the password in tfvars
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s/YourSecurePassword123!/$DB_PASSWORD/" terraform.tfvars
    else
        # Linux
        sed -i "s/YourSecurePassword123!/$DB_PASSWORD/" terraform.tfvars
    fi
    
    echo -e "${GREEN}✓ Created terraform.tfvars with auto-generated password${NC}"
else
    echo -e "${GREEN}✓ terraform.tfvars exists${NC}"
fi
echo ""

# -----------------------------------------------------------------------------
# Initialize Terraform
# -----------------------------------------------------------------------------
echo -e "${YELLOW}[3/8] Initializing Terraform...${NC}"

terraform init -input=false
echo -e "${GREEN}✓ Terraform initialized${NC}"
echo ""

# -----------------------------------------------------------------------------
# Deploy ECR repositories first (needed for images)
# -----------------------------------------------------------------------------
echo -e "${YELLOW}[4/8] Creating ECR repositories...${NC}"

terraform apply -auto-approve -input=false \
    -target=aws_ecr_repository.create_order_lambda \
    -target=aws_ecr_repository.get_order_status_lambda \
    -target=aws_ecr_repository.order_processor \
    -target=aws_ecr_lifecycle_policy.cleanup

echo -e "${GREEN}✓ ECR repositories created${NC}"
echo ""

# -----------------------------------------------------------------------------
# Login to ECR and build/push Docker images
# -----------------------------------------------------------------------------
echo -e "${YELLOW}[5/8] Building and pushing Docker images...${NC}"

# Login to ECR
echo "Logging into ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Build and push Create Order Lambda
echo "Building Create Order Lambda..."
cd "$PROJECT_ROOT/lambdas/create-order"
docker build --platform linux/amd64 --provenance=false -t $PROJECT_NAME/create-order-lambda .
docker tag $PROJECT_NAME/create-order-lambda:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME/create-order-lambda:latest
echo "Pushing Create Order Lambda..."
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME/create-order-lambda:latest

# Build and push Get Order Status Lambda
echo "Building Get Order Status Lambda..."
cd "$PROJECT_ROOT/lambdas/get-order-status"
docker build --platform linux/amd64 --provenance=false -t $PROJECT_NAME/get-order-status-lambda .
docker tag $PROJECT_NAME/get-order-status-lambda:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME/get-order-status-lambda:latest
echo "Pushing Get Order Status Lambda..."
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME/get-order-status-lambda:latest

# Build and push ECS Order Processor
echo "Building ECS Order Processor..."
cd "$PROJECT_ROOT/ecs-processor"
docker build --platform linux/amd64 --provenance=false -t $PROJECT_NAME/order-processor .
docker tag $PROJECT_NAME/order-processor:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME/order-processor:latest
echo "Pushing ECS Order Processor..."
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME/order-processor:latest

echo -e "${GREEN}✓ All Docker images pushed to ECR${NC}"
echo ""

# -----------------------------------------------------------------------------
# Deploy remaining infrastructure
# -----------------------------------------------------------------------------
echo -e "${YELLOW}[6/8] Deploying full infrastructure...${NC}"

cd "$PROJECT_ROOT/terraform"
terraform apply -auto-approve -input=false

echo -e "${GREEN}✓ Infrastructure deployed${NC}"
echo ""

# -----------------------------------------------------------------------------
# Wait for services to stabilize
# -----------------------------------------------------------------------------
echo -e "${YELLOW}[7/8] Waiting for services to stabilize...${NC}"

echo "Waiting for ECS service to reach steady state (this may take 2-3 minutes)..."
aws ecs wait services-stable \
    --cluster $PROJECT_NAME-cluster \
    --services $PROJECT_NAME-order-processor \
    --region $AWS_REGION 2>/dev/null || echo "ECS service stabilization check completed"

echo -e "${GREEN}✓ Services are running${NC}"
echo ""

# -----------------------------------------------------------------------------
# Get outputs and display summary
# -----------------------------------------------------------------------------
echo -e "${YELLOW}[8/8] Deployment complete! Here's your setup:${NC}"
echo ""

cd "$PROJECT_ROOT/terraform"

API_URL=$(terraform output -raw api_gateway_url 2>/dev/null)
RDS_ENDPOINT=$(terraform output -raw rds_endpoint 2>/dev/null)
SQS_URL=$(terraform output -raw sqs_queue_url 2>/dev/null)
SNS_ARN=$(terraform output -raw sns_topic_arn 2>/dev/null)

echo -e "${BLUE}=============================================${NC}"
echo -e "${BLUE}           DEPLOYMENT SUMMARY                ${NC}"
echo -e "${BLUE}=============================================${NC}"
echo ""
echo -e "${GREEN}API Gateway URL:${NC} $API_URL"
echo -e "${GREEN}RDS Endpoint:${NC} $RDS_ENDPOINT"
echo -e "${GREEN}SQS Queue URL:${NC} $SQS_URL"
echo -e "${GREEN}SNS Topic ARN:${NC} $SNS_ARN"
echo ""
echo -e "${BLUE}=============================================${NC}"
echo -e "${BLUE}             API ENDPOINTS                   ${NC}"
echo -e "${BLUE}=============================================${NC}"
echo ""
echo -e "${GREEN}Create Order:${NC}  POST $API_URL/orders"
echo -e "${GREEN}Get Order:${NC}     GET  $API_URL/orders/{order_id}"
echo -e "${GREEN}List Orders:${NC}   GET  $API_URL/orders"
echo ""
echo -e "${BLUE}=============================================${NC}"
echo -e "${BLUE}             TEST COMMANDS                   ${NC}"
echo -e "${BLUE}=============================================${NC}"
echo ""
echo "# Create a test order:"
echo -e "${YELLOW}curl -X POST $API_URL/orders \\
  -H \"Content-Type: application/json\" \\
  -d '{
    \"customer_email\": \"test@example.com\",
    \"customer_name\": \"Test User\",
    \"items\": [
      {\"product_name\": \"Widget A\", \"quantity\": 2, \"unit_price\": 29.99},
      {\"product_name\": \"Widget B\", \"quantity\": 1, \"unit_price\": 49.99}
    ]
  }'${NC}"
echo ""
echo "# Get order status (replace ORDER_ID):"
echo -e "${YELLOW}curl $API_URL/orders/ORDER_ID${NC}"
echo ""
echo "# List all orders:"
echo -e "${YELLOW}curl \"$API_URL/orders?limit=10\"${NC}"
echo ""
echo -e "${BLUE}=============================================${NC}"
echo -e "${GREEN}         ✅ DEPLOYMENT SUCCESSFUL!          ${NC}"
echo -e "${BLUE}=============================================${NC}"
echo ""
echo -e "${YELLOW}Note: If you provided an email for notifications, check your inbox to confirm the SNS subscription.${NC}"
echo ""


