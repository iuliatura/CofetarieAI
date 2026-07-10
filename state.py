from dataclasses import dataclass
from typing import List

@dataclass
class OrderItem:
    product_id: int | None
    product_name: str
    quantity: int
    unit_price: float
    subtotal: float
    price_unit: str = "RON/piece"

@dataclass
class PendingOrder:
    items: list[OrderItem]
    total: float
    status: str = "awaiting_confirmation"
    order_id: str | None = None
    invoice_path: str | None = None

@dataclass
class SessionState:
    pending_order: PendingOrder | None = None