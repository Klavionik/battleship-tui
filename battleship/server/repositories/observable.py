from typing import Any

from loguru import logger

from battleship.server.repositories import EntityChannel
from battleship.shared.events import Entity, EntityEvent, Message
from battleship.shared.models import Action


class Observable:
    entity: Entity

    def __init__(self, entity_channel: EntityChannel) -> None:
        self._entity_channel = entity_channel.topic(self.entity)

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

        await self._entity_channel.publish(
            Message(
                event=EntityEvent(
                    action=action, entity=self.entity, payload=payload, entity_id=entity_id
                )
            )
        )
