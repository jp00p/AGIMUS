.PHONY: build
build:
	@docker build -t ${BOT_CONTAINER_NAME} .

.PHONY: db-start
db-start:
	@echo "Starting mysql with docker:"
	@docker run --rm -dit \
		-p 3306:3306 \
		-e MYSQL_ROOT_PASSWORD=${DB_PASS} \
		--name ${DB_CONTAINER_NAME} \
		mysql:latest

.PHONY: db-mysql
db-mysql:
	@docker exec -it $(shell docker ps -aqf name=${DB_CONTAINER_NAME}) \
		mysql -u${DB_USER} -h${DB_HOST} -p${DB_PASS}

.PHONY: db-bash
db-bash:
	@docker exec -it $(shell docker ps -aqf name=${DB_CONTAINER_NAME}) \
		bash

.PHONY: db-dump
db-dump:
	@docker exec -it $(shell docker ps -aqf name=${DB_CONTAINER_NAME}) \
		bash -c 'mysqldump -u${DB_USER} -h${DB_HOST} -p${DB_PASS} -B ${DB_NAME} > /root/${DB_DUMP_FILENAME}'
	@docker cp $(shell docker ps -aqf name=${DB_CONTAINER_NAME}):/root/${DB_DUMP_FILENAME} ./${DB_DUMP_FILENAME}

.PHONY: db-load
db-load:
	@docker cp ./${DB_DUMP_FILENAME} $(shell docker ps -aqf name=${DB_CONTAINER_NAME}):/root/${DB_DUMP_FILENAME}
	@docker exec -it $(shell docker ps -aqf name=${DB_CONTAINER_NAME}) \
		bash -c 'mysql -u${DB_USER} -h${DB_HOST} -p${DB_PASS} < /root/${DB_DUMP_FILENAME}'

.PHONY: db-stop
db-stop:
	@docker rm -f $(shell docker ps -aqf name=${DB_CONTAINER_NAME})

.PHONY: setup
setup:
	@pip install -q -r requirements.txt

.PHONY: start
start: setup
	@python main.py

.PHONY: start-docker
start-docker:
	@docker run --rm -it \
		--name ${BOT_CONTAINER_NAME} \
		-v ${PWD}:/bot \
		-w /bot \
		${BOT_CONTAINER_NAME}

