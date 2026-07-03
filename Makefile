.PHONY: test docker-checks

test:
	python -m pip install --upgrade pip setuptools
	python -m pip install -r backend/general_physician/requirements.txt
	pytest -q backend/general_physician/tests

docker-checks:
	docker compose -f docker-compose.checks.yml up --build --abort-on-container-exit --exit-code-from backend-checks
