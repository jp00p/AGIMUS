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

.PHONY: start-docker
start-docker:
	docker-compose up -d --build

.PHONY: stop-docker
stop-docker:
	docker-compose down
