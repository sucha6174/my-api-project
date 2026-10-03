# Resilient & Scalable REST API with Terraform and AWS ECS Fargate

**Author**: KALARI SRISUCHA ([@sucha6174](https://github.com/sucha6174))  
**Repository**: [https://github.com/sucha6174/my-api-project](https://github.com/sucha6174/my-api-project)

A production-grade, highly available, and autoscaling REST API built using Python (FastAPI) and PostgreSQL, containerized with Docker multi-stage builds, and provisioned on Amazon Web Services (AWS) using Terraform. Deployments are fully automated via a declarative GitHub Actions CI/CD pipeline featuring automated post-deployment integration testing.

---

## Table of Contents
- [Architecture Overview](#architecture-overview)
- [Architectural Decisions & Trade-Offs](#architectural-decisions--trade-offs)
- [Local Development Setup](#local-development-setup)
- [API Documentation](#api-documentation)
- [Infrastructure as Code (Terraform)](#infrastructure-as-code-terraform)
- [Continuous Integration & Continuous Deployment (CI/CD)](#continuous-integration--continuous-deployment-cicd)
- [Automated Testing](#automated-testing)
- [Security Posture](#security-posture)

---

## Architecture Overview

```text
                  +---------------------------------------+
                  |            Internet (Public)          |
                  +-------------------+-------------------+
                                      |
                                      v [HTTP Port 80]
                  +-------------------+-------------------+
                  |      Application Load Balancer (ALB)   |
                  +-------------------+-------------------+
                                      | (Routes to Target Group)
                  +-------------------+-------------------+
                  |             AWS VPC (10.0.0.0/16)     |
                  |                                       |
                  |  +---------------------------------+  |
                  |  |      Public Subnets (ALB)       |  |
                  |  |      - 10.0.1.0/24 (AZ-a)       |  |
                  |  |      - 10.0.2.0/24 (AZ-b)       |  |
                  |  |      - NAT Gateway              |  |
                  |  +---------------------------------+  |
                  |  |      Private Subnets (ECS & DB) |  |
                  |  |      - 10.0.10.0/24 (AZ-a)      |  |
                  |  |      - 10.0.11.0/24 (AZ-b)      |  |
                  |  |                                 |  |
                  |  |  +---------------------------+  |  |
                  |  |  |   ECS Service (Fargate)   |  |  |
                  |  |  |  +-----+         +-----+  |  |  |
                  |  |  |  |Tasks|  <--->  |Tasks|  |  |  |
                  |  |  |  +-----+         +-----+  |  |  |
                  |  |  +---------------+-----------+  |  |
                  |  |                  | (Port 5432)  |  |
                  |  |                  v              |  |
                  |  |  +---------------+-----------+  |  |
                  |  |  |      RDS PostgreSQL DB    |  |  |
                  |  |  +---------------------------+  |  |
                  |  +---------------------------------+  |
                  +---------------------------------------+
```

### Core Components
1. **Application Load Balancer (ALB)**: Positioned in public subnets across two Availability Zones, terminating inbound public traffic on port 80 and routing requests to healthy ECS task instances.
2. **AWS ECS Fargate**: Serverless container orchestration running tasks inside private subnets across multiple AZs. Tasks scale dynamically between 2 and 4 instances based on CPU (80%) and memory (85%) target-tracking policies.
3. **AWS RDS (PostgreSQL 13)**: Managed relational database hosted in a dedicated private DB subnet group. Inaccessible from the internet; ingress is strictly limited to the ECS task security group.
4. **AWS Secrets Manager**: Generates and manages the database master password. Credentials are never written in source code or plain state; ECS injects the secret value directly into container environment variables at task startup.
5. **AWS NAT Gateway**: Located in a public subnet, granting outbound internet connectivity to private tasks for downloading container images from Amazon ECR and communicating with AWS API endpoints.
6. **Amazon Elastic Container Registry (ECR)**: Secure, private container registry configured with vulnerability scanning on image push.

---

## Architectural Decisions & Trade-Offs

### 1. Cloud Provider & Compute: AWS ECS Fargate
- **Why ECS Fargate over EC2**: Eliminates instance management, OS patching, and capacity planning. Fargate provides kernel-level task isolation, granular per-second billing, and native integration with Application Load Balancers and AWS IAM.
- **Why ECS over Kubernetes (EKS)**: For a stateless microservice architecture, ECS provides minimal operational complexity while delivering production-grade reliability, out-of-the-box CloudWatch logging, and rapid deployments.

### 2. Database Choice: AWS RDS PostgreSQL 13
- **Relational Integrity & Native UUIDs**: PostgreSQL natively supports the `uuid` data type and `uuid-ossp` / `gen_random_uuid()` generation, offering indexing efficiency for the primary keys required by `/message`.
- **Managed Reliability**: RDS manages automated snapshots, point-in-time recovery, automated minor version upgrades, and storage autoscaling.

### 3. Startup Resilience & Anti-Thundering Herd
- To prevent database connection storms when multiple container tasks initialize concurrently during an autoscaling event, `src/database.py` implements an exponential backoff retry loop with randomized jitter (`min(max_delay, base_delay * 2^(attempt-1)) + jitter`).

### 4. Strict Network Isolation
- **ALB Security Group**: Permits inbound HTTP (port 80) from `0.0.0.0/0`.
- **ECS Tasks Security Group**: Permits inbound TCP port 8000 only when originating from the ALB Security Group. Direct external inbound traffic is blocked.
- **RDS Database Security Group**: Permits inbound TCP port 5432 only when originating from the ECS Tasks Security Group. Direct inbound traffic from the ALB or internet is blocked.

---

## Local Development Setup

### Prerequisites
- [Docker](https://www.docker.com/) & [Docker Compose](https://docs.docker.com/compose/)
- [Python 3.11+](https://www.python.org/) (for running tests directly on the host)

### Quick Start
1. **Clone the repository**:
   ```bash
   git clone https://github.com/sucha6174/my-api-project.git
   cd my-api-project
   ```

2. **Configure environment variables**:
   ```bash
   cp .env.example .env
   ```

3. **Launch the local multi-container stack**:
   ```bash
   docker compose up --build -d
   ```
   *Docker Compose starts PostgreSQL 13, executes `init.sql`, performs database health checks, builds the multi-stage Docker image, and starts the FastAPI service on port 8000.*

4. **Verify container health**:
   ```bash
   docker compose ps
   curl http://localhost:8000/health
   ```

5. **Stop the stack**:
   ```bash
   docker compose down -v
   ```

---

## API Documentation

All endpoints return structured JSON.

### 1. Health Check
Used by the Application Load Balancer and container orchestrator to evaluate readiness and liveness.

- **URL**: `GET /health`
- **Response**: `200 OK`
- **Payload**:
  ```json
  {
    "status": "healthy"
  }
  ```
- **Example cURL**:
  ```bash
  curl -s http://localhost:8000/health
  ```

---

### 2. Greet User
Verifies dynamic path parameter parsing and routing.

- **URL**: `GET /greet/{name}`
- **Path Parameter**: `name` (string)
- **Response**: `200 OK`
- **Payload**:
  ```json
  {
    "message": "Hello, Alex!"
  }
  ```
- **Example cURL**:
  ```bash
  curl -s http://localhost:8000/greet/Alex
  ```

---

### 3. Store Message
Persists a message string to PostgreSQL and returns the generated UUID.

- **URL**: `POST /message`
- **Headers**: `Content-Type: application/json`
- **Payload Constraints**:
  - `text`: String, minimum length 1, maximum length 255.
- **Example Request**:
  ```json
  {
    "text": "Production verification payload."
  }
  ```
- **Response**: `201 Created`
- **Example Response**:
  ```json
  {
    "id": "e8d9101b-5309-4ce4-8e31-31ba34731df4",
    "text": "Production verification payload."
  }
  ```
- **Validation Failure (`400 Bad Request`)**:
  Returned when `text` is empty, missing, or exceeds 255 characters:
  ```json
  {
    "error": "Bad Request",
    "message": "Invalid input data provided.",
    "details": [
      {
        "type": "string_too_short",
        "loc": ["body", "text"],
        "msg": "String should have at least 1 characters"
      }
    ]
  }
  ```
- **Example cURL**:
  ```bash
  curl -X POST http://localhost:8000/message \
    -H "Content-Type: application/json" \
    -d '{"text": "Sample persistent message"}'
  ```

---

## Infrastructure as Code (Terraform)

Infrastructure is managed declaratively via HashiCorp Terraform in the `terraform/` directory.

### Prerequisites
- [AWS CLI v2](https://aws.amazon.com/cli/) configured with deployment credentials.
- [Terraform CLI](https://developer.hashicorp.com/terraform/downloads) (`>= 1.0.0`).

### Manual Deployment Steps
1. **Navigate to the Terraform configuration directory**:
   ```bash
   cd terraform
   ```

2. **Initialize Terraform providers and backend**:
   ```bash
   terraform init
   ```

3. **Preview resource provisioning**:
   ```bash
   terraform plan
   ```

4. **Apply infrastructure changes**:
   ```bash
   terraform apply -auto-approve
   ```

5. **Retrieve stack outputs**:
   ```bash
   terraform output api_url
   ```

6. **Teardown infrastructure when finished**:
   ```bash
   terraform destroy -auto-approve
   ```

---

## Continuous Integration & Continuous Deployment (CI/CD)

The repository includes a declarative GitHub Actions workflow located at `.github/workflows/main.yml`.

### Workflow Pipeline Stages
1. **Build & Test (`build-and-test`)**:
   - Executes on all pull requests and pushes to `main`.
   - Checks out the repository code.
   - Installs dependencies from `src/requirements.txt`.
   - Runs isolated unit tests (`python -m unittest discover -s tests/unit_tests`).
   - Builds the Docker image locally to validate the multi-stage build.
2. **Deploy & Verify (`deploy-infra-and-api`)**:
   - Executes automatically upon push to the `main` branch.
   - Configures AWS credentials via GitHub repository secrets.
   - Runs `terraform init`, `terraform plan`, and `terraform apply -auto-approve`.
   - Builds, tags, and pushes the production Docker image to Amazon ECR.
   - Issues a rolling update to the ECS Fargate service (`aws ecs update-service --force-new-deployment`).
   - Executes `scripts/wait_for_deployment.py` to block until the ALB health check reports HTTP 200.
   - Runs the live integration test suite against the live Application Load Balancer URL.

### Required GitHub Repository Secrets
Set these in your repository under **Settings > Secrets and variables > Actions**:
- `AWS_ACCESS_KEY_ID`: IAM user access key with deployment permissions.
- `AWS_SECRET_ACCESS_KEY`: IAM user secret access key.

---

## Automated Testing

### 1. Unit Tests
Unit tests use FastAPI's `TestClient` with database session dependency overrides (`app.dependency_overrides[get_db] = lambda: mock_db`) to test business logic and validation in complete isolation:

```bash
python -m unittest discover -s tests/unit_tests -p "test_*.py"
```

### 2. Integration Tests
Integration tests issue real HTTP calls using `httpx`. They can target local or deployed environments:

```bash
# Targeting local docker-compose environment:
export API_BASE_URL="http://localhost:8000"
python -m unittest discover -s tests/integration_tests -p "test_*.py"

# Targeting live cloud deployment:
export API_BASE_URL="http://<alb-dns-name>"
python -m unittest discover -s tests/integration_tests -p "test_*.py"
```

---

## Security Posture
- **Non-Root Container**: The Dockerfile builds under an unprivileged `appuser` (UID 10001) to limit the attack surface.
- **Zero Hardcoded Secrets**: Passwords are generated using Terraform's `random_password`, stored in AWS Secrets Manager, and injected into containers via ECS task execution roles.
- **Network Demarcation**: All compute and data storage layers reside strictly in private subnets, completely shielded from internet inbound traffic.
- **Strict Input Validation**: Request payloads are parsed and validated via Pydantic v2 to prevent injection attacks and database schema violations.
