-- Create schema for test results if it does not exist
CREATE SCHEMA IF NOT EXISTS test_results;

-- Drop existing table if it exists to replace it
DROP TABLE IF EXISTS test_results.dbt_test_results CASCADE;

-- Create the correct dbt_test_results table
CREATE TABLE IF NOT EXISTS test_results.dbt_test_results (
    unique_id VARCHAR(512) PRIMARY KEY,
    name VARCHAR(512) NOT NULL,
    status VARCHAR(32) NOT NULL,
    execution_time FLOAT,
    failures INT DEFAULT 0,
    model_name VARCHAR(256),
    column_name VARCHAR(256),
    severity VARCHAR(32),
    execution_completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance and queries
CREATE INDEX IF NOT EXISTS idx_dbt_test_results_status ON test_results.dbt_test_results(status);
CREATE INDEX IF NOT EXISTS idx_dbt_test_results_executed_at ON test_results.dbt_test_results(execution_completed_at);
