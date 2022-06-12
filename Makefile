REPO_OWNER:=jp00p
# REPO_OWNER:=mathew-fleisch
REPO_NAME:=FoDBot-SQL
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

.PHONY: docker-logs
docker-logs: ## Tail the logs of running containers
	@docker-compose logs -f

.PHONY: docker-stop
docker-stop: ## Stop the docker containers for the bot and the database
	@docker-compose down

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

##@ Miscellaneous stuff

.PHONY: update-tgg-metadata
update-tgg-metadata: ## Update the TGG metadata in the database via github action
	@curl -s -H "Accept: application/vnd.github.everest-preview+json" \
	    -H "Authorization: token $(GIT_TOKEN)" \
	    --request POST \
	    --data '{"event_type": "trigger-tgg-update"}' \
	    https://api.github.com/repos/$(REPO_OWNER)/$(REPO_NAME)/dispatches

.PHONY: help
help: ## Displays this help dialog
	@echo "Friends of DeSoto Bot"
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)
