from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4


@dataclass
class AgentMessage:
    """
    Standard message format for communication between agents.
    """

    sender: str
    receiver: str
    task: str

    payload: dict[str, Any] = field(default_factory=dict)
    message_type: str = "request"

    message_id: str = field(
        default_factory=lambda: str(uuid4())
    )

    reply_to: str | None = None

    timestamp: str = field(
        default_factory=lambda: datetime.now().isoformat(
            timespec="seconds"
        )
    )

    metadata: dict[str, Any] = field(default_factory=dict)

    def create_response(
        self,
        sender: str,
        payload: dict[str, Any],
        task: str | None = None,
        message_type: str = "response"
    ) -> "AgentMessage":
        """
        Create a response message to the current message.
        The response message:
        - is sent back to the sender;
        - maintains the link to the original message through reply_to.
        """

        return AgentMessage(
            sender=sender,
            receiver=self.sender,
            task=task or self.task,
            payload=payload,
            message_type=message_type,
            reply_to=self.message_id
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Transform the message into a dictionary.
        Useful for logging or saving.
        """

        return {
            "message_id": self.message_id,
            "sender": self.sender,
            "receiver": self.receiver,
            "task": self.task,
            "payload": self.payload,
            "message_type": self.message_type,
            "reply_to": self.reply_to,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }