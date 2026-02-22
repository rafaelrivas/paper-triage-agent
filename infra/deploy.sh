#!/bin/bash
# deploy to aws ecs fargate
# assumes aws cli configured, ecr repo exists
#
# usage: ./deploy.sh <aws-account-id> [region]

set -e

ACCOUNT_ID=${1:?"pass aws account id as first arg"}
REGION=${2:-"us-east-1"}
APP_NAME="paper-triage-agent"
ECR_REPO="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$APP_NAME"

echo "building docker image..."
cd "$(dirname "$0")/.."
docker build -f infra/Dockerfile -t $APP_NAME .

echo "pushing to ECR..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"
docker tag $APP_NAME:latest $ECR_REPO:latest
docker push $ECR_REPO:latest

# create cluster if needed
aws ecs describe-clusters --clusters $APP_NAME --region $REGION 2>/dev/null | grep -q "ACTIVE" || \
    aws ecs create-cluster --cluster-name $APP_NAME --region $REGION

# task role needs bedrock:InvokeModel if using bedrock
# the execution role is for ECR pull + cloudwatch, task role is for bedrock access
TASK_DEF=$(cat <<TASKEOF
{
  "family": "$APP_NAME",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::$ACCOUNT_ID:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::$ACCOUNT_ID:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "$APP_NAME",
      "image": "$ECR_REPO:latest",
      "portMappings": [{"containerPort": 8000, "protocol": "tcp"}],
      "environment": [
        {"name": "TRIAGE_MODEL", "value": "bedrock:us.anthropic.claude-sonnet-4-20250514-v1:0"},
        {"name": "AWS_DEFAULT_REGION", "value": "$REGION"},
        {"name": "PAPERS_DIR", "value": "/papers"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/$APP_NAME",
          "awslogs-region": "$REGION",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
TASKEOF
)

echo "$TASK_DEF" > /tmp/task-def.json
aws ecs register-task-definition --cli-input-json file:///tmp/task-def.json --region $REGION

echo ""
echo "done. create the service:"
echo "  aws ecs create-service --cluster $APP_NAME --service-name $APP_NAME \\"
echo "    --task-definition $APP_NAME --desired-count 1 --launch-type FARGATE \\"
echo "    --network-configuration 'awsvpcConfiguration={subnets=[YOUR_SUBNET],securityGroups=[YOUR_SG],assignPublicIp=ENABLED}' \\"
echo "    --region $REGION"
echo ""
echo "make sure ecsTaskRole has bedrock:InvokeModel permission."
echo "no API keys needed — bedrock auth uses the task's IAM role."
