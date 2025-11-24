PYTHON ?= python3

.PHONY: run-irc-server run-irc-client run-http-server run-http-client

run-irc-server:
	$(PYTHON) -m src.server

run-irc-client:
	$(PYTHON) -m src.client

run-http-server:
	$(PYTHON) -m http_ver.server

run-http-client:
	$(PYTHON) -m http_ver.client --host 127.0.0.1 --port 8080 --channel "#general" --nick Guest

run-rps-server:
	$(PYTHON) -m RPS.server

run-rps-client:
	$(PYTHON) -m RPS.client --host 127.0.0.1 --port 9090
