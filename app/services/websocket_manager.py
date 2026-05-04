"""WebSocket connection manager for real-time notifications."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
from uuid import UUID, uuid4

import redis.asyncio as redis
from redis.exceptions import RedisError
from starlette.websockets import WebSocket, WebSocketState

from app.config import settings

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Tracks active WebSocket connections per person."""

    def __init__(
        self,
        *,
        redis_url: str | None = None,
        redis_channel: str | None = None,
        redis_enabled: bool | None = None,
    ) -> None:
        self._connections: dict[str, set[WebSocket]] = {}
        self._redis_url = redis_url or getattr(settings, "redis_url", "")
        self._redis_channel = redis_channel or os.getenv(
            "WEBSOCKET_REDIS_CHANNEL", "starter:websocket"
        )
        self._redis_enabled = (
            redis_enabled
            if redis_enabled is not None
            else os.getenv("WEBSOCKET_REDIS_ENABLED", "true").lower()
            in {"1", "true", "yes", "on"}
        )
        self._node_id = uuid4().hex
        self._redis: redis.Redis | None = None
        self._subscriber_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Start Redis pub/sub listener for cross-worker fan-out."""
        if (
            not self._redis_enabled
            or not self._redis_url
            or self._subscriber_task is not None
        ):
            return
        self._subscriber_task = asyncio.create_task(self._listen(), name="ws-redis")

    async def stop(self) -> None:
        """Stop Redis pub/sub listener and close Redis connection."""
        if self._subscriber_task:
            self._subscriber_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._subscriber_task
            self._subscriber_task = None
        if self._redis:
            await self._redis.aclose()
            self._redis = None

    def _get_redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.Redis.from_url(
                self._redis_url,
                decode_responses=True,
                socket_connect_timeout=1,
                socket_timeout=1,
            )
        return self._redis

    async def _listen(self) -> None:
        while True:
            try:
                client = self._get_redis()
                pubsub = client.pubsub()
                await pubsub.subscribe(self._redis_channel)
                async for message in pubsub.listen():
                    if message.get("type") != "message":
                        continue
                    await self._handle_redis_message(str(message.get("data") or ""))
            except asyncio.CancelledError:
                raise
            except RedisError:
                logger.exception("WebSocket Redis subscriber failed")
                await asyncio.sleep(5)
            except Exception:
                logger.exception("WebSocket Redis message handling failed")
                await asyncio.sleep(5)

    async def _handle_redis_message(self, raw: str) -> None:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Ignoring malformed WebSocket Redis payload")
            return
        data = payload.get("data")
        if not isinstance(data, dict):
            return
        if payload.get("sender") == self._node_id:
            return
        person_id = payload.get("person_id")
        if person_id:
            await self._send_to_local(UUID(str(person_id)), data)
            return
        await self._broadcast_local(data)

    async def _publish(self, payload: dict) -> bool:
        if not self._redis_enabled or not self._redis_url:
            return False
        try:
            await self.start()
            await self._get_redis().publish(
                self._redis_channel, json.dumps({**payload, "sender": self._node_id})
            )
            return True
        except RedisError:
            logger.exception("WebSocket Redis publish failed")
            return False

    async def connect(
        self, person_id: UUID, websocket: WebSocket, subprotocol: str | None = None
    ) -> None:
        """Accept and register a WebSocket connection."""
        if subprotocol:
            await websocket.accept(subprotocol=subprotocol)
        else:
            await websocket.accept()
        key = str(person_id)
        if key not in self._connections:
            self._connections[key] = set()
        self._connections[key].add(websocket)
        logger.debug("WebSocket connected: person=%s", person_id)
        await self.start()

    def disconnect(self, person_id: UUID, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        key = str(person_id)
        connections = self._connections.get(key)
        if connections:
            connections.discard(websocket)
            if not connections:
                del self._connections[key]
        logger.debug("WebSocket disconnected: person=%s", person_id)

    async def send_to_person(self, person_id: UUID, data: dict) -> None:
        """Send a JSON message to all connections for a person."""
        await self._publish({"person_id": str(person_id), "data": data})
        await self._send_to_local(person_id, data)

    async def _send_to_local(self, person_id: UUID, data: dict) -> None:
        """Send a JSON message to local connections for a person."""
        key = str(person_id)
        connections = self._connections.get(key, set())
        dead: list[WebSocket] = []
        for ws in connections:
            try:
                if ws.client_state == WebSocketState.CONNECTED:
                    await ws.send_text(json.dumps(data))
            except Exception:
                dead.append(ws)
        for ws in dead:
            connections.discard(ws)
        if key in self._connections and not self._connections[key]:
            del self._connections[key]

    async def broadcast(self, data: dict) -> None:
        """Send a JSON message to all connected clients."""
        await self._publish({"person_id": None, "data": data})
        await self._broadcast_local(data)

    async def _broadcast_local(self, data: dict) -> None:
        """Send a JSON message to all local connected clients."""
        for person_id in list(self._connections.keys()):
            await self._send_to_local(UUID(person_id), data)

    def get_connection_count(self, person_id: UUID | None = None) -> int:
        """Get the number of active connections."""
        if person_id is not None:
            return len(self._connections.get(str(person_id), set()))
        return sum(len(conns) for conns in self._connections.values())


# Singleton instance
ws_manager = ConnectionManager()
