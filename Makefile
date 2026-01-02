.PHONY: help backup scrape web-view web-view-firefox web-view-brave all

# Default target - show help
.DEFAULT_GOAL := help

help:
	@echo "Available targets:"
	@echo "  make help           - Show this help message"
	@echo "  make backup         - Run the backup script"
	@echo "  make scrape         - Run scraping pipeline and save log"
	@echo "  make web-view       - Start web app in Brave browser"
	@echo "  make web-view-firefox - Start web app in Firefox"
	@echo "  make web-view-brave - Start web app in Brave browser"

# Run backup script
backup:
	@echo "Running backup..."
	@bash backup/backup.sh

# Run the scraping pipeline and save log
scrape:
	@echo "Running internship sync pipeline..."
	@mkdir -p logs
	@python -m src.main 2>&1 | tee logs/scrape_$(shell date +%Y%m%d_%H%M%S).log

# Run the web server and view it in the browser
web-view-firefox:
	@echo "Starting Web App..."
	@python -m web.app & \
	PID=$$!; \
	echo "Server PID: $$PID"; \
	trap "echo 'Stopping server'; kill $$PID" INT TERM; \
	while ! nc -z 127.0.0.1 5000; do sleep 0.2; done; \
	firefox-developer http://127.0.0.1:5000; \
	wait $$PID


web-view-brave:
	@echo "Starting Web App..."
	@python -m web.app & \
	PID=$$!; \
	echo "Server PID: $$PID"; \
	trap "echo 'Stopping server'; kill $$PID" INT TERM; \
	while ! nc -z 127.0.0.1 5000; do sleep 0.2; done; \
	brave-browser http://127.0.0.1:5000; \
	wait $$PID

web-view: web-view-brave

all: help