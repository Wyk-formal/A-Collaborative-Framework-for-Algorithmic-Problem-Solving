# Neo4j Dump Deployment Subproject

This subproject provides a reproducible environment to deploy the Neo4j database from a pre-exported dump.

## Quick Start

### Option A: Use bundled dump
Put your `neo4j.dump` file into the `./dumps/` directory, then run:

```bash
docker compose up -d
```

### Option B: Download dump from Releases
```bash
scripts/get_dump.sh "<RELEASE_ASSET_URL>" neo4j.dump
docker compose up -d
```

### Access
- Browser: http://localhost:7474
- Bolt: `bolt://localhost:7687`
- Default credentials: `neo4j / passcode123` (please change password after first login)

## Notes
- Pinned version: Neo4j 5.26.10
- Default database: `neo4j`
- To enable APOC/GDS plugins, edit `docker-compose.yml` and uncomment `NEO4J_PLUGINS`.
