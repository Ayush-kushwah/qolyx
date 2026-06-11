import sqlite3
import os

db_path = "qolyx_local.db"
print(f"Connecting to database: {db_path}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 1. Drop existing lineage tables to start clean
tables = ["lineage_edge_history", "lineage_edges", "lineage_nodes"]
for table in tables:
    cursor.execute(f"DROP TABLE IF EXISTS {table}")
    print(f"Dropped {table}")

# 2. Create lineage_nodes
cursor.execute("""
CREATE TABLE lineage_nodes (
    id VARCHAR(36) NOT NULL PRIMARY KEY,
    node_id VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,
    schema VARCHAR(255) NOT NULL,
    database VARCHAR(255),
    materialized_type VARCHAR(50),
    owner VARCHAR(255),
    description TEXT,
    meta JSON,
    trust_score FLOAT,
    last_updated_at DATETIME,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
)
""")
cursor.execute("CREATE INDEX ix_lineage_nodes_node_id ON lineage_nodes (node_id)")
print("Created table lineage_nodes and indexes.")

# 3. Create lineage_edges
cursor.execute("""
CREATE TABLE lineage_edges (
    id VARCHAR(36) NOT NULL PRIMARY KEY,
    source_node_id VARCHAR(255) NOT NULL,
    target_node_id VARCHAR(255) NOT NULL,
    edge_type VARCHAR(50) NOT NULL,
    valid_from DATETIME NOT NULL,
    valid_to DATETIME,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY (source_node_id) REFERENCES lineage_nodes(node_id) ON DELETE CASCADE,
    FOREIGN KEY (target_node_id) REFERENCES lineage_nodes(node_id) ON DELETE CASCADE
)
""")
cursor.execute("CREATE INDEX ix_lineage_edges_source_node_id ON lineage_edges (source_node_id)")
cursor.execute("CREATE INDEX ix_lineage_edges_target_node_id ON lineage_edges (target_node_id)")
cursor.execute("CREATE INDEX idx_lineage_edges_source_target ON lineage_edges (source_node_id, target_node_id)")
cursor.execute("CREATE INDEX idx_lineage_edges_valid_from_to ON lineage_edges (valid_from, valid_to)")
print("Created table lineage_edges and indexes.")

# 4. Create lineage_edge_history
cursor.execute("""
CREATE TABLE lineage_edge_history (
    id VARCHAR(36) NOT NULL PRIMARY KEY,
    source_node_id VARCHAR(255) NOT NULL,
    target_node_id VARCHAR(255) NOT NULL,
    edge_type VARCHAR(50) NOT NULL,
    valid_from DATETIME NOT NULL,
    valid_to DATETIME,
    recorded_at DATETIME NOT NULL
)
""")
cursor.execute("CREATE INDEX ix_lineage_edge_history_source_node_id ON lineage_edge_history (source_node_id)")
cursor.execute("CREATE INDEX ix_lineage_edge_history_target_node_id ON lineage_edge_history (target_node_id)")
cursor.execute("CREATE INDEX idx_lineage_history_source_target ON lineage_edge_history (source_node_id, target_node_id)")
cursor.execute("CREATE INDEX idx_lineage_history_valid_from_to ON lineage_edge_history (valid_from, valid_to)")
print("Created table lineage_edge_history and indexes.")

# 5. Align alembic_version to 03e4d60d721e
cursor.execute("DELETE FROM alembic_version")
cursor.execute("INSERT INTO alembic_version (version_num) VALUES ('03e4d60d721e')")
print("Updated alembic_version to head version '03e4d60d721e'.")

conn.commit()
conn.close()
print("Database schema successfully rebuilt!")
