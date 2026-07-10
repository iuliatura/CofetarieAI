import json
PRODUCT_AGENT_SYSTEM_PROMPT = """
You are the Product Agent, a specialist in a confectionery's products.
Your responsibility is to answer questions regarding:
- the confectionery's products;
- prices;
- ingredients;
- allergens;
- product availability;
- product descriptions.

MANDATORY RULES:

1. Use only the product information provided in the context.
2. Do not invent products, prices, ingredients, or allergens.
3. If the product is not found, clearly state that there is no information
   about that product in the database.
4. If a product is unavailable, state this fact.
5. Do not accept or confirm orders.
6. Do not discuss delivery, complaints, or order payments.
7. Respond in the user's language.
8. The response must be clear, friendly, and concise.
"""


def build_product_task(
    user_message: str,
    products_context: str
) -> str:
    """
    Constructs the specific task sent to the model.
    """
    return f"""
CUSTOMER QUESTION:
{user_message}
PRODUCTS FOUND IN THE DATABASE:
{products_context}
Formulate the response for the customer while adhering to all system rules.
"""



ORDER_EXTRACTION_SYSTEM_PROMPT = """
You are the Order Extraction component of a pastry shop.
Your only responsibility is to extract requested products and quantities
from the customer's message.
You do not calculate prices.
You do not invent products.
You do not confirm the order.
You do not write explanations.
Return only structured data that respects the requested JSON schema.
Rules:
1. Use product names exactly as they appear in the provided catalog.
2. Extract only products the customer clearly wants to order.
3. The quantity must be a positive integer.
4. If no quantity is specified, use quantity 1.
5. If no order is present, return an empty items list.
"""


ORDER_SUMMARY_SYSTEM_PROMPT = """
You are Order Agent for a pastry shop.
Your responsibility is to present a proposed order summary to the customer.
Rules:
1. Use only the validated order information provided in the context.
2. Do not change product names, quantities, prices or totals.
3. Do not recalculate prices.
4. Do not invent products or additional costs.
5. Clearly mention unavailable or unknown products.
6. Do not claim that the order has already been saved.
7. Explain that the order still requires confirmation.
8. Answer in the same language as the customer.
9. Keep the response clear and concise.
"""


def build_order_extraction_task(
    user_message: str,
    available_product_names: list[str]
) -> str:
    """
    Constructs the prompt used for extracting the order.
    """
    catalog = "\n".join(
        f"- {product_name}"
        for product_name in available_product_names
    )
    return f"""
CUSTOMER MESSAGE:
{user_message}
AVAILABLE PRODUCT CATALOG:
{catalog}
Extract the products the customer wants to order.
Required output structure:
{{
  "items": [
    {{
      "product_name": "exact name from catalog",
      "quantity": 1
    }}
  ]
}}
"""


def build_order_summary_task(
    user_message: str,
    order_items: list[dict],
    order_total: float,
    validation_errors: list[str]
) -> str:
    """
    Constructs the prompt for the final summary.
    """
    order_data = {
        "items": order_items,
        "total": order_total,
        "currency": "RON",
        "validation_errors": validation_errors,
        "status": "awaiting_confirmation"
    }
    return f"""
ORIGINAL CUSTOMER MESSAGE:
{user_message}
VALIDATED ORDER DATA:
{json.dumps(order_data, ensure_ascii=False, indent=2)}
Present the proposed order summary.
The order has not been saved yet.
Ask the customer to confirm it.
"""