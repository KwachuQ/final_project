# Python Engineering Mentoring Program 2026 — Final Project

The specification documents are in the `docs` folder:
- requirements.md
- architecture.md

## Running the Application

The application is fully containerized and can be easily deployed on any machine using Docker.

### Prerequisites

- Docker and Docker Compose installed.

### Setup

1. Clone the repository and navigate into the project directory.
2. Create an environment file by copying the example:
   ```bash
   cp .env.example .env
   ```
3. (Optional) Adjust the environment variables in `.env` if needed.

### Running with Docker

To start the application and its dependencies (PostgreSQL, LocalStack for S3), simply run:
```bash
docker-compose up --build -d
```

The application will be accessible at http://localhost:8000.
You can check the API documentation at http://localhost:8000/docs.

### Stopping the Application

To stop the containers:
```bash
docker-compose down
```