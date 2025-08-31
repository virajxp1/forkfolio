build:
	docker build -t myapp -f docker/Dockerfile .

up:
	docker compose -f docker/docker-compose.yml up --build

test:
	pytest -q

