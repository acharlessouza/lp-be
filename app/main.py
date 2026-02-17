from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routers.allocate import router as allocate_router
from .api.routers.catalog import router as catalog_router
from .api.routers.discover_pools import router as discover_pools_router
from .api.routers.estimated_fees import router as estimated_fees_router
from .api.routers.liquidity_distribution import router as liquidity_distribution_router
from .api.routers.match_ticks import router as match_ticks_router
from .api.routers.pool_price import router as pool_price_router
from .api.routers.pool_volume_history import router as pool_volume_history_router
from .api.routers.simulate_apr import router as simulate_apr_router

app = FastAPI(title="LP API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(allocate_router)
app.include_router(catalog_router)
app.include_router(pool_price_router)
app.include_router(pool_volume_history_router)
app.include_router(liquidity_distribution_router)
app.include_router(match_ticks_router)
app.include_router(estimated_fees_router)
app.include_router(discover_pools_router)
app.include_router(simulate_apr_router)
