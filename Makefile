REPO_OWNER?=jp00p
REPO_NAME?-=FoDBot-SQL
BOT_CONTAINER_NAME?=fodbot
LOCAL_KIND_CONFIG?=kind-config.yaml
ifneq (,$(wildcard ./.env))
    include .env
    export
endif

##@ Python stuff

.PHONY: setup
setup: ## Install python dependencies via requirements.txt
	@pip install -q -r requirements.txt

.PHONY: start
start: setup ## Start the bot via python
	@python main.py

##@ Docker stuff

.PHONY: docker-build
docker-build: ## Build the docker containers for the bot and the database
	@docker-compose build

.PHONY: docker-start
docker-start: ## Start the docker containers for the bot and the database
	@docker-compose up

.PHONY: docker-stop
docker-stop: ## Stop the docker containers for the bot and the database
	@docker-compose down

.PHONY: docker-logs
docker-logs: ## Tail the logs of running containers
	@docker-compose logs -f

.PHONY: docker-lint
docker-lint: ## Lint the container with dockle
	dockle --version
	dockle --exit-code 1 $(BOT_CONTAINER_NAME):latest

##@ MySQL stuff

.PHONY: db-mysql
db-mysql: ## MySQL session in running db container
	@docker-compose exec db mysql -u"${DB_USER}" -p"${DB_PASS}" "${DB_NAME}"

.PHONY: db-bash
db-bash: ## Bash session in running db container
	@docker-compose exec db bash

.PHONY: db-dump
db-dump: ## Dump the database to a file at ./$DB_DUMP_FILENAME
	@docker-compose exec db bash -c 'mysqldump -u"${DB_USER}" -p"${DB_PASS}" -B ${DB_NAME} 2>/dev/null' > ./${DB_DUMP_FILENAME}

.PHONY: db-load
db-load: ## Load the database from a file at ./$DB_DUMP_FILENAME
	@docker-compose exec -T db sh -c 'exec mysql -u"${DB_USER}" -p"${DB_PASS}" "${DB_NAME}"' < ./${DB_DUMP_FILENAME}


##@ Kubernetes in Docker (KinD) stuff

# yq '.nodes[0].extraMounts[0].hostPath="$(PWD)"' sample-kind-config.yaml > $(LOCAL_KIND_CONFIG)
.PHONY: kind-setup
kind-setup: docker-build ## create a KinD cluster with local config-yaml
	kind create cluster --config $(LOCAL_KIND_CONFIG) -v 5 || true
	make kind-load

.PHONY: kind-load
kind-load: ## load a locally built docker container into a running KinD cluster
	kind load docker-image $(BOT_CONTAINER_NAME):latest
	kind load docker-image mysql:latest

##@ Miscellaneous stuff

.PHONY: update-shows
update-shows: ## Update the TGG metadata in the database via github action
.PHONY: docker-restart
docker-restart:
	@docker-compose down && docker-compose up

.PHONY: update-tgg-metadata
update-tgg-metadata:
	@curl -s -H "Accept: application/vnd.github.everest-preview+json" \
	    -H "Authorization: token $(GIT_TOKEN)" \
	    --request POST \
	    --data '{"event_type": "update-shows"}' \
	    https://api.github.com/repos/$(REPO_OWNER)/$(REPO_NAME)/dispatches


.PHONY: lint-actions
lint-actions: ## run .gihtub/workflows/*.yaml|yml through action-valdator tool
	find .github/workflows -type f \( -iname \*.yaml -o -iname \*.yml \) \
		| xargs -I action_yaml action-validator --verbose action_yaml

.PHONY: version
version: ## Print the version of the bot from the helm chart (requires yq)
	@yq e '.version' charts/fodbot/Chart.yaml

.PHONY: help
help: ## Displays this help dialog (to set repo/fork ownker REPO_OWNWER=[github-username])
	@echo "Friends of DeSoto Bot"
	@echo "github.com/$$REPO_OWNER/$$REPO_NAME"
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)
