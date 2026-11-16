.PHONY: demo-setup

BASE_URL ?= https://sendils-cognite.github.io/tepdk-retro-poker

demo-setup:
	python3 -u demo/setup.py "$(BASE_URL)"
