## Reproduce Neo4j Dataset

This repository contains a Neo4j subproject under `infra/neo4j-dump-deploy/`.

### Quick Start
```bash
cd infra/neo4j-dump-deploy

# Option A: Use bundled dump
docker compose up -d

# Option B: Download dump from Releases
scripts/get_dump.sh "<RELEASE_ASSET_URL>" neo4j.dump
docker compose up -d
```

- Browser: http://localhost:7474  
- Bolt: `bolt://localhost:7687`  
- Default credentials: `neo4j / passcode123` (please change password after first login)  
- Version pinned: Neo4j 5.26.10
