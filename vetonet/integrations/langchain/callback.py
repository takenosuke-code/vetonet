"""
VetoNet LangChain Integration - Callback Handlers

LangChain callback handlers that capture conversation flow.
Uses IntentStore for thread-safe storage (never mutates shared state).
"""

import logging
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from .intent import IntentStore, get_intent_store

logger = logging.getLogger("vetonet.langchain")

# Try to import LangChain callback base classes
try:
    from langchain_core.callbacks import BaseCallbackHandler, AsyncCallbackHandler
    from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
    from langchain_core.outputs import LLMResult
    LANGCHAIN_AVAILABLE = True
except ImportError:
    # LangChain not installed - create stub classes
    LANGCHAIN_AVAILABLE = False

    class BaseCallbackHandler:
        """Stub for when LangChain is not installed."""
        pass

    class AsyncCallbackHandler:
        """Stub for when LangChain is not installed."""
        pass

    class BaseMessage:
        content: str = ""

    class HumanMessage(BaseMessage):
        pass

    class AIMessage(BaseMessage):
        pass

    class LLMResult:
        generations: list = []


def _extract_content(message: Any) -> Optional[str]:
    """Extract text content from various message types."""
    if isinstance(message, str):
        return message

    if hasattr(message, 'content'):
        content = message.content
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            # Handle multi-part content (text + images)
            text_parts = [
                p.get('text', '') if isinstance(p, dict) else str(p)
                for p in content
                if isinstance(p, (str, dict))
            ]
            return ' '.join(text_parts)

    if isinstance(message, dict):
        return message.get('content') or message.get('text')

    return None


def _get_role(message: Any) -> str:
    """Determine the role of a message."""
    if hasattr(message, 'type'):
        msg_type = message.type
        if msg_type == 'human':
            return 'user'
        if msg_type == 'ai':
            return 'assistant'
        if msg_type == 'system':
            return 'system'

    if isinstance(message, dict):
        role = message.get('role', 'user')
        if role == 'human':
            return 'user'
        if role == 'ai':
            return 'assistant'
        return role

    # Default based on class name
    class_name = type(message).__name__.lower()
    if 'human' in class_name or 'user' in class_name:
        return 'user'
    if 'ai' in class_name or 'assistant' in class_name:
        return 'assistant'
    if 'system' in class_name:
        return 'system'

    return 'user'


class VetoNetCallbackHandler(BaseCallbackHandler):
    """LangChain callback handler for capturing conversation flow.

    This handler captures user and assistant messages as the conversation
    progresses, storing them in IntentStore for later retrieval.

    Key design decisions:
    - Never mutates shared state (uses contextvars via IntentStore)
    - Never raises exceptions that would break the chain
    - Minimal performance overhead

    Usage:
        from vetonet.langchain import VetoNetCallbackHandler

        handler = VetoNetCallbackHandler()
        agent = create_agent(..., callbacks=[handler])
    """

    def __init__(self, store: Optional[IntentStore] = None):
        """Initialize callback handler.

        Args:
            store: IntentStore instance. Uses default if not provided.
        """
        super().__init__()
        self._store = store or get_intent_store()

    @property
    def store(self) -> IntentStore:
        """Get the intent store."""
        return self._store

    def on_chain_start(
        self,
        serialized: Dict[str, Any],
        inputs: Dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> None:
        """Capture initial input when chain starts."""
        try:
            # Look for input in common locations
            input_text = None

            if isinstance(inputs, str):
                input_text = inputs
            elif isinstance(inputs, dict):
                # Try common keys
                for key in ['input', 'question', 'query', 'message', 'text']:
                    if key in inputs:
                        val = inputs[key]
                        if isinstance(val, str):
                            input_text = val
                            break
                        content = _extract_content(val)
                        if content:
                            input_text = content
                            break

                # Check for messages list
                messages = inputs.get('messages') or inputs.get('chat_history')
                if messages and isinstance(messages, list) and messages:
                    last_msg = messages[-1]
                    if _get_role(last_msg) == 'user':
                        input_text = _extract_content(last_msg)

            if input_text:
                self._store.capture(input_text, role='user')
                logger.debug(f"Captured chain input: {input_text[:100]}...")

        except Exception as e:
            # Never break the chain
            logger.warning(f"Error capturing chain input: {e}")

    def on_chat_model_start(
        self,
        serialized: Dict[str, Any],
        messages: List[List[Any]],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> None:
        """Capture messages when chat model is invoked."""
        try:
            if not messages:
                return

            # messages is List[List[BaseMessage]] - flatten and capture
            for message_list in messages:
                if not isinstance(message_list, list):
                    message_list = [message_list]

                for msg in message_list:
                    content = _extract_content(msg)
                    role = _get_role(msg)

                    if content and role == 'user':
                        self._store.capture(content, role='user')
                        logger.debug(f"Captured user message: {content[:100]}...")

        except Exception as e:
            logger.warning(f"Error capturing chat model messages: {e}")

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any
    ) -> None:
        """Capture LLM response for conversation history."""
        try:
            if not hasattr(response, 'generations') or not response.generations:
                return

            for gen_list in response.generations:
                if not gen_list:
                    continue

                # Get first generation (usually only one)
                gen = gen_list[0]
                content = None

                if hasattr(gen, 'text'):
                    content = gen.text
                elif hasattr(gen, 'message'):
                    content = _extract_content(gen.message)

                if content:
                    self._store.capture(content, role='assistant')
                    logger.debug(f"Captured assistant response: {content[:100]}...")
                    break  # Only capture first response

        except Exception as e:
            logger.warning(f"Error capturing LLM response: {e}")

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> None:
        """Log when a tool is about to be invoked."""
        tool_name = serialized.get('name', 'unknown')
        logger.debug(f"Tool starting: {tool_name}")


class AsyncVetoNetCallbackHandler(AsyncCallbackHandler):
    """Async version of VetoNetCallbackHandler.

    Use this for async chains where callbacks need to be async.
    Internally delegates to the sync handler since IntentStore
    operations are fast and don't need to be async.
    """

    def __init__(self, store: Optional[IntentStore] = None):
        """Initialize async callback handler."""
        super().__init__()
        self._sync_handler = VetoNetCallbackHandler(store)

    @property
    def store(self) -> IntentStore:
        """Get the intent store."""
        return self._sync_handler.store

    async def on_chain_start(
        self,
        serialized: Dict[str, Any],
        inputs: Dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> None:
        """Async version - delegates to sync handler."""
        self._sync_handler.on_chain_start(
            serialized, inputs,
            run_id=run_id, parent_run_id=parent_run_id,
            tags=tags, metadata=metadata, **kwargs
        )

    async def on_chat_model_start(
        self,
        serialized: Dict[str, Any],
        messages: List[List[Any]],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> None:
        """Async version - delegates to sync handler."""
        self._sync_handler.on_chat_model_start(
            serialized, messages,
            run_id=run_id, parent_run_id=parent_run_id,
            tags=tags, metadata=metadata, **kwargs
        )

    async def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any
    ) -> None:
        """Async version - delegates to sync handler."""
        self._sync_handler.on_llm_end(
            response, run_id=run_id, parent_run_id=parent_run_id, **kwargs
        )

    async def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> None:
        """Async version - delegates to sync handler."""
        self._sync_handler.on_tool_start(
            serialized, input_str,
            run_id=run_id, parent_run_id=parent_run_id,
            tags=tags, metadata=metadata, **kwargs
        )


__all__ = [
    "VetoNetCallbackHandler",
    "AsyncVetoNetCallbackHandler",
    "LANGCHAIN_AVAILABLE",
]
