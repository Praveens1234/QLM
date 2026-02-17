from pydantic import BaseModel, Field, SecretStr
from typing import List, Optional, Dict, Literal
from datetime import datetime

class Model(BaseModel):
    id: str
    name: str
    context_window: int = 4096
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0

class ProviderConfig(BaseModel):
    id: str
    name: str
    # Relaxed type hint to allow custom/mock providers during runtime
    type: str = "openai"
    base_url: str
    api_key: Optional[str] = None
    is_active: bool = False
    models: List[Model] = []

class AIConfig(BaseModel):
    active_provider_id: Optional[str] = None
    active_model_id: Optional[str] = None
    system_prompt: str = "You are a helpful AI assistant."
    temperature: float = 0.7
    max_tokens: int = 2000
    providers: List[ProviderConfig] = []
