.PHONY: help install run clean smtp-build smtp-up smtp-down smtp-logs

# Default keyword and resume parameters (can be overridden on command line)
KEYWORD ?= KBRI Singapore local staff karir
RESUME ?= resume.txt

help:
	@echo "Available commands:"
	@echo "  make install      - Install Python dependencies"
	@echo "  make run          - Run the Career Scout multi-agent orchestration workflow"
	@echo "                      (Override with: make run KEYWORD=\"KBRI Canberra\" RESUME=\"other.pdf\")"
	@echo "  make clean        - Remove Python caches and stop the local SMTP container"
	@echo "  make smtp-build   - Build the local mock SMTP server (Mailpit) Docker image"
	@echo "  make smtp-up      - Run the local mock SMTP server in the background"
	@echo "                      (Web UI: http://localhost:8025, SMTP: localhost:1025)"
	@echo "  make smtp-down    - Stop and remove the local mock SMTP server container"
	@echo "  make smtp-logs    - Show running logs of the mock SMTP server"

install:
	pip install pydantic beautifulsoup4 pypdf openai python-dotenv

run:
	python3 orchestrator.py "$(KEYWORD)" "$(RESUME)"

clean: smtp-down
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -f *.pyc
	rm -f *.pyo
	rm -f *.pyd

smtp-build:
	docker build -t local-smtp -f Dockerfile.smtp .

smtp-up: smtp-build
	@docker rm -f local-smtp 2>/dev/null || true
	docker run -d --name local-smtp -p 1025:1025 -p 8025:8025 local-smtp
	@echo "🚀 Mock SMTP server running! Send emails via localhost:1025."
	@echo "👉 Open http://localhost:8025 in your browser to view emails in the Web UI."

smtp-down:
	@docker stop local-smtp 2>/dev/null || true
	@docker rm local-smtp 2>/dev/null || true
	@echo "🛑 Mock SMTP server stopped and removed."

smtp-logs:
	docker logs local-smtp
