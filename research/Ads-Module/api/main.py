"""
FastAPI Application Entrypoint for GrowthOS Ads Module
Strictly NO emojis in code, docstrings, or logs.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

from config import get_config, AdsModuleConfig
from storage.ads_storage import SqlAdsStorageAdapter
from connectors.google_ads_connector import GoogleAdsConnector
from normalization.normalizer import AdsNormalizer
from events.publisher import EventPublisher
from services.sync_service import AdsSyncService
from engines.planning_engine import CampaignPlanningEngine
from engines.validation_engine import CampaignValidationEngine
from services.deployment_service import CampaignDeploymentService
from attribution.click_tracker import ClickTracker
from attribution.conversion_matcher import ConversionMatcher
from connectors.offline_conversion_uploader import OfflineConversionUploader
from api.routes import router, AdsModuleContainer, set_container


from connectors.base import AdsConnectorBase


def create_app(
    config: Optional[AdsModuleConfig] = None,
    storage: Optional[SqlAdsStorageAdapter] = None,
    connector: Optional[AdsConnectorBase] = None
) -> FastAPI:
    cfg = config or get_config()
    db_storage = storage or SqlAdsStorageAdapter(cfg.db_url.replace("sqlite:///", ""))
    ads_connector = connector or GoogleAdsConnector(cfg)
    normalizer = AdsNormalizer(default_currency=cfg.currency, default_timezone=cfg.timezone)
    publisher = EventPublisher(webhook_url=cfg.ai_module_webhook_url)

    sync_service = AdsSyncService(
        connector=ads_connector,
        normalizer=normalizer,
        storage=db_storage,
        publisher=publisher
    )

    planning_engine = CampaignPlanningEngine()
    validation_engine = CampaignValidationEngine()
    deployment_service = CampaignDeploymentService(
        storage=db_storage,
        connector=ads_connector,
        validation_engine=validation_engine,
        publisher=publisher
    )

    click_tracker = ClickTracker(storage=db_storage)
    conversion_matcher = ConversionMatcher(storage=db_storage, publisher=publisher)
    conversion_uploader = OfflineConversionUploader(
        storage=db_storage,
        connector=ads_connector if isinstance(ads_connector, GoogleAdsConnector) else None
    )

    container = AdsModuleContainer()
    container.storage = db_storage
    container.connector = ads_connector
    container.sync_service = sync_service
    container.planning_engine = planning_engine
    container.validation_engine = validation_engine
    container.deployment_service = deployment_service
    container.click_tracker = click_tracker
    container.conversion_matcher = conversion_matcher
    container.conversion_uploader = conversion_uploader
    set_container(container)

    app = FastAPI(
        title="GrowthOS Ads Layer Manager",
        description="Google Ads Connector, Normalization Engine, and Metrics REST API",
        version="1.0.0"
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    cfg = get_config()
    uvicorn.run("api.main:app", host="0.0.0.0", port=cfg.port, reload=True)
