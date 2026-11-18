# Settings come from config/environment.json (copy config/environment.example.json).
# Override on the command line, e.g.  make deploy ARGS='--workspace "Other WS"'
CONFIG := $(if $(wildcard config/environment.json),config/environment.json,config/environment.example.json)
ARGS ?=

.PHONY: all data build test config dry-run deploy clean
all: data build test

data:      ## regenerate the demo CSVs (deterministic)
	python3 src/data_gen/generate_data.py

build:     ## notebooks (.ipynb + Fabric item folders) and PBIP
	python3 src/tools/build_notebooks.py
	python3 src/tools/build_pbip.py

test:
	python3 -m unittest discover -s tests -v

config:    ## create your local settings file from the template
	@test -f config/environment.json && echo "config/environment.json already exists" || \
	  (cp config/environment.example.json config/environment.json && echo "Created config/environment.json - edit it")

dry-run:   ## print every fab command without touching a tenant
	python3 src/deploy/deploy.py --config $(CONFIG) --dry-run $(ARGS)

deploy:    ## requires: pip install ms-fabric-cli && fab auth login
	python3 src/deploy/deploy.py --config config/environment.json $(ARGS)

clean:
	rm -rf build
