from agents import OrderAgent, ProductAgent, InvoiceAgent
from state import SessionState
from tools import generate_order_id
from message_bus import MessageBus



class Orchestrator:
    def __init__(self) -> None:
        self.session_state = SessionState()
        self.message_bus = MessageBus()
        self.product_agent = ProductAgent()
        self.order_agent = OrderAgent(
            session_state=self.session_state,
            message_bus=self.message_bus
        )
        self.invoice_agent = InvoiceAgent(
            session_state=self.session_state
        )
        self.register_agents()

    def register_agents(self) -> None:
        """
        Registers the agents with the message bus.
        """
        self.message_bus.register_agent(
            "ProductAgent",
            self.product_agent.handle_message
        )
        self.message_bus.register_agent(
            "InvoiceAgent",
            self.invoice_agent.handle_message
    )

    def is_confirmation(self, user_message: str) -> bool:
        normalized_message = user_message.lower().strip()

        confirmation_phrases = {
            "confirm",
            "confirm order",
            "confirm the order",
            "yes",
            "yes confirm",
            "yes, confirm",
            "ok",
            "okay",
            "proceed",
            "that's correct",
            "that is correct",
            "confirma",
            "confirmă",
            "confirm comanda",
            "confirmă comanda",
            "da",
            "da, confirm"
        }

        return normalized_message in confirmation_phrases

    def confirm_pending_order(self) -> str:
        pending_order = self.session_state.pending_order

        if pending_order is None:
            return "There is no pending order to confirm."

        if pending_order.status == "confirmed":
            return (
                f"Order {pending_order.order_id} "
                "has already been confirmed."
            )

        if pending_order.status != "awaiting_confirmation":
            return (
                "The current order cannot be confirmed because "
                f"its status is '{pending_order.status}'."
            )

        pending_order.status = "confirmed"
        pending_order.order_id = generate_order_id()

        print(
            "[STATE] PendingOrder status changed: "
            "awaiting_confirmation -> confirmed"
        )

        print(
            f"[STATE] Generated order ID: "
            f"{pending_order.order_id}"
        )

        invoice_response = self.invoice_agent.generate_invoice()

        return (
            f"Order {pending_order.order_id} "
            "was confirmed successfully.\n"
            f"Total: {pending_order.total:.2f} RON.\n\n"
            f"{invoice_response}"
        )

    def detect_intent(self, user_message: str) -> str:
        message = user_message.lower()

        order_phrases = {
            "i want to order",
            "i would like to order",
            "i want",
            "i'll take",
            "place an order",
            "order me",
            "buy",
            "purchase",
            "vreau să comand",
            "vreau sa comand",
            "aș dori",
            "as dori",
            "comand",
            "cumpăr",
            "cumpar"
        }

        if any(
            phrase in message
            for phrase in order_phrases
        ):
            return "place_order"

        return "product_question"

    def handle_message(self, user_message: str) -> str:
        print("\n[FLOW] User -> Orchestrator")
        print( "[DEBUG] is_confirmation:", self.is_confirmation(user_message)
    )
        # Confirmarea trebuie verificată prima.
        if self.is_confirmation(user_message):
            print("[FLOW] Orchestrator detected confirmation")

            response = self.confirm_pending_order()

            print("[FLOW] Orchestrator -> User")

            return response

        # Abia după aceea detectăm intenția normală.
        intent = self.detect_intent(user_message)

        print(
            f"[FLOW] Orchestrator detected intent: {intent}"
        )

        if intent == "place_order":
            print("[FLOW] Orchestrator -> OrderAgent")

            response = self.order_agent.answer(user_message)

            if self.session_state.pending_order is not None:
                print("[STATE] Pending order:")
                print(self.session_state.pending_order)

            print("[FLOW] OrderAgent -> Orchestrator")

        else:
            print("[FLOW] Orchestrator -> ProductAgent")

            response = self.product_agent.answer(user_message)

            print("[FLOW] ProductAgent -> Orchestrator")

        print("[FLOW] Orchestrator -> User")

        return response
    
    def request_invoice_generation(
    self
    ) -> str:
        """
        
        """

        pending_order = self.session_state.pending_order

        if pending_order is None:
            return "There is no order available for invoice generation."

        if pending_order.status != "confirmed":
            return (
                "The invoice cannot be requested because the order "
                f"status is '{pending_order.status}'."
            )

        request = AgentMessage(
            sender="Orchestrator",
            receiver="InvoiceAgent",
            task="generate_invoice",
            payload={
                "order_id": pending_order.order_id
            },
            metadata={
                "reason": "order_confirmed",
                "handoff": True
            }
        )

        print(
            "[HANDOFF] Orchestrator -> InvoiceAgent "
            "through MessageBus"
        )

        response = self.message_bus.send(request)

        print(
            "[HANDOFF] InvoiceAgent -> Orchestrator "
            "through MessageBus"
        )

        if response.message_type == "error":
            error_message = response.payload.get(
                "error",
                "Unknown invoice generation error."
            )

            return (
                "The invoice could not be generated. "
                f"Reason: {error_message}"
            )

        if not response.payload.get("success", False):
            return (
                "InvoiceAgent could not generate the invoice."
            )

        invoice_path = response.payload.get(
            "invoice_path"
        )

        already_generated = response.payload.get(
            "already_generated",
            False
        )

        if already_generated:
            return (
                "The invoice had already been generated.\n"
                f"File: {invoice_path}"
            )

        return (
            "The invoice was generated successfully.\n"
            f"File: {invoice_path}"
        )