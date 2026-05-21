import asyncio
import gzip
import io
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List
import httpx
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.core import events
from backend.core.events import redis_client
from backend.core.exceptions import QolyxException
from backend.modules.ingestion.models import BronzeFdaEvent, BronzeFinancialCandle, BronzeGithubEvent

logger = logging.getLogger("qolyx.ingestion.service")

# Map of ingestion source names to their corresponding dataset IDs
DATASET_IDS = {
    "finnhub": "finnhub.stock.candles",
    "fda": "fda.drug.adverse_events",
    "github": "github.archive.events",
}

class IngestionService:
    """Service to orchestrate and execute real data ingestion from external APIs into the Bronze staging tables."""

    @classmethod
    async def fetch_finnhub_data(cls) -> List[Dict[str, Any]]:
        """Fetches real stock candle data from Finnhub API for AAPL, MSFT, TSLA, and GOOGL.

        Returns:
            A list of dictionary records representing 1-minute stock candles.
        """
        api_key = settings.FINNHUB_API_KEY
        if not api_key:
            raise QolyxException("FINNHUB_API_KEY is not configured in settings.")

        symbols = ["AAPL", "MSFT", "TSLA", "GOOGL"]
        to_ts = int(time.time())
        from_ts = to_ts - 300  # Last 5 minutes

        records = []
        async with httpx.AsyncClient() as client:
            for symbol in symbols:
                url = "https://finnhub.io/api/v1/stock/candle"
                params = {
                    "symbol": symbol,
                    "resolution": "1",
                    "from": from_ts,
                    "to": to_ts,
                    "token": api_key
                }
                logger.info(
                    "Fetching stock candles from Finnhub API",
                    extra={"symbol": symbol, "from_ts": from_ts, "to_ts": to_ts}
                )
                try:
                    response = await client.get(url, params=params, timeout=10.0)
                    response.raise_for_status()
                    data = response.json()

                    if data.get("s") == "ok":
                        c_list = data.get("c", [])
                        h_list = data.get("h", [])
                        l_list = data.get("l", [])
                        o_list = data.get("o", [])
                        t_list = data.get("t", [])
                        v_list = data.get("v", [])

                        for i in range(len(t_list)):
                            records.append({
                                "symbol": symbol,
                                "open_price": float(o_list[i]) if o_list[i] is not None else None,
                                "high_price": float(h_list[i]) if h_list[i] is not None else None,
                                "low_price": float(l_list[i]) if l_list[i] is not None else None,
                                "close_price": float(c_list[i]) if c_list[i] is not None else None,
                                "volume": int(v_list[i]) if v_list[i] is not None else None,
                                "candle_timestamp": datetime.fromtimestamp(t_list[i], tz=timezone.utc)
                            })
                        logger.info(
                            "Successfully retrieved candles from Finnhub",
                            extra={"symbol": symbol, "candles_count": len(t_list)}
                        )
                    else:
                        logger.warning(
                            "Finnhub returned non-ok status for symbol",
                            extra={"symbol": symbol, "status": data.get("s")}
                        )
                except Exception as exc:
                    logger.error(
                        "Failed to fetch stock candles from Finnhub",
                        exc_info=True,
                        extra={"symbol": symbol}
                    )
                    raise QolyxException(f"Finnhub API fetch failure for {symbol}: {str(exc)}") from exc
        return records

    @classmethod
    async def fetch_fda_data(cls) -> List[Dict[str, Any]]:
        """Fetches real FDA Drug Adverse Events using Redis-based pagination offsets.

        Returns:
            A list of dictionary records representing FDA Drug Adverse Events.
        """
        offset_key = "ingestion:fda:offset"
        try:
            offset_str = redis_client.get(offset_key)
            offset = int(offset_str) if offset_str else 0
        except Exception as exc:
            logger.warning(
                "Failed to retrieve FDA offset from Redis, defaulting to 0",
                exc_info=True
            )
            offset = 0

        url = "https://api.fda.gov/drug/event.json"
        params = {
            "limit": 50,
            "skip": offset
        }
        logger.info(
            "Fetching FDA drug adverse events",
            extra={"limit": 50, "offset": offset}
        )

        records = []
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, params=params, timeout=15.0)
                response.raise_for_status()
                data = response.json()
                results = data.get("results", [])

                for result in results:
                    drugs = result.get("patient", {}).get("drug", [])
                    drug_name = drugs[0].get("medicinalproduct") if drugs else None

                    reactions = result.get("patient", {}).get("reaction", [])
                    reaction_desc = reactions[0].get("reactionmeddrapt") if reactions else None

                    records.append({
                        "receipt_date": result.get("receiptdate"),
                        "serious": result.get("serious"),
                        "reporter_country": result.get("reportercountry"),
                        "drug_name": drug_name,
                        "reaction_description": reaction_desc,
                        "seriousness_hospitalization": result.get("seriousnesshospitalization"),
                        "raw_payload": result
                    })

                # Update Redis offset
                next_offset = offset + 50
                if next_offset >= 25000:  # openFDA skip parameter is capped at 25000
                    next_offset = 0
                redis_client.set(offset_key, str(next_offset))
                logger.info(
                    "Successfully fetched FDA adverse events, updated Redis offset",
                    extra={"fetched_count": len(results), "next_offset": next_offset}
                )

            except Exception as exc:
                logger.error("Failed to fetch adverse events from openFDA", exc_info=True)
                raise QolyxException(f"openFDA API fetch failure: {str(exc)}") from exc

        return records

    @classmethod
    async def fetch_github_data(cls) -> List[Dict[str, Any]]:
        """Downloads real GitHub Archive event files and parses events by cycling through 0-23 hours.

        Returns:
            A list of dictionary records representing GitHub events.
        """
        hour_key = "ingestion:github:hour"
        try:
            hour_str = redis_client.get(hour_key)
            hour = int(hour_str) if hour_str else 0
        except Exception as exc:
            logger.warning(
                "Failed to retrieve GitHub hour from Redis, defaulting to 0",
                exc_info=True
            )
            hour = 0

        # Construct GH Archive URL for 2024-01-01
        url = f"https://data.gharchive.org/2024-01-01-{hour:02d}.json.gz"
        logger.info(
            "Downloading GitHub Archive events",
            extra={"url": url, "hour": hour}
        )

        records = []
        headers = {"User-Agent": "Qolyx/1.0"}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, timeout=30.0)
                response.raise_for_status()

                # Decompress and parse gzipped line-delimited JSON
                compressed_file = io.BytesIO(response.content)
                with gzip.GzipFile(fileobj=compressed_file, mode="rb") as gz_file:
                    text_wrapper = io.TextIOWrapper(gz_file, encoding="utf-8")
                    count = 0
                    for line in text_wrapper:
                        if not line.strip():
                            continue
                        event_dict = json.loads(line)

                        created_at_str = event_dict.get("created_at")
                        created_at = None
                        if created_at_str:
                            created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))

                        records.append({
                            "event_id": event_dict.get("id"),
                            "event_type": event_dict.get("type"),
                            "actor_login": event_dict.get("actor", {}).get("login"),
                            "repo_name": event_dict.get("repo", {}).get("name"),
                            "payload_action": event_dict.get("payload", {}).get("action"),
                            "created_at": created_at,
                            "raw_payload": event_dict
                        })

                        count += 1
                        if count >= 50:
                            break

                # Increment hour counter on success
                next_hour = (hour + 1) % 24
                redis_client.set(hour_key, str(next_hour))
                logger.info(
                    "Successfully fetched and parsed GitHub Archive events",
                    extra={"fetched_count": len(records), "next_hour": next_hour}
                )

            except Exception as exc:
                logger.error(
                    "Failed to fetch or parse GitHub Archive data",
                    exc_info=True,
                    extra={"url": url}
                )
                raise QolyxException(f"GitHub Archive fetch failure: {str(exc)}") from exc

        return records

    @classmethod
    def save_bronze_records(cls, db: Session, source: str, records: List[Dict[str, Any]], pipeline_run_id: uuid.UUID) -> None:
        """Saves real fetched records to the correct Bronze staging database table.

        Args:
            db: Database session.
            source: Source system name ("finnhub", "fda", "github").
            records: List of parsed record dictionaries.
            pipeline_run_id: UUID identifying the current pipeline run.
        """
        logger.info(
            "Persisting ingested records to Bronze staging table",
            extra={"source": source, "records_count": len(records), "pipeline_run_id": str(pipeline_run_id)}
        )

        try:
            if source == "finnhub":
                for rec in records:
                    db_rec = BronzeFinancialCandle(
                        pipeline_run_id=pipeline_run_id,
                        symbol=rec["symbol"],
                        open_price=rec["open_price"],
                        high_price=rec["high_price"],
                        low_price=rec["low_price"],
                        close_price=rec["close_price"],
                        volume=rec["volume"],
                        candle_timestamp=rec["candle_timestamp"]
                    )
                    db.add(db_rec)
            elif source == "fda":
                for rec in records:
                    db_rec = BronzeFdaEvent(
                        pipeline_run_id=pipeline_run_id,
                        receipt_date=rec["receipt_date"],
                        serious=rec["serious"],
                        reporter_country=rec["reporter_country"],
                        drug_name=rec["drug_name"],
                        reaction_description=rec["reaction_description"],
                        seriousness_hospitalization=rec["seriousness_hospitalization"],
                        raw_payload=rec["raw_payload"]
                    )
                    db.add(db_rec)
            elif source == "github":
                for rec in records:
                    db_rec = BronzeGithubEvent(
                        pipeline_run_id=pipeline_run_id,
                        event_id=rec["event_id"],
                        event_type=rec["event_type"],
                        actor_login=rec["actor_login"],
                        repo_name=rec["repo_name"],
                        payload_action=rec["payload_action"],
                        created_at=rec["created_at"],
                        raw_payload=rec["raw_payload"]
                    )
                    db.add(db_rec)
            else:
                raise ValueError(f"Unknown data source: {source}")

            db.commit()
            logger.info("Successfully persisted records in Bronze layer", extra={"source": source, "records_count": len(records)})
        except Exception as exc:
            db.rollback()
            logger.error("Failed to save records to Bronze staging table", exc_info=True, extra={"source": source})
            raise QolyxException(f"Database error writing to Bronze table for {source}: {str(exc)}") from exc

    @classmethod
    async def run_ingestion(cls, db: Session, source_name: str) -> uuid.UUID:
        """Orchestrates the ingestion pipeline execution for the specified source.

        Args:
            db: Database session.
            source_name: Name of the data source ("finnhub", "fda", "github").

        Returns:
            The generated pipeline_run_id.
        """
        if source_name not in DATASET_IDS:
            raise QolyxException(f"Invalid ingestion source name: {source_name}")

        pipeline_run_id = uuid.uuid4()
        dataset_id = DATASET_IDS[source_name]

        # Emit pipeline.started event to Redis event bus
        logger.info(
            "Emitting pipeline.started event",
            extra={"source_name": source_name, "pipeline_run_id": str(pipeline_run_id), "dataset_id": dataset_id}
        )
        try:
            events.publish(
                "pipeline.started",
                {
                    "pipeline_run_id": str(pipeline_run_id),
                    "dataset_id": dataset_id,
                    "started_at": datetime.now(timezone.utc).isoformat()
                }
            )
        except Exception as exc:
            # We log but continue, or we can raise depending on requirements.
            # Following standard robust practices, we log a warning but allow pipeline execution.
            logger.warning(
                "Could not publish pipeline.started event to Redis bus, continuing ingestion execution",
                exc_info=True,
                extra={"pipeline_run_id": str(pipeline_run_id)}
            )

        # Fetch real data based on source
        if source_name == "finnhub":
            records = await cls.fetch_finnhub_data()
        elif source_name == "fda":
            records = await cls.fetch_fda_data()
        elif source_name == "github":
            records = await cls.fetch_github_data()

        # Save records to the corresponding Bronze table
        cls.save_bronze_records(db, source_name, records, pipeline_run_id)

        return pipeline_run_id


def run_ingestion_sync(db: Session, source_name: str) -> uuid.UUID:
    """Synchronous wrapper for run_ingestion() to be called
    from Airflow PythonOperator tasks which run in sync context.
    
    Args:
        db: Database session.
        source_name: Name of the data source.
    
    Returns:
        The generated pipeline_run_id.
    """
    return asyncio.run(IngestionService.run_ingestion(db, source_name))

