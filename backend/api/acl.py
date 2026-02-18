from typing import List, Dict, Optional
import logging
from enum import Enum

logger = logging.getLogger("QLM.Security.ACL")

class Permission(Enum):
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"

class Role(Enum):
    VIEWER = [Permission.READ]
    RESEARCHER = [Permission.READ, Permission.EXECUTE]
    DEVELOPER = [Permission.READ, Permission.WRITE, Permission.EXECUTE]
    ADMIN = [Permission.READ, Permission.WRITE, Permission.EXECUTE, Permission.ADMIN]

class AccessControl:
    """
    Manages Role-Based Access Control (RBAC) for MCP tools.
    """
    def __init__(self):
        # Map tools to required permissions
        self.tool_permissions: Dict[str, Permission] = {
            "list_datasets": Permission.READ,
            "list_strategies": Permission.READ,
            "get_strategy_code": Permission.READ,
            "get_market_data": Permission.READ,
            "read_file": Permission.READ,
            "get_tools_manifest": Permission.READ,
            "get_system_status": Permission.READ,
            "analyze_market_structure": Permission.READ, # Technically compute, but read-only side effects

            "run_backtest": Permission.EXECUTE,
            "validate_strategy": Permission.EXECUTE,
            "optimize_parameters": Permission.EXECUTE,

            "create_strategy": Permission.WRITE,
            "write_file": Permission.WRITE,
            "import_dataset_from_url": Permission.WRITE,
            "delete_entity": Permission.ADMIN, # Dangerous
            "update_ai_config": Permission.ADMIN
        }

    def check_access(self, role: Role, tool_name: str) -> bool:
        required_perm = self.tool_permissions.get(tool_name, Permission.ADMIN) # Default to Admin for unknown tools

        user_perms = role.value

        # Admin overrides all
        if Permission.ADMIN in user_perms:
            return True

        return required_perm in user_perms

# Singleton
acl = AccessControl()
