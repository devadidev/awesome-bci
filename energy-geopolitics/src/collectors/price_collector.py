"""Oil price data collector with simulated + real API support."""
import random
from datetime import datetime
from typing import Any, List, Optional
import httpx
from src.collectors.base import BaseCollector
from src.data.db import get_store
from src.models.intelligence import OilPriceSnapshot
from src.recovery import RecoveryManager
from src.logger import get_logger

logger = get_logger(__name__)

# Simulated realistic Brent crude price baseline
_BRENT_BASE = 85.0
_WTI_SPREAD = 3.2   # WTI typically trades ~$3 below Brent
_GAS_BASE = 3.1


class PriceCollector(BaseCollector):
    """
    Collects oil and gas price data.

    In production: calls EIA API or Alpha Vantage.
    In development / when no API key: generates realistic simulated prices.
    """

    def __init__(
        self,
        recovery_manager: RecoveryManager,
        eia_api_key: str = "",
        interval_seconds: int = 60,
    ):
        super().__init__("price_collector", recovery_manager, interval_seconds)
        self._api_key = eia_api_key
        self._simulated = not bool(eia_api_key)
        self._last_brent: float = _BRENT_BASE
        self._last_gas: float = _GAS_BASE

    async def _fetch(self) -> List[dict]:
        if self._simulated:
            return self._simulate_prices()
        return await self._fetch_eia()

    def _simulate_prices(self) -> List[dict]:
        """Generate realistic-looking price movement."""
        # Random walk with mean reversion
        shock = random.gauss(0, 0.5)
        mean_rev = 0.05 * (_BRENT_BASE - self._last_brent)
        self._last_brent = round(self._last_brent + shock + mean_rev, 2)
        self._last_brent = max(40.0, min(130.0, self._last_brent))

        gas_shock = random.gauss(0, 0.05)
        self._last_gas = round(self._last_gas + gas_shock, 2)
        self._last_gas = max(1.5, min(10.0, self._last_gas))

        return [{
            "brent_crude_usd": self._last_brent,
            "wti_crude_usd": round(self._last_brent - _WTI_SPREAD + random.gauss(0, 0.2), 2),
            "natural_gas_usd": self._last_gas,
            "source": "simulated",
        }]

    async def _fetch_eia(self) -> List[dict]:
        """Fetch from US EIA API (real integration)."""
        url = "https://api.eia.gov/v2/petroleum/pri/spt/data/"
        params = {
            "api_key": self._api_key,
            "frequency": "daily",
            "data[0]": "value",
            "facets[product][]": ["EPCBRENT", "EPCWTI"],
            "sort[0][column]": "period",
            "sort[0][direction]": "desc",
            "length": 1,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", {}).get("data", [])

    async def _process(self, raw_items: List[Any]) -> int:
        store = get_store()
        existing = store.latest_price()
        count = 0
        for item in raw_items:
            snapshot = OilPriceSnapshot(
                timestamp=datetime.utcnow(),
                brent_crude_usd=item.get("brent_crude_usd"),
                wti_crude_usd=item.get("wti_crude_usd"),
                natural_gas_usd=item.get("natural_gas_usd"),
                change_24h_pct=self._calc_change(
                    item.get("brent_crude_usd"), existing
                ),
                source=item.get("source", "eia"),
            )
            store.append_price(snapshot.model_dump())
            count += 1
        return count

    def _calc_change(self, current: Optional[float], prev_snapshot: Optional[dict]) -> Optional[float]:
        if current is None or prev_snapshot is None:
            return None
        prev = prev_snapshot.get("brent_crude_usd")
        if prev and prev != 0:
            return round(((current - prev) / prev) * 100, 3)
        return None
