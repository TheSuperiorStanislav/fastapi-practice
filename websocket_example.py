import enum
import secrets
import string

import arrow
import pydantic
from starlette.websockets import WebSocket


class ClientInfo(pydantic.BaseModel):
    client_name: str
    client_id: str


class Message(pydantic.BaseModel):
    message: str
    created: str
    client_info: ClientInfo


class EventEnum(str, enum.Enum):
    connection_started = "connection_started"
    connection_denied = "connection_denied"
    new_message = "new_message"
    user_connected = "user_connected"
    user_disconnected = "user_disconnected"


class Event(pydantic.BaseModel):
    event_tag: EventEnum


class ConnectionStartedEvent(Event):
    event_tag = EventEnum.connection_started
    client_info: ClientInfo
    messages: list[Message]


class ConnectionDeniedEvent(Event):
    event_tag = EventEnum.connection_denied
    reason: str


class NewMessageEvent(Event):
    event_tag = EventEnum.new_message
    message: Message


class UserConnectedEvent(Event):
    event_tag = EventEnum.user_connected
    client_info: ClientInfo


class UserDisconnectedEvent(Event):
    event_tag = EventEnum.user_disconnected
    client_info: ClientInfo


class ChatConnectionManager:
    chats: dict[str, "ChatConnectionManager"] = dict()

    @classmethod
    def get_chat(cls, chat_name: str) -> "ChatConnectionManager":
        if chat_name not in cls.chats:
            cls.chats[chat_name] = ChatConnectionManager()
        return cls.chats[chat_name]

    def __init__(self):
        self._messages: list[Message] = []
        self._client_infos: dict[str, ClientInfo] = dict()
        self._active_connections: dict[str, WebSocket] = dict()

    async def connect(
        self,
        client_name: str,
        websocket: WebSocket,
    ) -> str:
        """Create connection to chat."""
        await websocket.accept()
        client_id = self._generate_client_id()
        self._client_infos[client_id] = ClientInfo(
            client_id=client_id,
            client_name=client_name,
        )
        self._active_connections[client_id] = websocket
        await self.broadcast(
            UserConnectedEvent(client_info=self._client_infos[client_id])
        )
        await self.broadcast_to_client(
            client_id=client_id,
            event=ConnectionStartedEvent(
                client_info=self._client_infos[client_id],
                messages=self._messages,
            ),
        )
        await websocket.send_json(
            ConnectionStartedEvent(
                client_info=self._client_infos[client_id],
                messages=self._messages,
            ).dict()
        )
        return client_id

    def _generate_client_id(self, length=6):
        """Generate a digits-only string of given length."""
        rand = secrets.SystemRandom()
        digits = rand.choices(string.digits, k=length)
        return ''.join(digits)

    async def disconnect(
        self,
        client_id: str,
    ):
        if client_id not in self._active_connections:
            return
        self._active_connections.pop(client_id)
        client_info = self._client_infos.pop(client_id)
        await self.broadcast(UserDisconnectedEvent(client_info=client_info))

    async def process_event(
        self,
        client_id: str,
        event_data: dict,
    ):
        """Process websocket event."""
        event_map = dict(
            new_message=self._on_new_message,
        )
        await event_map[event_data["event_tag"]](client_id, event_data)

    async def _on_new_message(self, client_id: str, event_data: dict):
        """Inform users of new user."""
        message = Message(
            client_info=self._client_infos[client_id],
            message=event_data["message"],
            created=arrow.now().datetime.isoformat(),
        )
        self._messages.append(message)
        await self.broadcast(
            NewMessageEvent(
                message=message,
            )
        )

    async def broadcast_to_client(self, client_id: str, event: Event):
        """Send event to specific client."""
        await self._active_connections[client_id].send_json(event.dict())

    async def broadcast(self, event: Event):
        """Send event to all clients."""
        for client_id, connection in self._active_connections.items():
            await connection.send_json(event.dict())
