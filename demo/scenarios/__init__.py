"""Production failure scenario injectors for Qolyx demo."""

from demo.scenarios import scenario_01_surge_pricing
from demo.scenarios import scenario_02_api_breaking_change
from demo.scenarios import scenario_03_silent_null
from demo.scenarios import scenario_04_freshness_delay
from demo.scenarios import scenario_05_duplicate_fraud
from demo.scenarios import scenario_06_timezone_apocalypse

__all__ = [
    "scenario_01_surge_pricing",
    "scenario_02_api_breaking_change",
    "scenario_03_silent_null",
    "scenario_04_freshness_delay",
    "scenario_05_duplicate_fraud",
    "scenario_06_timezone_apocalypse",
]
