WS ?= Fabric User Group Demo
CAPACITY ?=

.PHONY: all data build test deploy dry-run clean
all: data build test

data:      ## regenerate the demo CSVs (deterministic)
	python3 src/data_gen/generate_data.py

build:     ## notebooks (.ipynb + Fabric item folders) and PBIP
	python3 src/tools/build_notebooks.py
	python3 src/tools/build_pbip.py

test:
	python3 -m unittest discover -s tests -v

dry-run:
	python3 src/deploy/deploy.py --workspace "$(WS)" --dry-run --with-notifications

deploy:    ## requires: pip install ms-fabric-cli && fab auth login
	python3 src/deploy/deploy.py --workspace "$(WS)" $(if $(CAPACITY),--capacity "$(CAPACITY)")

clean:
	rm -rf build
