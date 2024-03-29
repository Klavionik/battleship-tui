from typing import Any

from loguru import logger

from battleship.server.bus import MessageBus
from battleship.shared.events import Entity, EntityEvent, Message
from battleship.shared.models import Action


class Observable:
    entity: Entity

    def __init__(self, message_bus: MessageBus) -> None:
        self._bus = message_bus

    async def notify(
        self, entity_id: str, action: Action, payload: dict[str, Any] | None = None
    ) -> None:
        payload = payload or {}

        logger.debug(
            "{repo} notifies about {action}, entity {entity}:{entity_id}",
            repo=self.__class__.__name__,
            action=action,
            entity=self.entity,
            entity_id=entity_id,
        )

        await self._bus.emit(
            f"entities.{self.entity}",
            Message(
                event=EntityEvent(
                    action=action, entity=self.entity, payload=payload, entity_id=entity_id
                )
            ),
        )
