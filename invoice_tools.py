from datetime import datetime
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from state import PendingOrder

INVOICES_DIRECTORY = Path(__file__).parent / "invoices"

def generate_invoice_id(order_id: str) -> str:
    """
    Generate a unique invoice ID based on the order ID and the current timestamp.
    """
    return order_id.replace("ORD-", "INV-", 1)


def generate_invoice_pdf(order: PendingOrder) -> str:
    """
    Generate a PDF for a confirmed order.
    Returns the absolute path of the generated document.
    """

    if order.status != "confirmed":
        raise ValueError(
            "An invoice can only be generated for a confirmed order."
        )

    if not order.order_id:
        raise ValueError(
            "The confirmed order does not have an order ID."
        )

    if not order.items:
        raise ValueError(
            "An invoice cannot be generated for an empty order."
        )

    INVOICES_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True
    )

    invoice_id = generate_invoice_id(order.order_id)
    invoice_path = INVOICES_DIRECTORY / f"{invoice_id}.pdf"

    pdf = canvas.Canvas(
        str(invoice_path),
        pagesize=A4
    )

    page_width, page_height = A4
    left_margin = 20 * mm
    right_margin = page_width - 20 * mm
    current_y = page_height - 20 * mm

    # Titlu
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(
        left_margin,
        current_y,
        "Pastry Shop Invoice"
    )

    current_y -= 12 * mm

    # Informații document
    pdf.setFont("Helvetica", 10)

    pdf.drawString(
        left_margin,
        current_y,
        f"Invoice ID: {invoice_id}"
    )

    current_y -= 6 * mm

    pdf.drawString(
        left_margin,
        current_y,
        f"Order ID: {order.order_id}"
    )

    current_y -= 6 * mm

    pdf.drawString(
        left_margin,
        current_y,
        f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )

    current_y -= 12 * mm

    # Antet tabel
    pdf.setFont("Helvetica-Bold", 10)

    pdf.drawString(
        left_margin,
        current_y,
        "Product"
    )

    pdf.drawRightString(
        125 * mm,
        current_y,
        "Quantity"
    )

    pdf.drawRightString(
        155 * mm,
        current_y,
        "Unit price"
    )

    pdf.drawRightString(
        right_margin,
        current_y,
        "Subtotal"
    )

    current_y -= 3 * mm

    pdf.line(
        left_margin,
        current_y,
        right_margin,
        current_y
    )

    current_y -= 7 * mm

    # Produsele
    pdf.setFont("Helvetica", 10)

    for item in order.items:
        pdf.drawString(
            left_margin,
            current_y,
            item.product_name
        )

        pdf.drawRightString(
            125 * mm,
            current_y,
            str(item.quantity)
        )

        pdf.drawRightString(
            155 * mm,
            current_y,
            f"{item.unit_price:.2f} RON"
        )

        pdf.drawRightString(
            right_margin,
            current_y,
            f"{item.subtotal:.2f} RON"
        )

        current_y -= 8 * mm

    # Total
    current_y -= 4 * mm

    pdf.line(
        125 * mm,
        current_y,
        right_margin,
        current_y
    )

    current_y -= 8 * mm

    pdf.setFont("Helvetica-Bold", 12)

    pdf.drawRightString(
        155 * mm,
        current_y,
        "Total:"
    )

    pdf.drawRightString(
        right_margin,
        current_y,
        f"{order.total:.2f} RON"
    )

    current_y -= 18 * mm

    pdf.setFont("Helvetica-Oblique", 9)

    pdf.drawString(
        left_margin,
        current_y,
        "This document was generated automatically."
    )

    pdf.save()

    return str(invoice_path.resolve())