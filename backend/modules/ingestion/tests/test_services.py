import gzip
import io
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from backend.core.exceptions import QolyxException
from backend.modules.ingestion.models import BronzeFdaEvent, BronzeFinancialCandle, BronzeGithubEvent
from backend.modules.ingestion.services import IngestionService


@pytest.fixture
def mock_httpx_client():
    """Fixture to mock httpx.AsyncClient async context manager and client."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_redis():
    """Fixture to mock Redis client get and set methods."""
    with patch("backend.modules.ingestion.services.redis_client") as mock_redis_client:
        yield mock_redis_client


@pytest.fixture
def mock_db_session():
    """Fixture to mock SQLAlchemy database Session."""
    return MagicMock(spec=Session)


@pytest.fixture
def dummy_finnhub_key():
    """Fixture to mock the Finnhub API Key settings."""
    with patch("backend.modules.ingestion.services.settings") as mock_settings:
        mock_settings.FINNHUB_API_KEY = "dummy_finnhub_key"
        yield mock_settings


@pytest.fixture
def mock_github_gzipped_content():
    """Fixture to generate gzipped line-delimited JSON data for GitHub Archive response."""
    event = {
        "id": "12345",
        "type": "PushEvent",
        "actor": {"login": "test-actor"},
        "repo": {"name": "test-org/test-repo"},
        "payload": {"action": "created"},
        "created_at": "2024-01-01T00:00:00Z"
    }
    payload = json.dumps(event) + "\n"
    out = io.BytesIO()
    with gzip.GzipFile(fileobj=out, mode="wb") as f:
        f.write(payload.encode("utf-8"))
    return out.getvalue()


@pytest.mark.asyncio
async def test_fetch_finnhub_data_returns_dict(mock_httpx_client, dummy_finnhub_key):
    """Test fetching stock candle data from Finnhub returns parsed dictionary records."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json = MagicMock(return_value={
        "s": "ok",
        "c": [150.0],
        "h": [152.0],
        "l": [149.0],
        "o": [151.0],
        "t": [1700000000],
        "v": [1000]
    })
    
    mock_httpx_client.get = AsyncMock(return_value=mock_response)

    records = await IngestionService.fetch_finnhub_data()

    # 4 symbols (AAPL, MSFT, TSLA, GOOGL) * 1 candle each = 4 records
    assert len(records) == 4
    for record in records:
        assert isinstance(record, dict)
        assert "symbol" in record
        assert record["open_price"] == 151.0
        assert record["high_price"] == 152.0
        assert record["low_price"] == 149.0
        assert record["close_price"] == 150.0
        assert record["volume"] == 1000
        assert isinstance(record["candle_timestamp"], datetime)


@pytest.mark.asyncio
async def test_fetch_fda_data_returns_dict(mock_httpx_client, mock_redis):
    """Test fetching drug adverse events from openFDA returns parsed dictionary records."""
    mock_redis.get.return_value = "50"
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json = MagicMock(return_value={
        "results": [
            {
                "receiptdate": "20240101",
                "serious": "1",
                "reportercountry": "US",
                "patient": {
                    "drug": [{"medicinalproduct": "Aspirin"}],
                    "reaction": [{"reactionmeddrapt": "Headache"}]
                },
                "seriousnesshospitalization": "1"
            }
        ]
    })
    
    mock_httpx_client.get = AsyncMock(return_value=mock_response)

    records = await IngestionService.fetch_fda_data()

    assert len(records) == 1
    record = records[0]
    assert isinstance(record, dict)
    assert record["receipt_date"] == "20240101"
    assert record["serious"] == "1"
    assert record["reporter_country"] == "US"
    assert record["drug_name"] == "Aspirin"
    assert record["reaction_description"] == "Headache"
    assert record["seriousness_hospitalization"] == "1"
    assert "raw_payload" in record
    
    # Assert Redis offset was updated
    mock_redis.set.assert_called_once_with("ingestion:fda:offset", "100")


@pytest.mark.asyncio
async def test_fetch_github_data_returns_dict(mock_httpx_client, mock_redis, mock_github_gzipped_content):
    """Test fetching GitHub event data from GH Archive returns parsed dictionary records."""
    mock_redis.get.return_value = "0"
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.content = mock_github_gzipped_content
    
    mock_httpx_client.get = AsyncMock(return_value=mock_response)

    records = await IngestionService.fetch_github_data()

    assert len(records) == 1
    record = records[0]
    assert isinstance(record, dict)
    assert record["event_id"] == "12345"
    assert record["event_type"] == "PushEvent"
    assert record["actor_login"] == "test-actor"
    assert record["repo_name"] == "test-org/test-repo"
    assert record["payload_action"] == "created"
    assert isinstance(record["created_at"], datetime)
    assert "raw_payload" in record

    # Assert Redis hour counter was updated (incremented modulo 24)
    mock_redis.set.assert_called_once_with("ingestion:github:hour", "1")


def test_save_bronze_records_saves_to_db(mock_db_session):
    """Test saving bronze records persists them to database via SQLAlchemy session."""
    pipeline_run_id = uuid.uuid4()

    # 1. Finnhub
    finnhub_records = [
        {
            "symbol": "AAPL",
            "open_price": 150.0,
            "high_price": 155.0,
            "low_price": 149.0,
            "close_price": 152.0,
            "volume": 1000,
            "candle_timestamp": datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
        }
    ]
    IngestionService.save_bronze_records(mock_db_session, "finnhub", finnhub_records, pipeline_run_id)
    assert mock_db_session.add.call_count == 1
    added_finnhub = mock_db_session.add.call_args[0][0]
    assert isinstance(added_finnhub, BronzeFinancialCandle)
    assert added_finnhub.pipeline_run_id == pipeline_run_id
    assert added_finnhub.symbol == "AAPL"
    assert added_finnhub.close_price == 152.0
    mock_db_session.commit.assert_called_once()
    
    mock_db_session.reset_mock()

    # 2. FDA
    fda_records = [
        {
            "receipt_date": "20240101",
            "serious": "1",
            "reporter_country": "US",
            "drug_name": "Aspirin",
            "reaction_description": "Headache",
            "seriousness_hospitalization": "1",
            "raw_payload": {"test": "fda"}
        }
    ]
    IngestionService.save_bronze_records(mock_db_session, "fda", fda_records, pipeline_run_id)
    assert mock_db_session.add.call_count == 1
    added_fda = mock_db_session.add.call_args[0][0]
    assert isinstance(added_fda, BronzeFdaEvent)
    assert added_fda.pipeline_run_id == pipeline_run_id
    assert added_fda.drug_name == "Aspirin"
    mock_db_session.commit.assert_called_once()
    
    mock_db_session.reset_mock()

    # 3. GitHub
    github_records = [
        {
            "event_id": "12345",
            "event_type": "PushEvent",
            "actor_login": "test-actor",
            "repo_name": "test-org/test-repo",
            "payload_action": "created",
            "created_at": datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
            "raw_payload": {"test": "github"}
        }
    ]
    IngestionService.save_bronze_records(mock_db_session, "github", github_records, pipeline_run_id)
    assert mock_db_session.add.call_count == 1
    added_github = mock_db_session.add.call_args[0][0]
    assert isinstance(added_github, BronzeGithubEvent)
    assert added_github.pipeline_run_id == pipeline_run_id
    assert added_github.event_id == "12345"
    mock_db_session.commit.assert_called_once()
