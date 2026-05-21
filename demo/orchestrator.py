import argparse
import logging
import sys
from sqlalchemy.orm import Session
from backend.core.database import SessionLocal
from backend.core.logging import setup_logging

# Import all scenarios
from demo.scenarios import (
    scenario_01_surge_pricing,
    scenario_02_api_breaking_change,
    scenario_03_silent_null,
    scenario_04_freshness_delay,
    scenario_05_duplicate_fraud,
    scenario_06_timezone_apocalypse,
)

# Initialize logging namespace
logger = logging.getLogger("qolyx.demo.orchestrator")

# Metadata mapping for scenarios
SCENARIOS = {
    1: {
        "name": "surge_pricing",
        "module": scenario_01_surge_pricing,
        "title": "Scenario 01: Surge Pricing (Volume Spike)",
        "table": "bronze_financial_candles"
    },
    2: {
        "name": "api_breaking_change",
        "module": scenario_02_api_breaking_change,
        "title": "Scenario 02: API Breaking Change",
        "table": "bronze_financial_candles"
    },
    3: {
        "name": "silent_null",
        "module": scenario_03_silent_null,
        "title": "Scenario 03: Silent Null Corruption",
        "table": "bronze_fda_events"
    },
    4: {
        "name": "freshness_delay",
        "module": scenario_04_freshness_delay,
        "title": "Scenario 04: Freshness Delay (Finance Close)",
        "table": "all_pipelines (Redis last_run)"
    },
    5: {
        "name": "duplicate_fraud",
        "module": scenario_05_duplicate_fraud,
        "title": "Scenario 05: Duplicate Fraud (Retry Bug)",
        "table": "bronze_financial_candles"
    },
    6: {
        "name": "timezone_apocalypse",
        "module": scenario_06_timezone_apocalypse,
        "title": "Scenario 06: Timezone Apocalypse",
        "table": "bronze_github_events"
    }
}

def list_scenarios() -> None:
    """Prints a beautifully formatted ASCII table of the scenarios."""
    print("=" * 120)
    print(f"{'#':<3} | {'SCENARIO NAME':<20} | {'AFFECTED TARGET':<25} | {'DESCRIPTION':<60}")
    print("=" * 120)
    
    for num, meta in SCENARIOS.items():
        module = meta["module"]
        # Call inject with a dummy or dry run? No, we can get information from a dry-run style or mock run
        # Wait, since inject returns the config, let's extract the description directly
        # Let's inspect the docstring or construct a mock session or simply write down description from meta
        # Actually, let's create a temporary mock/dummy Session to retrieve the metadata return dict
        # without committing any changes.
        # But wait! We can just define the description and penalties statically or extract them safely.
        # Let's dynamically call the inject function with a dummy session that raises immediately or does nothing.
        # A safer way: since we know the details, we can list them dynamically by calling inject(None)
        # But inject(None) might fail when querying db. Instead, let's just write the metadata statically
        # in the orchestrator or extract it.
        # Let's check: can we run inject with a dummy session?
        # Actually, we can just run the scenario descriptions directly from the module docstring and definition.
        # Let's write them statically here to ensure robust display even without DB connections!
        pass

    # Static metadata table for clean printing without executing DB queries
    meta_details = [
        (
            "1", 
            "surge_pricing", 
            "bronze_financial_candles", 
            "Simulates Uber-style volume spike: AAPL candle records multiplied 10x simulating market data feed duplication."
        ),
        (
            "2", 
            "api_breaking_change", 
            "bronze_financial_candles", 
            "Simulates Salesforce API breaking change: close_price column is COMPLETELY MISSING from ingested payload."
        ),
        (
            "3", 
            "silent_null", 
            "bronze_fda_events", 
            "Simulates silent null corruption: 40% of FDA serious field set to NULL after backend engineer made field optional."
        ),
        (
            "4", 
            "freshness_delay", 
            "all_pipelines (Redis)", 
            "Simulates finance close delay: pipeline intentionally skipped to trigger freshness SLA violation (6+ hours)."
        ),
        (
            "5", 
            "duplicate_fraud", 
            "bronze_financial_candles", 
            "Simulates payment processor retry bug: all financial candle records duplicated exactly. Row count doubled."
        ),
        (
            "6", 
            "timezone_apocalypse", 
            "bronze_github_events", 
            "Simulates timezone deployment bug: all GitHub event timestamps shifted +5:30 hours (India timezone)."
        ),
    ]
    
    for num, name, target, desc in meta_details:
        # Wrap description to fit nicely
        desc_lines = [desc[i:i+60] for i in range(0, len(desc), 60)]
        print(f"{num:<3} | {name:<20} | {target:<25} | {desc_lines[0]:<60}")
        for extra_line in desc_lines[1:]:
            print(f"{'':<3} | {'':<20} | {'':<25} | {extra_line:<60}")
        print("-" * 120)


def execute_scenario(num: int, db: Session) -> dict:
    """Executes a single scenario by its number and prints the output."""
    meta = SCENARIOS[num]
    logger.info(f"Starting execution of {meta['title']}")
    
    # Run the injector function
    result = meta["module"].inject(db)
    
    print("\n" + "=" * 80)
    print(f" SCENARIO RUN RESULT: {meta['title']}")
    print("=" * 80)
    print(f"Scenario Key : {result.get('scenario')}")
    print(f"Target Table : {result.get('affected_table')}")
    print(f"Description  : {result.get('description')}")
    print("-" * 80)
    print("Expected Trust Score Penalties:")
    penalties = result.get("expected_trust_score_impact", {})
    for key, value in penalties.items():
        print(f"  - {key:<20}: {value}")
    print("=" * 80 + "\n")
    
    return result


def main() -> None:
    """CLI orchestrator entrypoint."""
    # Ensure standard structured logging is set up
    setup_logging()
    
    parser = argparse.ArgumentParser(
        description="Qolyx Production Failure Scenario Ingestor & Orchestrator"
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "-l", "--list", 
        action="store_true", 
        help="List all available production failure scenarios."
    )
    group.add_argument(
        "-s", "--scenario", 
        type=str, 
        help="Run a specific scenario by number (1-6) or name."
    )
    group.add_argument(
        "-a", "--all", 
        action="store_true", 
        help="Run all scenarios sequentially."
    )
    
    args = parser.parse_args()
    
    if args.list:
        list_scenarios()
        sys.exit(0)
        
    db = SessionLocal()
    try:
        if args.scenario:
            # Resolve scenario number or name
            scenario_num = None
            val = args.scenario.strip().lower()
            
            if val.isdigit():
                num = int(val)
                if num in SCENARIOS:
                    scenario_num = num
            else:
                for k, v in SCENARIOS.items():
                    if v["name"] == val:
                        scenario_num = k
                        break
                        
            if not scenario_num:
                logger.error(f"Invalid scenario identifier: '{args.scenario}'. Use -l to list available options.")
                sys.exit(1)
                
            execute_scenario(scenario_num, db)
            
        elif args.all:
            logger.info("Running all 6 production failure scenarios in sequence...")
            results = []
            for num in sorted(SCENARIOS.keys()):
                res = execute_scenario(num, db)
                results.append(res)
            logger.info(f"Successfully executed all {len(results)} scenarios.")
            
    except Exception as exc:
        logger.critical("Orchestrator encountered an unhandled exception", exc_info=True)
        sys.exit(1)
    finally:
        db.close()
        logger.info("Database session closed.")

if __name__ == "__main__":
    main()
