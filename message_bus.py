from collections.abc import Callable
from typing import Any
from agent_message import AgentMessage

AgentHandler = Callable[[AgentMessage], AgentMessage]

class MessageBus:
    """
    Coordonates the communication between agents.
    The agents are registered with:
        register_agent(name, handler)
    Messages are sent with:
        send(message)
    """

    def __init__(self) -> None:
        self._handlers: dict[str, AgentHandler] = {}
        self._history: list[AgentMessage] = []

    def register_agent(
        self,
        agent_name: str,
        handler: AgentHandler
    ) -> None:
        """
        Register an agent and its processing function.
        The handler must accept an AgentMessage and return an AgentMessage.
        """

        normalized_name = agent_name.strip()

        if not normalized_name:
            raise ValueError(
                "Agent name cannot be empty."
            )

        if normalized_name in self._handlers:
            raise ValueError(
                f"Agent '{normalized_name}' is already registered."
            )

        if not callable(handler):
            raise TypeError(
                f"Handler for agent '{normalized_name}' "
                "must be callable."
            )

        self._handlers[normalized_name] = handler

        print(
            f"[BUS] Registered agent: {normalized_name}"
        )

    def unregister_agent(
        self,
        agent_name: str
    ) -> None:
        """
        Eliminates an agent from the bus, preventing it from receiving messages.
        """

        if agent_name not in self._handlers:
            raise ValueError(
                f"Agent '{agent_name}' is not registered."
            )

        del self._handlers[agent_name]

        print(
            f"[BUS] Unregistered agent: {agent_name}"
        )

    def send(
        self,
        message: AgentMessage
    ) -> AgentMessage:
        """
        Send the message to the recipient agent and return the response.
        """

        self._validate_message(message)

        print(
            f"[BUS] {message.sender} "
            f"-> {message.receiver}"
        )

        print(
            f"[BUS] Task: {message.task}"
        )

        print(
            f"[BUS] Message ID: {message.message_id}"
        )

        self._history.append(message)

        handler = self._handlers[message.receiver]

        try:
            response = handler(message)
        except Exception as error:
            error_response = message.create_response(
                sender="MessageBus",
                task=f"{message.task}_failed",
                message_type="error",
                payload={
                    "success": False,
                    "error": str(error),
                    "error_type": type(error).__name__
                }
            )

            self._history.append(error_response)

            print(
                f"[BUS ERROR] {message.receiver} failed: "
                f"{error}"
            )

            return error_response

        if not isinstance(response, AgentMessage):
            error_response = message.create_response(
                sender="MessageBus",
                task=f"{message.task}_failed",
                message_type="error",
                payload={
                    "success": False,
                    "error": (
                        f"Agent '{message.receiver}' did not "
                        "return an AgentMessage."
                    )
                }
            )

            self._history.append(error_response)

            return error_response

        self._history.append(response)

        print(
            f"[BUS] {response.sender} "
            f"-> {response.receiver}"
        )

        print(
            f"[BUS] Response to: {response.reply_to}"
        )

        return response

    def _validate_message(
        self,
        message: AgentMessage
    ) -> None:
        """
        Verifică dacă mesajul poate fi trimis.
        """

        if not isinstance(message, AgentMessage):
            raise TypeError(
                "MessageBus can only send AgentMessage objects."
            )

        if not message.sender.strip():
            raise ValueError(
                "Message sender cannot be empty."
            )

        if not message.receiver.strip():
            raise ValueError(
                "Message receiver cannot be empty."
            )

        if not message.task.strip():
            raise ValueError(
                "Message task cannot be empty."
            )

        if message.receiver not in self._handlers:
            registered_agents = ", ".join(
                self._handlers.keys()
            )

            raise ValueError(
                f"Agent '{message.receiver}' is not registered. "
                f"Registered agents: "
                f"{registered_agents or 'none'}."
            )

    def is_registered(
        self,
        agent_name: str
    ) -> bool:
        """
        Checks if an agent is registered.
        """

        return agent_name in self._handlers

    def get_registered_agents(self) -> list[str]:
        """
        Returns the list of registered agents.
        """

        return list(self._handlers.keys())

    def get_history(self) -> list[AgentMessage]:
        """
        Returns a copy of the message history.
        """

        return self._history.copy()

    def clear_history(self) -> None:
        """
        Clears the message history.
        """

        self._history.clear()

    def print_history(self) -> None:
        """
        Prints the complete flow of messages between agents.
        """

        print("\n" + "=" * 70)
        print("AGENT COMMUNICATION HISTORY")
        print("=" * 70)

        if not self._history:
            print("No messages were exchanged.")
            return

        for index, message in enumerate(
            self._history,
            start=1
        ):
            print(
                f"\n[{index}] "
                f"{message.sender} -> {message.receiver}"
            )

            print(
                f"    Type: {message.message_type}"
            )

            print(
                f"    Task: {message.task}"
            )

            print(
                f"    ID: {message.message_id}"
            )

            if message.reply_to:
                print(
                    f"    Reply to: {message.reply_to}"
                )

            print(
                f"    Timestamp: {message.timestamp}"
            )

            print(
                f"    Payload: {message.payload}"
            )

        print("\n" + "=" * 70)