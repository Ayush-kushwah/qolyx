from typing import List
from backend.modules.contracts.schemas import ColumnExpectation, ContractCreate

bronze_financial_candles_contract: ContractCreate = ContractCreate(
    name="Finnhub Financial Candles Contract",
    table_name="bronze_financial_candles",
    schema_definition={
        "id": ColumnExpectation(data_type="uuid", nullable=False, is_required=True),
        "pipeline_run_id": ColumnExpectation(data_type="uuid", nullable=False, is_required=True),
        "symbol": ColumnExpectation(data_type="string", nullable=False, max_length=10, is_required=True),
        "open_price": ColumnExpectation(data_type="float", nullable=True, is_required=False),
        "high_price": ColumnExpectation(data_type="float", nullable=True, is_required=False),
        "low_price": ColumnExpectation(data_type="float", nullable=True, is_required=False),
        "close_price": ColumnExpectation(data_type="float", nullable=True, is_required=False),
        "volume": ColumnExpectation(data_type="integer", nullable=True, is_required=False),
        "candle_timestamp": ColumnExpectation(data_type="datetime", nullable=False, is_required=True),
        "ingested_at": ColumnExpectation(data_type="datetime", nullable=False, is_required=True),
    },
    is_active=True,
)

bronze_fda_events_contract: ContractCreate = ContractCreate(
    name="FDA Adverse Events Contract",
    table_name="bronze_fda_events",
    schema_definition={
        "id": ColumnExpectation(data_type="uuid", nullable=False, is_required=True),
        "pipeline_run_id": ColumnExpectation(data_type="uuid", nullable=False, is_required=True),
        "receipt_date": ColumnExpectation(data_type="string", nullable=True, max_length=8, is_required=False),
        "serious": ColumnExpectation(data_type="string", nullable=True, max_length=5, is_required=False),
        "reporter_country": ColumnExpectation(data_type="string", nullable=True, max_length=10, is_required=False),
        "drug_name": ColumnExpectation(data_type="string", nullable=True, max_length=255, is_required=False),
        "reaction_description": ColumnExpectation(data_type="string", nullable=True, max_length=1000, is_required=False),
        "seriousness_hospitalization": ColumnExpectation(data_type="string", nullable=True, max_length=5, is_required=False),
        "raw_payload": ColumnExpectation(data_type="json", nullable=False, is_required=True),
        "ingested_at": ColumnExpectation(data_type="datetime", nullable=False, is_required=True),
    },
    is_active=True,
)

bronze_github_events_contract: ContractCreate = ContractCreate(
    name="GitHub Archive Events Contract",
    table_name="bronze_github_events",
    schema_definition={
        "id": ColumnExpectation(data_type="uuid", nullable=False, is_required=True),
        "pipeline_run_id": ColumnExpectation(data_type="uuid", nullable=False, is_required=True),
        "event_id": ColumnExpectation(data_type="string", nullable=False, max_length=50, is_required=True),
        "event_type": ColumnExpectation(data_type="string", nullable=False, max_length=50, is_required=True),
        "actor_login": ColumnExpectation(data_type="string", nullable=True, max_length=255, is_required=False),
        "repo_name": ColumnExpectation(data_type="string", nullable=True, max_length=255, is_required=False),
        "payload_action": ColumnExpectation(data_type="string", nullable=True, max_length=50, is_required=False),
        "created_at": ColumnExpectation(data_type="datetime", nullable=True, is_required=False),
        "raw_payload": ColumnExpectation(data_type="json", nullable=False, is_required=True),
        "ingested_at": ColumnExpectation(data_type="datetime", nullable=False, is_required=True),
    },
    is_active=True,
)

ALL_CONTRACTS: List[ContractCreate] = [
    bronze_financial_candles_contract,
    bronze_fda_events_contract,
    bronze_github_events_contract,
]
