web-view:
	@echo "Running Web App..."
	@python -m web.app
	@firefox-developer http://127.0.0.1:5000
dev:
	@echo "Running internship sync pipeline..."
	@python -m src.main

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

all:
	@./scripts/run.sh
