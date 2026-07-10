import json
import re
from pathlib import Path
from typing import Any


PRODUCTS_FILE = Path(__file__).parent / "data" / "products.json"


def load_products() -> list[dict[str, Any]]:
    """
    Load all of the products from the JSON file and return them as a list of dictionaries.
    """

    try:
        with PRODUCTS_FILE.open("r", encoding="utf-8") as file:
            products = json.load(file)
    except FileNotFoundError as error:
        raise RuntimeError(
            f"No file: {PRODUCTS_FILE}"
        ) from error
    except json.JSONDecodeError as error:
        raise RuntimeError(
            f"The file {PRODUCTS_FILE} does not have a valid JSON format."
        ) from error

    if not isinstance(products, list):
        raise RuntimeError("The file products.json must contain a list.")
    return products


def normalize_text(text: str) -> str:
    """
    Transform the text into a more comparable format.
    """

    text = text.lower().strip()
    text = re.sub(r"[^\wăâîșț]+", " ", text)
    return text


def search_products(query: str) -> list[dict[str, Any]]:
    """
   Search for relevant products based on the query and return a list of matching products.
   The search is case-insensitive and ignores certain common words to focus on significant terms.
    """

    normalized_query = normalize_text(query)
    query_words = set(normalized_query.split())

    products = load_products()
    results: list[dict[str, Any]] = []

    ignored_words = {
        "have",
        "exists",
        "want",
        "about",
        "which",
        "is",
        "are",
        "product",
        "products",
        "price",
        "cost",
        "contains",
        "ingredient",
        "ingredients",
        "allergen",
        "allergens",
        "a",
        "with",
        "of",
        "to",
        "in"
}

    significant_words = query_words - ignored_words

    for product in products:
        searchable_fields = [
            product.get("name", ""),
            product.get("category", ""),
            product.get("description", ""),
            " ".join(product.get("ingredients", [])),
            " ".join(product.get("allergens", []))
        ]

        searchable_text = normalize_text(" ".join(searchable_fields))

        if any(word in searchable_text for word in significant_words):
            results.append(product)

    return results

def get_product_by_name(
    product_name: str
) -> dict[str, Any] | None:
    """
    Search a product by name.
    First, try an exact match.
    If that doesn't exist, try a partial match.
    """

    products = load_products()
    normalized_name = normalize_text(product_name)

    for product in products:
        current_name = normalize_text(product.get("name", ""))

        if current_name == normalized_name:
            return product

    for product in products:
        current_name = normalize_text(product.get("name", ""))

        if (
            normalized_name in current_name
            or current_name in normalized_name
        ):
            return product

    return None


def validate_order_items(
    requested_items: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[str]]:
    """
    Check the products and quantities extracted by the model.
    Return only the valid products and quantities, and collect any errors found.
    """

    valid_items: list[dict[str, Any]] = []
    errors: list[str] = []

    for requested_item in requested_items:
        product_name = str(
            requested_item.get("product_name", "")
        ).strip()

        quantity = requested_item.get("quantity", 0)

        if not product_name:
            errors.append(
                "One of the requested products has no name."
            )
            continue

        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            errors.append(
                f"The quantity for '{product_name}' is invalid."
            )
            continue

        if quantity <= 0:
            errors.append(
                f"The quantity for '{product_name}' must be greater than 0."
            )
            continue

        product = get_product_by_name(product_name)

        if product is None:
            errors.append(
                f"Product '{product_name}' was not found."
            )
            continue

        if not product.get("available", False):
            errors.append(
                f"Product '{product['name']}' is currently unavailable."
            )
            continue

        unit_price = float(product.get("price", 0))

        valid_items.append(
            {
                "product_id": product.get("id"),
                "product_name": product["name"],
                "quantity": quantity,
                "unit_price": unit_price,
                "price_unit": product.get(
                    "price_unit",
                    "lei/piece"
                )
            }
        )

    return valid_items, errors


def calculate_order_total(
    order_items: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], float]:
    """
    Calculate the subtotal for each product and the total for the order.
    """

    calculated_items: list[dict[str, Any]] = []
    order_total = 0.0

    for item in order_items:
        quantity = int(item["quantity"])
        unit_price = float(item["unit_price"])

        subtotal = quantity * unit_price
        order_total += subtotal

        calculated_item = item.copy()
        calculated_item["subtotal"] = round(subtotal, 2)

        calculated_items.append(calculated_item)

    return calculated_items, round(order_total, 2)

from datetime import datetime
from uuid import uuid4


def generate_order_id() -> str:
    """
    Generate a unique order ID based on the current date and a random component.
    The format is: ORD-YYYYMMDD-XXXXXX
    Example:
    ORD-20260710-A3F91C
    """
    current_date = datetime.now().strftime("%Y%m%d")
    unique_part = uuid4().hex[:6].upper()
    return f"ORD-{current_date}-{unique_part}"