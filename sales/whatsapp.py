
from urllib.parse import quote

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone

from .models import Sale


@login_required
def sale_whatsapp(request, pk):
    sale = get_object_or_404(
        Sale.objects.select_related(
            "customer",
            "created_by",
        ).prefetch_related(
            "items__product",
            "items__product_size",
        ),
        pk=pk,
    )

    # Get customer name
    if sale.customer:
        customer_name = sale.customer.name
        customer_phone = getattr(sale.customer, "phone", "")
    else:
        customer_name = "Walk-in Customer"
        customer_phone = ""

    # Format invoice date
    invoice_date = timezone.localtime(
        sale.created_at
    ).strftime("%d-%m-%Y")

    # Build WhatsApp invoice message
    message_lines = [
        "Ananta Aura - Invoice",
        "",
        f"Hello {customer_name},",
        "Thank you for shopping with us!",
        "",
        f"Invoice No: {sale.invoice_number}",
        f"Date: {invoice_date}",
        "",
        "Items:",
    ]

    # Add products with their selected sizes
    sale_items = sale.items.select_related(
        "product",
        "product_size",
    ).all()

    for item in sale_items:
        product_name = item.product.name

        if item.product_size:
            size_text = f" (Size: {item.product_size.size})"
        else:
            size_text = " (Size not recorded)"

        message_lines.append(
            f"- {product_name}{size_text} "
            f"x {item.quantity} = "
            f"Rs. {item.total_price:.2f}"
        )

    # Add invoice totals
    message_lines.extend([
        "",
        f"Subtotal: Rs. {sale.subtotal:.2f}",
        f"Discount: Rs. {sale.discount_amount:.2f}",
        f"Tax: Rs. {sale.tax:.2f}",
        f"Total Amount: Rs. {sale.total_amount:.2f}",
        f"Payment Method: {sale.get_payment_method_display()}",
        "",
        "Thank you for your business!",
        "Ananta Aura",
    ])

    whatsapp_message = "\n".join(message_lines)

    # Open WhatsApp with the customer's phone number
    encoded_message = quote(whatsapp_message)

    if customer_phone:
        # Remove spaces and common phone-number separators
        phone = "".join(
            character
            for character in str(customer_phone)
            if character.isdigit()
        )

        # Add India's country code when the number is 10 digits
        if len(phone) == 10:
            phone = "91" + phone

        whatsapp_url = (
            f"https://wa.me/{phone}"
            f"?text={encoded_message}"
        )
    else:
        # Open WhatsApp without a recipient when no phone exists
        whatsapp_url = (
            f"https://wa.me/?text={encoded_message}"
        )

    return redirect(whatsapp_url)
