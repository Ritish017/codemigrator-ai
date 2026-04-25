.PHONY: setup setup-api setup-web run-api run-web demo test smoke clean docker-up docker-down

setup: setup-api setup-web

setup-api:
	cd apps/api && python -m pip install -e .

setup-web:
	cd apps/web && npm install

run-api:
	cd apps/api && uvicorn main:app --reload --host 0.0.0.0 --port 8000

run-web:
	cd apps/web && npm run dev

demo:
	@echo "==> Starting CodeMigrator AI demo"
	@echo "    API: http://localhost:8000"
	@echo "    Web: http://localhost:3000"
	@echo ""
	@(make run-api &) && (make run-web)

test:
	cd apps/api && pytest -v

smoke:
	cd apps/api && python -m pytest tests/test_nemotron.py -v -s

docker-up:
	docker-compose up --build

docker-down:
	docker-compose down

clean:
	rm -rf apps/api/__pycache__ apps/api/**/__pycache__ apps/web/.next apps/web/node_modules .pytest_cache
