from pydantic import BaseModel, Field, ValidationError
from typing import Optional, Dict, Any, Union, Literal
import logging

logger = logging.getLogger("QLM.MCP.Validation")

# JSON-RPC 2.0 Models
class JsonRpcRequest(BaseModel):
    jsonrpc: Literal["2.0"]
    method: str
    params: Optional[Union[Dict[str, Any], list]] = None
    id: Optional[Union[str, int]] = None

class JsonRpcNotification(BaseModel):
    jsonrpc: Literal["2.0"]
    method: str
    params: Optional[Union[Dict[str, Any], list]] = None

class ValidationMiddleware:
    """
    Validates incoming payloads against JSON-RPC 2.0 spec.
    """

    @staticmethod
    def validate_payload(payload: Dict[str, Any]) -> bool:
        try:
            # Check if it's a notification (no id) or request
            if "id" in payload:
                JsonRpcRequest(**payload)
            else:
                JsonRpcNotification(**payload)
            return True
        except ValidationError as e:
            logger.warning(f"Invalid JSON-RPC payload: {e}")
            return False
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return False
