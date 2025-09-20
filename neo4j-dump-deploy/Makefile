up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f --tail=200

clean:
	docker compose down -v
	rm -rf neo4j/data neo4j/logs

checksum:
	shasum -a 256 dumps/*.dump | tee dumps/neo4j.dump.sha256
