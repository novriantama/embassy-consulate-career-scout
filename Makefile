.PHONY: help install run clean

# Default keyword and resume parameters (can be overridden on command line)
KEYWORD ?= "KBRI Singapore local staff karir"
RESUME ?= resume.txt

help:
	@echo "Available commands:"
	@echo "  make install      - Install Python dependencies"
	@echo "  make run          - Run the Career Scout multi-agent orchestration workflow"
	@echo "                      (Override with: make run KEYWORD=\"KBRI Canberra\" RESUME=\"other.pdf\")"
	@echo "  make clean        - Remove Python caches and build artifacts"

install:
	pip install google-antigravity pydantic beautifulsoup4 pypdf

run:
	python3 orchestrator.py $(KEYWORD) $(RESUME)

clean:
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -f *.pyc
	rm -f *.pyo
	rm -f *.pyd
