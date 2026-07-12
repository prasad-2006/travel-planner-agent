"""
Configuration settings for Travel Planner Agent
IBM Cloud Lite / IBM Granite Integration
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask
    SECRET_KEY = os.getenv("SECRET_KEY", "travel-planner-secret-key-2024")
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"

    # IBM watsonx.ai (Granite LLM)
    IBM_WATSONX_API_KEY    = os.getenv("IBM_WATSONX_API_KEY", "")
    IBM_WATSONX_URL        = os.getenv("IBM_WATSONX_URL", "https://eu-de.ml.cloud.ibm.com")
    IBM_WATSONX_PROJECT_ID = os.getenv("IBM_WATSONX_PROJECT_ID", "")

    # IBM Granite Model IDs (available on IBM Cloud Lite)
    GRANITE_CHAT_MODEL     = os.getenv("GRANITE_CHAT_MODEL",     "ibm/granite-3-8b-instruct")
    GRANITE_INSTRUCT_MODEL = os.getenv("GRANITE_INSTRUCT_MODEL", "ibm/granite-3-8b-instruct")

    # IBM Watson Assistant (Lite tier)
    WATSON_ASSISTANT_API_KEY    = os.getenv("WATSON_ASSISTANT_API_KEY", "")
    WATSON_ASSISTANT_URL        = os.getenv("WATSON_ASSISTANT_URL", "")
    WATSON_ASSISTANT_ID         = os.getenv("WATSON_ASSISTANT_ID", "")

    # IBM watsonx Orchestrate
    WATSONX_ORCHESTRATE_API_KEY     = os.getenv("WATSONX_ORCHESTRATE_API_KEY", "")
    WATSONX_ORCHESTRATE_URL         = os.getenv("WATSONX_ORCHESTRATE_URL", "https://api.us-south.assistant.watson.cloud.ibm.com")
    WATSONX_ORCHESTRATE_INSTANCE_ID = os.getenv("WATSONX_ORCHESTRATE_INSTANCE_ID", "")

    # Amadeus Travel API (flights + hotels — free sandbox)
    AMADEUS_API_KEY    = os.getenv("AMADEUS_API_KEY", "")
    AMADEUS_API_SECRET = os.getenv("AMADEUS_API_SECRET", "")
    AMADEUS_SANDBOX    = os.getenv("AMADEUS_SANDBOX", "True").lower() == "true"

    # OpenTripMap (attractions — free, 5000 calls/day)
    OPENTRIPMAP_API_KEY = os.getenv("OPENTRIPMAP_API_KEY", "")

    # External APIs
    OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")   # optional — wttr.in used if blank

    # IBM Cloud Object Storage (optional)
    IBM_COS_API_KEY           = os.getenv("IBM_COS_API_KEY", "")
    IBM_COS_INSTANCE_CRN      = os.getenv("IBM_COS_INSTANCE_CRN", "")
    IBM_COS_ENDPOINT          = os.getenv("IBM_COS_ENDPOINT", "https://s3.us-south.cloud-object-storage.appdomain.cloud")
    IBM_COS_BUCKET            = os.getenv("IBM_COS_BUCKET", "travel-planner-data")

    # LLM Generation Parameters
    LLM_MAX_TOKENS   = int(os.getenv("LLM_MAX_TOKENS", "1500"))
    LLM_TEMPERATURE  = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    LLM_TOP_P        = float(os.getenv("LLM_TOP_P", "0.95"))
    LLM_TOP_K        = int(os.getenv("LLM_TOP_K", "50"))

    # App settings
    MAX_ITINERARY_DAYS  = int(os.getenv("MAX_ITINERARY_DAYS", "30"))
    DEFAULT_CURRENCY    = os.getenv("DEFAULT_CURRENCY", "USD")
    SESSION_LIFETIME    = int(os.getenv("SESSION_LIFETIME", "3600"))  # seconds


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config_map = {
    "development": DevelopmentConfig,
    "production":  ProductionConfig,
    "default":     DevelopmentConfig,
}
