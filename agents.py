import json
from re import error
from typing import Any
from agent_message import AgentMessage
from ollama import Client, ResponseError
from state import OrderItem, PendingOrder, SessionState
from invoice_tools import generate_invoice_pdf
from agent_message import AgentMessage
from message_bus import MessageBus
from tasks import (
    PRODUCT_AGENT_SYSTEM_PROMPT,
    ORDER_EXTRACTION_SYSTEM_PROMPT,
    ORDER_SUMMARY_SYSTEM_PROMPT,
    build_product_task,
    build_order_extraction_task,
    build_order_summary_task
)
from tools import (
    search_products,
    load_products,
    validate_order_items,
    calculate_order_total
)

class ProductAgent:
    """
    A specialised agent for handling questions about the confectionery's products.
    """

    def __init__(
        self,
        model_name: str = "qwen3.5:2b",
        ollama_host: str = "http://localhost:11434"
    ) -> None:
        self.model_name = model_name
        self.client = Client(host=ollama_host)

    def format_products_context(
        self,
        products: list[dict[str, Any]]
    ) -> str:
        """
        Transform the tool's results into a text sent to the model.
        """

        if not products:
            return "No relevant products found."

        return json.dumps(
            products,
            ensure_ascii=False,
            indent=2
        )

    def answer(self, user_message: str) -> str:
        """
        Execute the complete flow of the Product Agent.
        """

        print("\n[FLOW] ProductAgent a primit mesajul utilizatorului")
        print("[FLOW] ProductAgent -> search_products")

        products = search_products(user_message)

        print(
            f"[FLOW] search_products -> "
            f"{len(products)} produse gasite"
        )

        products_context = self.format_products_context(products)

        task = build_product_task(
            user_message=user_message,
            products_context=products_context
        )

        print(
            f"[FLOW] ProductAgent -> Ollama "
            f"({self.model_name})"
        )

        try:
            response = self.client.chat(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": PRODUCT_AGENT_SYSTEM_PROMPT
                    },
                    {
                        "role": "user",
                        "content": task
                    }
                ],
                options={
                    "temperature": 0.2
                }
            )
        except ResponseError as error:
            return (
                "Nu am putut obtine un raspuns de la modelul AI. "
                f"Eroare Ollama: {error}"
            )
        except ConnectionError:
            return (
                "Nu ma pot conecta la Ollama. "
                "Verifica daca aplicatia Ollama ruleaza."
            )

        answer = response.message.content.strip()

        print("[FLOW] Ollama -> ProductAgent")
        print("[FLOW] ProductAgent -> Orchestrator")

        return answer
    
    def handle_message(
    self,
    message: AgentMessage
    ) -> AgentMessage:
        """
        Process the messages received from other agents.
        Accepts the following tasks:
        - find_products
        - validate_order_products
        """

        print(
            f"\n[AGENT] ProductAgent received task "
            f"'{message.task}' from {message.sender}"
        )

        if message.task == "find_products":
            query = str(
                message.payload.get("query", "")
            ).strip()

            if not query:
                return message.create_response(
                    sender="ProductAgent",
                    message_type="error",
                    payload={
                        "success": False,
                        "error": "The product search query is empty."
                    }
                )

            products = search_products(query)

            return message.create_response(
                sender="ProductAgent",
                payload={
                    "success": True,
                    "products": products,
                    "count": len(products)
                }
            )

        if message.task == "validate_order_products":
            requested_items = message.payload.get(
                "items",
                []
            )

            if not isinstance(requested_items, list):
                return message.create_response(
                    sender="ProductAgent",
                    message_type="error",
                    payload={
                        "success": False,
                        "error": (
                            "The 'items' field must be a list."
                        )
                    }
                )

            print(
                "[AGENT] ProductAgent -> "
                "validate_order_items"
            )

            valid_items, validation_errors = (
                validate_order_items(requested_items)
            )

            print(
                "[AGENT] ProductAgent validation result: "
                f"{len(valid_items)} valid items, "
                f"{len(validation_errors)} errors"
            )

            return message.create_response(
                sender="ProductAgent",
                payload={
                    "success": True,
                    "valid_items": valid_items,
                    "validation_errors": validation_errors
                }
            )

        return message.create_response(
            sender="ProductAgent",
            task=f"{message.task}_unsupported",
            message_type="error",
            payload={
                "success": False,
                "error": (
                    f"ProductAgent does not support "
                    f"task '{message.task}'."
                )
            }
        )
    

ORDER_EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "product_name": {
                        "type": "string"
                    },
                    "quantity": {
                        "type": "integer",
                        "minimum": 1
                    }
                },
                "required": [
                    "product_name",
                    "quantity"
                ],
                "additionalProperties": False
            }
        }
    },
    "required": ["items"],
    "additionalProperties": False
}


class OrderAgent:
    """
    A specialized agent for constructing a proposed order.
    """

    def __init__(
    self,
    session_state: SessionState,
    message_bus: MessageBus,
    model_name: str = "qwen3.5:2b",
    ollama_host: str = "http://localhost:11434"
    ) -> None:
        self.session_state = session_state
        self.message_bus = message_bus
        self.model_name = model_name
        self.client = Client(host=ollama_host)

    def get_available_product_names(self) -> list[str]:
        """
        Return the names of available products.
        """
        products = load_products()
        return [
            product["name"]
            for product in products
            if product.get("available", False)
        ]

    def extract_order_items(
        self,
        user_message: str
    ) -> list[dict[str, Any]]:
        """
        Use Qwen to extract the products and quantities.
        """
        product_names = self.get_available_product_names()
        extraction_task = build_order_extraction_task(
            user_message=user_message,
            available_product_names=product_names
        )
        print("[FLOW] OrderAgent -> Ollama: extract order")
        response = self.client.chat(
            model=self.model_name,
            messages=[
                {
                    "role": "system",
                    "content": ORDER_EXTRACTION_SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": extraction_task
                }
            ],
            format=ORDER_EXTRACTION_SCHEMA,
            think=False,
            options={
                "temperature": 0,
                "num_predict": 150
            }

        )
        raw_content = response.message.content.strip()
        print("[DEBUG] Raw model response:")
        print(repr(raw_content))
        print("[FLOW] Ollama -> OrderAgent: structured order")
        try:
            extracted_data = json.loads(raw_content)
        except json.JSONDecodeError as error:
            raise RuntimeError(
                "OrderAgent did not return valid JSON."
            ) from error
        items = extracted_data.get("items", [])
        if not isinstance(items, list):
            raise RuntimeError(
                "The extracted 'items' field is not a list."
            )
        return items

    def build_summary(
        self,
        user_message: str,
        order_items: list[dict[str, Any]],
        order_total: float,
        validation_errors: list[str]
    ) -> str:
        summary_task = build_order_summary_task(
            user_message=user_message,
            order_items=order_items,
            order_total=order_total,
            validation_errors=validation_errors
        )
        print("[FLOW] OrderAgent -> Ollama: build summary")
        response = self.client.chat(
            model=self.model_name,
            messages=[
                {
                    "role": "system",
                    "content": ORDER_SUMMARY_SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": summary_task
                }
            ],
            think=False,
            options={
                "temperature": 0.2,
                "num_predict": 300
            },
            keep_alive="30m"
        )
        answer = response.message.content.strip()
        print("[DEBUG] Final summary content:")
        print(repr(answer))
        if not answer:
            raise RuntimeError(
                "OrderAgent returned an empty order summary."
            )
        print("[FLOW] Ollama -> OrderAgent: final summary")
        return answer

    def answer(self, user_message: str) -> str:
        """
        Execute the entire flow of the OrderAgent.
        """
        print("\n[FLOW] OrderAgent received the user message")
        try:
            requested_items = self.extract_order_items(
                user_message
            )
            print(
                "[FLOW] OrderAgent extracted "
                f"{len(requested_items)} requested items"
            )
            if not requested_items:
                return (
                    "I could not identify a product order in your "
                    "message. Please specify the product and quantity."
                )
            print(
                "[FLOW] OrderAgent -> ProductAgent "
                "through MessageBus"
            )
            valid_items, validation_errors = (
                self.request_product_validation(
                    requested_items
                )
            )
            print(
                "[FLOW] validate_order_items -> "
                f"{len(valid_items)} valid items, "
                f"{len(validation_errors)} errors"
            )
            if not valid_items:
                return self.build_summary(
                    user_message=user_message,
                    order_items=[],
                    order_total=0.0,
                    validation_errors=validation_errors
                )
            print("[FLOW] OrderAgent -> calculate_order_total")
            calculated_items, order_total = (
                calculate_order_total(valid_items)
            )
            print(
                "[FLOW] calculate_order_total -> "
                f"{order_total:.2f} RON"
            )
            print("[FLOW] OrderAgent -> save_pending_order")
            pending_order = self.save_pending_order(
                calculated_items=calculated_items,
                order_total=order_total
            )
            print(
                "[FLOW] PendingOrder saved in SessionState "
                f"with status: {pending_order.status}"
            )
            return self.build_summary(
                user_message=user_message,
                order_items=calculated_items,
                order_total=order_total,
                validation_errors=validation_errors
            )
        except ResponseError as error:
            return (
                "The AI model could not process the order. "
                f"Ollama error: {error}"
            )
        except ConnectionError:
            return (
                "Could not connect to Ollama. "
                "Please check whether Ollama is running."
            )
        except RuntimeError as error:
            return (
                "The order could not be processed correctly. "
                f"Reason: {error}"
            )
        
    def save_pending_order(
        self,
        calculated_items: list[dict[str, Any]],
        order_total: float
    ) -> PendingOrder:
        """
        Transforms the validated dictionaries into OrderItem objects
        and saves the order in SessionState.
        """
        order_items: list[OrderItem] = []
        for item in calculated_items:
            order_item = OrderItem(
                product_id=item.get("product_id"),
                product_name=item["product_name"],
                quantity=int(item["quantity"]),
                unit_price=float(item["unit_price"]),
                subtotal=float(item["subtotal"]),
                price_unit=item.get("price_unit", "RON/piece")
            )
            order_items.append(order_item)
        pending_order = PendingOrder(
            items=order_items,
            total=float(order_total),
            status="awaiting_confirmation"
        )
        self.session_state.pending_order = pending_order
        return pending_order
    
    def request_product_validation(
    self,
    requested_items: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], list[str]]:
        """
        Ask ProductAgent to validate the products in the order.
        """

        request = AgentMessage(
            sender="OrderAgent",
            receiver="ProductAgent",
            task="validate_order_products",
            payload={
                "items": requested_items
            },
            metadata={
                "purpose": "order_validation"
            }
        )

        print(
            "[AGENT] OrderAgent -> MessageBus: "
            "request product validation"
        )

        response = self.message_bus.send(request)

        print(
            "[AGENT] MessageBus -> OrderAgent: "
            "product validation response"
        )

        if response.message_type == "error":
            error_message = response.payload.get(
                "error",
                "Unknown ProductAgent error."
            )

            raise RuntimeError(
                f"ProductAgent validation failed: "
                f"{error_message}"
            )

        if not response.payload.get("success", False):
            raise RuntimeError(
                "ProductAgent could not validate the products."
            )

        valid_items = response.payload.get(
            "valid_items",
            []
        )

        validation_errors = response.payload.get(
            "validation_errors",
            []
        )

        if not isinstance(valid_items, list):
            raise RuntimeError(
                "ProductAgent returned invalid 'valid_items'."
            )

        if not isinstance(validation_errors, list):
            raise RuntimeError(
                "ProductAgent returned invalid "
                "'validation_errors'."
            )

        return valid_items, validation_errors
    
class InvoiceAgent:
    """
    Responsable for generating the invoice for a confirmed order.
    """

    def __init__(
        self,
        session_state: SessionState
    ) -> None:
        self.session_state = session_state

    def generate_invoice(self) -> str:
        """
        Generates the invoice for the confirmed order in SessionState.
        """

        print("\n[FLOW] InvoiceAgent received invoice request")

        order = self.session_state.pending_order

        if order is None:
            return (
                "There is no order available for invoice generation."
            )

        if order.status == "invoiced":
            return (
                "The invoice has already been generated.\n"
                f"File: {order.invoice_path}"
            )

        if order.status != "confirmed":
            return (
                "The invoice cannot be generated because the order "
                f"status is '{order.status}'."
            )

        try:
            print("[FLOW] InvoiceAgent -> generate_invoice_pdf")

            invoice_path = generate_invoice_pdf(order)

            print("[FLOW] generate_invoice_pdf -> InvoiceAgent")

            order.invoice_path = invoice_path
            order.status = "invoiced"

            print(
                "[STATE] PendingOrder status changed: "
                "confirmed -> invoiced"
            )

            print(
                f"[STATE] Invoice path: {invoice_path}"
            )

            return (
                "The invoice was generated successfully.\n"
                f"File: {invoice_path}"
            )

        except (ValueError, OSError) as error:
            return (
                "The invoice could not be generated. "
                f"Reason: {error}"
            )

    def handle_message(
        self,
        message: AgentMessage
    ) -> AgentMessage:
        """
        Process the messages received from other agents or from the orchestrator.
        Accepts the following task:
        - generate_invoice
        """

        print(
            f"\n[AGENT] InvoiceAgent received task "
            f"'{message.task}' from {message.sender}"
        )

        if message.task != "generate_invoice":
            return message.create_response(
                sender="InvoiceAgent",
                task=f"{message.task}_unsupported",
                message_type="error",
                payload={
                    "success": False,
                    "error": (
                        f"InvoiceAgent does not support "
                        f"task '{message.task}'."
                    )
                }
            )

        order = self.session_state.pending_order

        if order is None:
            return message.create_response(
                sender="InvoiceAgent",
                message_type="error",
                payload={
                    "success": False,
                    "error": (
                        "There is no order available for "
                        "invoice generation."
                    )
                }
            )

        requested_order_id = message.payload.get(
            "order_id"
        )

        if (
            requested_order_id
            and requested_order_id != order.order_id
        ):
            return message.create_response(
                sender="InvoiceAgent",
                message_type="error",
                payload={
                    "success": False,
                    "error": (
                        "The requested order ID does not match "
                        "the current confirmed order."
                    ),
                    "requested_order_id": requested_order_id,
                    "current_order_id": order.order_id
                }
            )

        if order.status == "invoiced":
            return message.create_response(
                sender="InvoiceAgent",
                payload={
                    "success": True,
                    "already_generated": True,
                    "order_id": order.order_id,
                    "invoice_path": order.invoice_path,
                    "status": order.status
                }
            )

        if order.status != "confirmed":
            return message.create_response(
                sender="InvoiceAgent",
                message_type="error",
                payload={
                    "success": False,
                    "error": (
                        "The invoice can only be generated for "
                        "a confirmed order."
                    ),
                    "order_status": order.status
                }
            )

        try:
            print(
                "[AGENT] InvoiceAgent -> "
                "generate_invoice_pdf"
            )

            invoice_path = generate_invoice_pdf(order)

            order.invoice_path = invoice_path
            order.status = "invoiced"

            print(
                "[STATE] PendingOrder status changed: "
                "confirmed -> invoiced"
            )

            return message.create_response(
                sender="InvoiceAgent",
                payload={
                    "success": True,
                    "already_generated": False,
                    "order_id": order.order_id,
                    "invoice_path": invoice_path,
                    "status": order.status
                }
            )

        except (ValueError, OSError) as error:
            return message.create_response(
                sender="InvoiceAgent",
                message_type="error",
                payload={
                    "success": False,
                    "error": str(error),
                    "error_type": type(error).__name__
                }
            )