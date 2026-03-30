#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------------------------------
# Usage:
#   export AWS_ACCOUNT_ID=123456789012
#   export AWS_REGION=eu-west-1
#   export OTEL_GATEWAY_HOST=otel-gateway.internal   # hostname/IP reachable from ECS
#   ./deploy.sh
# ---------------------------------------------------------------------------

: "${AWS_ACCOUNT_ID:?Set AWS_ACCOUNT_ID}"
: "${AWS_REGION:?Set AWS_REGION}"
: "${OTEL_GATEWAY_HOST:?Set OTEL_GATEWAY_HOST}"

ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
IMAGE_NAME="inventory-service"
IMAGE_TAG="${IMAGE_TAG:-latest}"
FULL_IMAGE="${ECR_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"

echo "==> Authenticating with ECR"
aws ecr get-login-password --region "${AWS_REGION}" \
  | docker login --username AWS --password-stdin "${ECR_REGISTRY}"

echo "==> Creating ECR repository (skips if exists)"
aws ecr describe-repositories --repository-names "${IMAGE_NAME}" \
    --region "${AWS_REGION}" > /dev/null 2>&1 \
  || aws ecr create-repository --repository-name "${IMAGE_NAME}" \
       --region "${AWS_REGION}" > /dev/null

echo "==> Building image"
docker build --platform linux/amd64 -t "${FULL_IMAGE}" .

echo "==> Pushing image to ECR"
docker push "${FULL_IMAGE}"

echo "==> Registering ECS task definition"
# Substitute placeholders in the template
sed \
  -e "s|<ACCOUNT_ID>|${AWS_ACCOUNT_ID}|g" \
  -e "s|<REGION>|${AWS_REGION}|g" \
  -e "s|<OTEL_GATEWAY_HOST>|${OTEL_GATEWAY_HOST}|g" \
  ecs-task-definition.json \
  | aws ecs register-task-definition \
      --region "${AWS_REGION}" \
      --cli-input-json file:///dev/stdin

echo "==> Done. Deploy the new task definition revision to your ECS service."
