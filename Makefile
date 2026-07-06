.PHONY: test docker-checks

test:
	docker compose -f docker-compose.checks.yml up --build --abort-on-container-exit --exit-code-from backend-checks

docker-checks:
	docker compose -f docker-compose.checks.yml up --build --abort-on-container-exit --exit-code-from backend-checks
