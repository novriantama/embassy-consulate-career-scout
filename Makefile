.PHONY: help install run clean smtp-build smtp-up smtp-down smtp-logs

# Default keyword and resume parameters (can be overridden on command line)
KEYWORD ?= KBRI Singapore local staff karir
RESUME ?= resume.txt

help:
	@echo "Available commands:"
	@echo "  make install         - Install Python dependencies"
	@echo "  make ollama-install  - Install Ollama (via Homebrew) and pull qwen2.5 model"
	@echo "  make run             - Run the Career Scout multi-agent orchestration workflow"
	@echo "                         (Override with: make run KEYWORD=\"KBRI Canberra\" RESUME=\"other.pdf\")"
	@echo "  make clean           - Remove Python caches and stop the local SMTP container"
	@echo "  make smtp-build      - Build the local mock SMTP server (Mailpit) Docker image"
	@echo "  make smtp-up         - Run the local mock SMTP server in the background"
	@echo "                         (Web UI: http://localhost:8025, SMTP: localhost:1025)"
	@echo "  make smtp-down       - Stop and remove the local mock SMTP server container"
	@echo "  make smtp-logs       - Show running logs of the mock SMTP server"

install:
	pip install pydantic beautifulsoup4 pypdf openai python-dotenv

ollama-install:
	@if command -v ollama >/dev/null 2>&1; then \
		echo "✅ Ollama is already installed."; \
	else \
		if command -v brew >/dev/null 2>&1; then \
			echo "📥 Installing Ollama via Homebrew Cask..."; \
			brew install --cask ollama; \
		else \
			echo "❌ Homebrew is not installed. Please download Ollama manually from https://ollama.com"; \
			exit 1; \
		fi \
	fi
	@echo "🚀 Launching Ollama application..."
	@if [ -d "/Applications/Ollama.app" ]; then \
		open /Applications/Ollama.app; \
	else \
		open -a Ollama || true; \
	fi
	@echo "⏳ Waiting for Ollama server to respond on port 11434..."
	@success=0; \
	for i in {1..15}; do \
		if curl -s http://localhost:11434 >/dev/null; then \
			echo "✅ Ollama server is up and running!"; \
			success=1; \
			break; \
		fi; \
		sleep 2; \
	done; \
	if [ $$success -ne 1 ]; then \
		echo "⚠️ Ollama application start delayed or failed. Starting CLI background server instead..."; \
		nohup ollama serve >/dev/null 2>&1 & \
		sleep 5; \
	fi
	@echo "📥 Pulling Qwen 2.5 model..."
	ollama pull qwen2.5

run:
	python3 main.py "$(KEYWORD)" "$(RESUME)"

test:
	python3 -m unittest discover -s tests

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
