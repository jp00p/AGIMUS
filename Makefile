REPO_OWNER?=jp00p
REPO_NAME?=AGIMUS
BOT_CONTAINER_NAME?=agimus
LOCAL_KIND_CONFIG?=kind-config.yaml
namespace?=agimus
SHELL=/bin/bash
DB_BACKUP_RESTORE_COMMIT?=main
ifneq (,$(wildcard ./.env))
    include .env
    export
endif

.PHONY: help
help: ## Displays this help dialog (to set repo/fork ownker REPO_OWNWER=[github-username])
	@echo "Friends of DeSoto Bot - github.com/$$REPO_OWNER/$$REPO_NAME:$(shell make --no-print-directory version)"
	@cat banner.txt
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Python stuff

.PHONY: setup
setup: ## Install python dependencies via requirements.txt
	@pip install -q -r requirements.txt --no-warn-script-location

.PHONY: start
start: setup ## Start the bot via python
	@python main.py

##@ Docker stuff

.PHONY: docker-build
docker-build: ## Build the docker containers for the bot and the database
	@docker-compose build

.PHONY: docker-pull
docker-pull: ## Pull the defined upstream containers for BOT_CONTAINER_NAME and BOT_CONTAINER_VERSION
	@docker-compose pull

.PHONY: docker-start
docker-start: ## Start the docker containers for the bot and the database
	@docker-compose up

.PHONY: docker-stop
docker-stop: ## Stop the docker containers for the bot and the database
	@docker-compose down

.PHONY: docker-restart
docker-restart: ## Restart the docker containers running mysql and AGIMUS
	@docker-compose down && docker-compose up

.PHONY: docker-logs
docker-logs: ## Tail the logs of running containers
	@docker-compose logs -f

.PHONY: docker-cleanup
docker-cleanup: ## Remove all AGIMUS containers from this system
	docker images | grep agimus | awk '{print $$3}' | xargs -I {} docker rmi -f {}
	docker images | grep mysql | awk '{print $$3}' | xargs -I {} docker rmi -f {}

.PHONY: docker-exec
docker-exec: ## Get a shell in a running AGIMUS container
	@docker-compose exec app bash

.PHONY: docker-lint
docker-lint: ## Lint the container with dockle
	dockle --version
	dockle --exit-code 1 $(BOT_CONTAINER_NAME):latest

##@ MySQL stuff

.PHONY: db-mysql
db-mysql: ## MySQL session in running db container
	@docker-compose exec db mysql -u$(DB_USER) -p$(DB_PASS) $(DB_NAME)

.PHONY: db-bash
db-bash: ## Bash session in running db container
	@docker-compose exec db bash

.PHONY: db-dump
db-dump: ## Dump the database to a file at $DB_DUMP_FILENAME
	@docker-compose exec app mysqldump -h$(DB_HOST) -u$(DB_USER) -p$(DB_PASS) -B $(DB_NAME) 2>/dev/null > $(DB_DUMP_FILENAME)

.PHONY: db-load
db-load: ## Load the database from a file at $DB_DUMP_FILENAME
	@docker-compose exec -T app mysql -h$(DB_HOST) -u$(DB_USER) -p$(DB_PASS) $(DB_NAME) < $(DB_DUMP_FILENAME)

.PHONY: db-migrate
db-migrate: ## Apply a migration/sql file to the database from a file at ./migrations/v#.#.#.sql
	@docker-compose exec -T app mysql -u$(DB_USER) -p$(DB_PASS) $(DB_NAME) < ./migrations/$(shell make version).sql

.PHONY: db-seed
db-seed: ## Reload the database from a file at $DB_SEED_FILEPATH
	@docker-compose exec -T app mysql -h$(DB_HOST) -u$(DB_USER) -p$(DB_PASS) <<< "DROP DATABASE IF EXISTS FoD;"
	@docker-compose exec -T app mysql -h$(DB_HOST) -u$(DB_USER) -p$(DB_PASS) <<< "create database FoD;"
	@docker-compose exec -T app mysql -h$(DB_HOST) -u$(DB_USER) -p$(DB_PASS) $(DB_NAME) < $(DB_SEED_FILEPATH)

.PHONY: db-backup
db-backup: db-setup-git ## Back the database to a file at $DB_DUMP_FILENAME then commit it to the private database repository (intended to run inside AGIMUS container)
	@echo "Dumping db to $(DB_DUMP_FILENAME)"
	@mysqldump -h$(DB_HOST) -u$(DB_USER) -p$(DB_PASS) -B $(DB_NAME) > $(DB_DUMP_FILENAME)
	@rm -rf database || true
	git clone --depth 1 git@github.com:Friends-of-DeSoto/database.git
	@mkdir -p database/$(DB_BACKUP_SUB_DIR)
	cp $(DB_DUMP_FILENAME) database/$(DB_BACKUP_SUB_DIR)/agimus.sql
	pushd database/$(DB_BACKUP_SUB_DIR) \
		&& tar czf agimus.sql.tar.gz agimus.sql \
		&& du -sh agimus.sql* \
		&& git add agimus.sql.tar.gz \
		&& git commit -m "Backup AGIMUS DB: $(DB_BACKUP_SUB_DIR) $(shell date)" \
		&& git push origin main \
		&& popd

.PHONY: db-restore
db-restore: db-setup-git ## Restore the database from the private database repository (intended to run inside AGIMUS container)
	@rm -rf database || true
	git clone git@github.com:Friends-of-DeSoto/database.git \
		&& cd database \
		&& git reset --hard $(DB_BACKUP_RESTORE_COMMIT)
	@mkdir -p database/$(DB_BACKUP_SUB_DIR)
	pushd database/$(DB_BACKUP_SUB_DIR) \
		&& tar xzf agimus.sql.tar.gz \
		&& du -sh agimus.sql* \
		&& popd \
		&& cp database/$(DB_BACKUP_SUB_DIR)/agimus.sql $(DB_DUMP_FILENAME)
	@mysql -h$(DB_HOST) -u$(DB_USER) -p$(DB_PASS) <<< "DROP DATABASE IF EXISTS FoD;"
	@mysql -h$(DB_HOST) -u$(DB_USER) -p$(DB_PASS) <<< "create database FoD;"
	@mysql -h$(DB_HOST) -u$(DB_USER) -p$(DB_PASS) $(DB_NAME) < $(DB_DUMP_FILENAME)

.PHONY: db-setup-git
db-setup-git: ## Decode private deploy key environment variable and set up git for that user (intended to run inside AGIMUS container)
ifneq ("$(wildcard $(HOME)/.ssh/id_ed25519)","")
	@echo "$(HOME)/.ssh/id_ed25519 - ssh key already exists. skipping git setup..."
else
	mkdir -p $(HOME)/.ssh
	@echo $(DB_BACKUP_DEPLOY_KEY) | base64 -d > $(HOME)/.ssh/id_ed25519
	chmod 600 $(HOME)/.ssh/id_ed25519
	@git config --global user.name $(DB_BACKUP_GITHUB_USER)
	@git config --global user.email $(DB_BACKUP_GITHUB_EMAIL)
	ssh-keyscan github.com >> $(HOME)/.ssh/known_hosts
endif

##@ Kubernetes in Docker (KinD) stuff

.PHONY: kind
kind: kind-create kind-load helm-config-rm kind-test ## Create a KinD cluster, build docker container, load into cluster, and install with helm

.PHONY: kind-create
kind-create: ## Create a KinD cluster with local config-yaml
	kind create cluster --config $(LOCAL_KIND_CONFIG) || true

.PHONY: kind-load
kind-load: ## Load $BOT_CONTAINER_NAME into a running kind cluster
	@BOT_CONTAINER_VERSION=local make --no-print-directory docker-build
	kind load docker-image $(BOT_CONTAINER_NAME):local

.PHONY: kind-test
kind-test: ## Install AGIMUS into a running KinD cluster with helm
	@kubectl create namespace $(namespace) || true
	@make helm-config-rm
	@make helm-config
	helm upgrade --install --debug --wait \
		--namespace $(namespace) \
		--set image.repository=$(BOT_CONTAINER_NAME) \
		--set image.tag=local \
		agimus charts/agimus
	sleep 30
	kubectl --namespace $(namespace) get pods -o wide
	@make helm-db-load

.PHONY: kind-destroy
kind-destroy: ## Tear the KinD cluster down
	@kind delete cluster

##@ Helm stuff

.PHONY: helm-config
helm-config: ## Install the configmaps and secrets from .env and $(BOT_CONFIGURATION_FILEPATH) using helm
	@kubectl --namespace $(namespace) create configmap agimus-dotenv --from-file=.env || true
	@kubectl --namespace $(namespace) create configmap agimus-config --from-file=$(BOT_CONFIGURATION_FILEPATH) || true
	@kubectl --namespace $(namespace) create secret generic mysql-secret --from-literal=MYSQL_ROOT_PASSWORD=$(DB_PASS) || true

.PHONY: helm-config-rm
helm-config-rm: ## Delete configmaps and secrets
	@kubectl --namespace $(namespace) delete configmap agimus-dotenv --ignore-not-found=true
	@kubectl --namespace $(namespace) delete configmap agimus-config --ignore-not-found=true
	@kubectl --namespace $(namespace) delete secret mysql-secret --ignore-not-found=true

.PHONY: helm-install
helm-install: helm-config ## Install AGIMUS helm chart
	helm upgrade --install --debug --wait \
		--create-namespace \
		--namespace $(namespace) \
		--set image.repository=$(BOT_CONTAINER_NAME) \
		--set image.tag=$(shell make --no-print-directory version) \
		agimus agimus/agimus

.PHONY: helm-uninstall
helm-uninstall: helm-config-rm ## Remove AGIMUS helm chart
	@helm --namespace $(namespace) delete agimus

.PHONY: helm-db-load
helm-db-load: ## Load the database from a file at $DB_SEED_FILEPATH
	@kubectl --namespace $(namespace) exec -i $(shell make --no-print-directory helm-db-pod) \
		-- bash -c 'exec mysql -h127.0.0.1 -u"${DB_USER}" -p"${DB_PASS}"' < ${DB_SEED_FILEPATH}

.PHONY: helm-db-migrate
helm-db-migrate: ## Load the database from a file at $DB_SEED_FILEPATH
	@kubectl --namespace $(namespace) exec -i $(shell make --no-print-directory helm-db-pod) \
		-- bash -c 'exec mysql -h127.0.0.1 -u"${DB_USER}" -p"${DB_PASS}" ${DB_NAME}' < ./migrations/$(shell --no-print-directory make version).sql

.PHONY: helm-db-mysql
helm-db-mysql: ## Mysql session in mysql pod
	@kubectl --namespace $(namespace) exec -it $(shell make --no-print-directory helm-db-pod) \
		-- mysql -u"${DB_USER}" -p"${DB_PASS}"

.PHONY: helm-db-forward
helm-db-forward: ## Forward the mysql port 3306
	@kubectl --namespace $(namespace) port-forward svc/mysql-service 3306

.PHONY: helm-db-pod
helm-db-pod: ## Display the pod name for mysql
	@kubectl --namespace $(namespace) get pods --template '{{range .items}}{{.metadata.name}}{{end}}' --selector=app=mysql

.PHONY: helm-agimus-pod
helm-agimus-pod: ## Display the pod name for AGIMUS
	@kubectl --namespace $(namespace) get pods --template '{{range .items}}{{.metadata.name}}{{end}}' --selector=app=agimus

.PHONY: helm-bump-patch
helm-bump-patch: ## Bump-patch the semantic version of the helm chart using semver tool
	sed -i 's/'$(shell make version)'/v'$(shell semver bump patch $(shell make version))'/g' charts/agimus/Chart.yaml

.PHONY: helm-bump-minor
helm-bump-minor: ## Bump-minor the semantic version of the helm chart using semver tool
	sed -i 's/'$(shell make version)'/v'$(shell semver bump minor $(shell make version))'/g' charts/agimus/Chart.yaml

.PHONY: helm-bump-major
helm-bump-major: ## Bump-major the semantic version of the helm chart using semver tool
	sed -i 's/'$(shell make version)'/v'$(shell semver bump major $(shell make version))'/g' charts/agimus/Chart.yaml

##@ Miscellaneous stuff

.PHONY: update-badges
update-badges: ## Run the automated badge updater script, then commit the changes to a new branch and push
	@echo "Updating badges!"
	git checkout -b badge_updates/v$(shell semver bump minor $(shell make version))
	@python badge_updater.py
	@make helm-bump-minor
	git add charts \
		&& git add migrations \
		&& git add images \
		&& git commit -m "Committing Badge Update for v$(shell semver bump minor $(shell make version)) - $(shell date)" \
		&& git push --set-upstream origin badge_updates/v$(shell semver bump minor $(shell make version)) \
		&& git checkout main

.PHONY: update-shows
update-shows: ## Update the TGG metadata in the database via github action
	@curl -s -H "Accept: application/vnd.github.everest-preview+json" \
	    -H "Authorization: token $(GIT_TOKEN)" \
	    --request POST \
	    --data '{"event_type": "update-shows"}' \
	    https://api.github.com/repos/$(REPO_OWNER)/$(REPO_NAME)/dispatches

.PHONY: lint-actions
lint-actions: ## Run .gihtub/workflows/*.yaml|yml through action-valdator tool
	find .github/workflows -type f \( -iname \*.yaml -o -iname \*.yml \) \
		| xargs -I action_yaml action-validator --verbose action_yaml

.PHONY: version
version: ## Print the version of the bot from the helm chart (requires yq)
	@yq e '.version' charts/agimus/Chart.yaml

.PHONY: encode-config
encode-config: ## Print the base64 encoded contents of $(BOT_CONFIGURATION_FILEPATH) (Pro-Tip: pipe to pbcopy on mac)
	@cat $(BOT_CONFIGURATION_FILEPATH) | base64

.PHONY: encode-env
encode-env: ## Print the base64 encoded contents of the .env file  (Pro-Tip: pipe to pbcopy on mac)
	@cat .env | base64
