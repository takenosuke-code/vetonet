"""
VetoNet LangChain Integration - Tool Registry & Signature Mapping

Maps tool parameters to VetoNet's AgentPayload fields.
Validates at decoration time for early error detection.
"""

import re
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

from .exceptions import SignatureError, MappingError

# Valid AgentPayload fields
AGENT_PAYLOAD_FIELDS: Set[str] = {
    'item_description',
    'item_category',
    'unit_price',
    'quantity',
    'vendor',
    'currency',
    'is_recurring',
    'fees',
    'metadata',
}

# Common parameter name -> AgentPayload field mappings
AUTO_FIELD_MAP: Dict[str, str] = {
    # Price variations
    'price': 'unit_price',
    'cost': 'unit_price',
    'amount': 'unit_price',
    'total': 'unit_price',
    'unit_price': 'unit_price',

    # Description variations
    'description': 'item_description',
    'desc': 'item_description',
    'item': 'item_description',
    'product': 'item_description',
    'name': 'item_description',
    'item_description': 'item_description',

    # Vendor variations
    'vendor': 'vendor',
    'seller': 'vendor',
    'merchant': 'vendor',
    'store': 'vendor',
    'shop': 'vendor',
    'retailer': 'vendor',

    # Category variations
    'category': 'item_category',
    'type': 'item_category',
    'item_category': 'item_category',

    # Quantity
    'quantity': 'quantity',
    'qty': 'quantity',
    'count': 'quantity',

    # Currency
    'currency': 'currency',
}


def coerce_to_float(value: Any) -> float:
    """Coerce value to float, handling currency strings.

    Examples:
        "$50.00" -> 50.0
        "1,234.56" -> 1234.56
        100 -> 100.0
    """
    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        # Remove currency symbols and commas
        cleaned = re.sub(r'[$,\s]', '', value.strip())
        try:
            return float(cleaned)
        except ValueError:
            raise MappingError(f"Cannot convert '{value}' to float")

    raise MappingError(f"Cannot convert {type(value).__name__} to float")


def coerce_to_int(value: Any) -> int:
    """Coerce value to int."""
    if isinstance(value, int):
        return value

    if isinstance(value, float):
        return int(value)

    if isinstance(value, str):
        try:
            return int(float(value))
        except ValueError:
            raise MappingError(f"Cannot convert '{value}' to int")

    raise MappingError(f"Cannot convert {type(value).__name__} to int")


def coerce_to_bool(value: Any) -> bool:
    """Coerce value to bool."""
    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        return bool(value)

    if isinstance(value, str):
        lower = value.lower().strip()
        if lower in ('true', '1', 'yes', 'on'):
            return True
        if lower in ('false', '0', 'no', 'off', ''):
            return False

    return bool(value)


@dataclass
class ToolSignatureConfig:
    """Configuration for mapping tool parameters to AgentPayload.

    Example:
        ToolSignatureConfig(
            field_map={"cost": "unit_price", "seller": "vendor"},
            defaults={"item_category": "gift_card"},
            auto_infer=True
        )
    """
    # Explicit mappings: tool_param -> payload_field
    field_map: Dict[str, str] = field(default_factory=dict)

    # Default values for fields not in tool params
    defaults: Dict[str, Any] = field(default_factory=dict)

    # Auto-infer mappings from common param names
    auto_infer: bool = True

    # Custom mapper function (overrides field_map)
    custom_mapper: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None

    # Fail mode
    fail_open: bool = False


class SignatureMapper:
    """Maps tool arguments to AgentPayload dict.

    Handles:
    - Explicit field mappings
    - Auto-inference from common param names
    - Type coercion ($50 -> 50.0)
    - Default values
    - Custom mapper functions
    """

    def __init__(self, config: ToolSignatureConfig):
        """Initialize mapper with configuration."""
        self._config = config
        self._validate_config()

    def _validate_config(self) -> None:
        """Validate configuration at construction time."""
        # Check that field_map targets are valid
        invalid_targets = set(self._config.field_map.values()) - AGENT_PAYLOAD_FIELDS
        if invalid_targets:
            raise SignatureError(
                f"Invalid field_map targets: {invalid_targets}. "
                f"Valid fields are: {AGENT_PAYLOAD_FIELDS}"
            )

        # Check that defaults are for valid fields
        invalid_defaults = set(self._config.defaults.keys()) - AGENT_PAYLOAD_FIELDS
        if invalid_defaults:
            raise SignatureError(
                f"Invalid defaults for fields: {invalid_defaults}. "
                f"Valid fields are: {AGENT_PAYLOAD_FIELDS}"
            )

    def _build_effective_map(self, tool_params: Set[str]) -> Dict[str, str]:
        """Build effective field map including auto-inference."""
        effective = {}

        # Auto-infer first (so explicit mappings override)
        if self._config.auto_infer:
            for param in tool_params:
                param_lower = param.lower()
                if param_lower in AUTO_FIELD_MAP:
                    effective[param] = AUTO_FIELD_MAP[param_lower]

        # Apply explicit mappings (override auto)
        effective.update(self._config.field_map)

        return effective

    def map(
        self,
        tool_args: Dict[str, Any],
        tool_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Map tool arguments to AgentPayload dict.

        Args:
            tool_args: Arguments passed to the tool
            tool_name: Tool name for error messages

        Returns:
            Dict matching AgentPayload schema

        Raises:
            MappingError: If required fields can't be extracted
        """
        # Use custom mapper if provided
        if self._config.custom_mapper:
            result = self._config.custom_mapper(tool_args)
            return self._apply_defaults(result)

        # Build effective field map
        field_map = self._build_effective_map(set(tool_args.keys()))

        # Start with defaults
        payload = dict(self._config.defaults)

        # Apply mapped values
        for param, value in tool_args.items():
            if param in field_map:
                target_field = field_map[param]
                payload[target_field] = self._coerce_value(target_field, value, param)

        # Ensure required fields
        payload = self._apply_defaults(payload)
        self._validate_payload(payload, tool_name)

        return payload

    def _coerce_value(self, field: str, value: Any, source: str) -> Any:
        """Coerce value to correct type for field."""
        try:
            if field == 'unit_price':
                return coerce_to_float(value)
            if field == 'quantity':
                return coerce_to_int(value)
            if field == 'is_recurring':
                return coerce_to_bool(value)
            if field == 'fees':
                return self._coerce_fees(value)
            return value
        except MappingError as e:
            raise MappingError(
                f"Cannot coerce '{source}' value '{value}' to {field}: {e}",
                source_field=source,
                target_field=field,
                value=value
            )

    def _coerce_fees(self, value: Any) -> List[Dict[str, Any]]:
        """Coerce fees to list of {name, amount} dicts."""
        if not value:
            return []

        if isinstance(value, list):
            result = []
            for fee in value:
                if isinstance(fee, dict):
                    result.append({
                        'name': fee.get('name', 'fee'),
                        'amount': coerce_to_float(fee.get('amount', 0))
                    })
            return result

        return []

    def _apply_defaults(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Apply default values for missing fields."""
        defaults = {
            'item_description': str(payload.get('item_description', 'Unknown item')),
            'item_category': 'general',
            'unit_price': 0.0,
            'quantity': 1,
            'vendor': 'unknown',
            'currency': 'USD',
            'is_recurring': False,
            'fees': [],
            'metadata': {},
        }

        # Merge: payload values take precedence
        for key, default in defaults.items():
            if key not in payload or payload[key] is None:
                payload[key] = default

        return payload

    def _validate_payload(self, payload: Dict[str, Any], tool_name: Optional[str]) -> None:
        """Validate payload has required fields with valid values."""
        # Price should be non-negative (>= 0 to allow free items/trials)
        price = payload.get('unit_price', 0)
        if price < 0:
            raise MappingError(
                f"unit_price cannot be negative, got {price}",
                tool_name=tool_name,
                target_field='unit_price',
                value=price
            )


class ToolRegistry:
    """Registry of tool signature configurations.

    Thread-safe for concurrent access.

    Usage:
        registry = ToolRegistry()
        registry.register("buy_gift_card", ToolSignatureConfig(
            field_map={"amount": "unit_price"},
            defaults={"item_category": "gift_card"}
        ))

        payload = registry.map_to_payload("buy_gift_card", {"amount": 50})
    """

    def __init__(self):
        """Initialize empty registry."""
        self._signatures: Dict[str, SignatureMapper] = {}
        self._lock = threading.RLock()

    def register(
        self,
        tool_name: str,
        config: ToolSignatureConfig
    ) -> None:
        """Register a tool's signature configuration.

        Args:
            tool_name: Name of the tool
            config: Signature configuration

        Raises:
            SignatureError: If config is invalid
        """
        mapper = SignatureMapper(config)  # Validates at creation

        with self._lock:
            self._signatures[tool_name] = mapper

    def get_mapper(self, tool_name: str) -> Optional[SignatureMapper]:
        """Get mapper for a tool."""
        with self._lock:
            return self._signatures.get(tool_name)

    def has_tool(self, tool_name: str) -> bool:
        """Check if tool is registered."""
        with self._lock:
            return tool_name in self._signatures

    def map_to_payload(
        self,
        tool_name: str,
        tool_args: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Map tool arguments to AgentPayload dict.

        Args:
            tool_name: Name of the tool
            tool_args: Arguments passed to the tool

        Returns:
            Dict matching AgentPayload schema

        Raises:
            SignatureError: If tool not registered
            MappingError: If mapping fails
        """
        mapper = self.get_mapper(tool_name)

        if mapper is None:
            # Not registered - try default mapping
            default_mapper = SignatureMapper(ToolSignatureConfig())
            return default_mapper.map(tool_args, tool_name)

        return mapper.map(tool_args, tool_name)

    def unregister(self, tool_name: str) -> bool:
        """Remove a tool from the registry.

        Returns:
            True if tool was registered, False otherwise
        """
        with self._lock:
            if tool_name in self._signatures:
                del self._signatures[tool_name]
                return True
            return False

    def list_tools(self) -> List[str]:
        """List all registered tool names."""
        with self._lock:
            return list(self._signatures.keys())

    def clear(self) -> None:
        """Remove all registered tools."""
        with self._lock:
            self._signatures.clear()


# Global registry instance
_default_registry: Optional[ToolRegistry] = None


def get_registry() -> ToolRegistry:
    """Get or create the default ToolRegistry instance."""
    global _default_registry
    if _default_registry is None:
        _default_registry = ToolRegistry()
    return _default_registry


__all__ = [
    # Config
    "ToolSignatureConfig",
    "AGENT_PAYLOAD_FIELDS",
    "AUTO_FIELD_MAP",

    # Mapper
    "SignatureMapper",

    # Registry
    "ToolRegistry",
    "get_registry",

    # Coercion
    "coerce_to_float",
    "coerce_to_int",
    "coerce_to_bool",
]
