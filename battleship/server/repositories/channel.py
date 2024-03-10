from battleship.server.pubsub import Broker, Channel
from battleship.shared.events import EntityEvent, Message


class EntityChannel(Channel[Message[EntityEvent]]):
    def __init__(self, broker: Broker):
        super().__init__("entity", broker)
