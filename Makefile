REPO_OWNER:=jp00p
# REPO_OWNER:=mathew-fleisch
REPO_NAME:=FoDBot-SQL
ifneq (,$(wildcard ./.env))
    include .env
    export
endif

.PHONY: db-mysql
db-mysql:
	@docker-compose exec db mysql -u"${DB_USER}" -p"${DB_PASS}" "${DB_NAME}"

.PHONY: db-bash
db-bash:
	@docker-compose exec db bash

.PHONY: db-dump
db-dump:
	@docker-compose exec db bash -c 'mysqldump -u"${DB_USER}" -p"${DB_PASS}" -B ${DB_NAME} 2>/dev/null' > ./${DB_DUMP_FILENAME}

.PHONY: db-load
db-load:
	@docker-compose exec -T db sh -c 'exec mysql -u"${DB_USER}" -p"${DB_PASS}" "${DB_NAME}"' < ./${DB_DUMP_FILENAME}

.PHONY: setup
setup:
	@pip install -q -r requirements.txt

.PHONY: start
start: setup
	@python main.py

.PHONY: docker-build
docker-build:
	@docker-compose build

.PHONY: docker-start
docker-start:
	@docker-compose up

.PHONY: docker-logs
docker-logs:
	@docker-compose logs -f

.PHONY: docker-stop
docker-stop:
	@docker-compose down

.PHONY: update-tgg-metadata
update-tgg-metadata:
	@curl -s -H "Accept: application/vnd.github.everest-preview+json" \
	    -H "Authorization: token $(GIT_TOKEN)" \
	    --request POST \
	    --data '{"event_type": "trigger-tgg-update"}' \
	    https://api.github.com/repos/$(REPO_OWNER)/$(REPO_NAME)/dispatches