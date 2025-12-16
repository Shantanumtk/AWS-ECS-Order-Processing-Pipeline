#!/bin/bash
set -e

AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
PROJECT_NAME="order-processing"

echo "🔐 Logging into ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

echo "🏗️ Building and pushing Create Order Lambda..."
cd ../lambdas/create-order
docker build --platform linux/amd64 --provenance=false -t $PROJECT_NAME/create-order-lambda .
docker tag $PROJECT_NAME/create-order-lambda:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME/create-order-lambda:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME/create-order-lambda:latest

echo "🏗️ Building and pushing Get Order Status Lambda..."
cd ../get-order-status
docker build --platform linux/amd64 --provenance=false -t $PROJECT_NAME/get-order-status-lambda .
docker tag $PROJECT_NAME/get-order-status-lambda:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME/get-order-status-lambda:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME/get-order-status-lambda:latest

echo "🏗️ Building and pushing ECS Order Processor..."
cd ../../ecs-processor
docker build --platform linux/amd64 --provenance=false -t $PROJECT_NAME/order-processor .
docker tag $PROJECT_NAME/order-processor:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME/order-processor:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME/order-processor:latest

echo "🔄 Updating Lambda functions..."
aws lambda update-function-code --function-name $PROJECT_NAME-create-order --image-uri $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME/create-order-lambda:latest || true
aws lambda update-function-code --function-name $PROJECT_NAME-get-order-status --image-uri $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME/get-order-status-lambda:latest || true

echo "🔄 Updating ECS service..."
aws ecs update-service --cluster $PROJECT_NAME-cluster --service $PROJECT_NAME-order-processor --force-new-deployment || true

echo "✅ Deployment complete!"