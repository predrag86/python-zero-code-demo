# Deployment

## AWS ECS (Fargate)

### Prerequisites

- `ecsTaskExecutionRole` with `AmazonECSTaskExecutionRolePolicy` attached
- `ecsTaskRole` — can be empty for this app (no AWS API calls made)
- The OTel gateway must be reachable on port `4318` from the ECS task's VPC and security group
- Tasks run in `awsvpc` network mode; outbound TCP to the gateway must be allowed

### 1. Build, push to ECR, and register the task definition

```bash
export AWS_ACCOUNT_ID=123456789012
export AWS_REGION=eu-west-1
export OTEL_GATEWAY_HOST=otel-gateway.internal   # hostname reachable from ECS tasks

./deploy.sh
```

`deploy.sh` does three things:

1. Builds the image for `linux/amd64` and pushes it to ECR
2. Substitutes `<ACCOUNT_ID>`, `<REGION>`, and `<OTEL_GATEWAY_HOST>` in `ecs-task-definition.json`
3. Registers a new task definition revision via the AWS CLI

### 2. Deploy to your ECS service

```bash
aws ecs update-service \
  --cluster <your-cluster> \
  --service <your-service> \
  --task-definition inventory-service \
  --region "${AWS_REGION}"
```

## Docker Compose (local)

```bash
OTEL_GATEWAY_ENDPOINT=http://<your-gateway>:4318 docker compose up --build
```

The `SELF_URL` environment variable is set to `http://app:5000` in Compose so that
the `/chain` and `/burst` endpoints can call back to themselves over the internal
Docker network.
