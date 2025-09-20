"""
Configuration management module
"""

import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class DatabaseConfig:
    """Database configuration"""
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "passcode123"
    neo4j_database: str = "neo4j"

@dataclass
class AIConfig:
    """AI configuration"""
    zhipu_api_key: str = ""
    embedding_model: str = "embedding-2"
    chat_model: str = "glm-4.5"

@dataclass
class ValidationConfig:
    """Validation configuration"""
    time_limit: int = 5
    memory_limit: int = 256
    max_iterations: int = 8

@dataclass
class SystemConfig:
    """System configuration"""
    debug: bool = False
    show_query_warnings: bool = False
    log_level: str = "INFO"
    show_debug_info: bool = False

class Settings:
    """Global configuration management"""
    def __init__(self):
        self.database = DatabaseConfig(
            neo4j_uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            neo4j_user=os.getenv("NEO4J_USER", "neo4j"),
            neo4j_password=os.getenv("NEO4J_PASSWORD", "passcode123"),
            neo4j_database=os.getenv("NEO4J_DATABASE", "neo4j")
        )
        self.ai = AIConfig(
            zhipu_api_key=os.getenv("ZHIPU_API_KEY", ""),
            embedding_model=os.getenv("EMBEDDING_MODEL", "embedding-2"),
            chat_model=os.getenv("CHAT_MODEL", "glm-4.5")
        )
        self.validation = ValidationConfig(
            time_limit=int(os.getenv("TIME_LIMIT", "5")),
            memory_limit=int(os.getenv("MEMORY_LIMIT", "256")),
            max_iterations=int(os.getenv("MAX_ITERATIONS", "8"))
        )
        self.system = SystemConfig(
            debug=os.getenv("DEBUG", "false").lower() == "true",
            show_query_warnings=os.getenv("SHOW_QUERY_WARNINGS", "false").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            show_debug_info=os.getenv("SHOW_DEBUG_INFO", "false").lower() == "true"
        )

# Create global settings instance
settings = Settings()
