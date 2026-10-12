from decimal import Decimal, InvalidOperation
import os

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from customers.models import Customer
from products.models import Product
from .models import Sale, SaleItem


# =========================================================
# DELETE SALE
# =========================================================

@login_required
def sale_delete(request, pk):
    sale = get_object_or_404(
        Sale.objects.prefetch_related("items__product"),
        pk=pk,
    )

    if request.method == "POST":
        with transaction.atomic():
            for item in sale.items.all():
                product = (
                    Product.objects.select_for_update()
                    .get(pk=item.product.id)
                )
                product.stock += item.quantity
                product.save(update_fields=["stock", "updated_at"])

            sale.delete()

        messages.success(
            request,
            "Invoice deleted successfully and stock has been restored.",
        )
        return redirect("sale_list")

    return render(
        request,
        "sales/sale_confirm_delete.html",
        {"sale": sale},
    )


# =========================================================
# PDF FONT SETUP
# =========================================================

FONT_PATH = "C:/Windows/Fonts/arial.ttf"
FONT_BOLD_PATH = "C:/Windows/Fonts/arialbd.ttf"

if os.path.exists(FONT_PATH):
    pdfmetrics.registerFont(TTFont("BusinessFlowFont", FONT_PATH))

    if os.path.exists(FONT_BOLD_PATH):
        pdfmetrics.registerFont(
            TTFont("BusinessFlowFontBold", FONT_BOLD_PATH)
        )
    else:
        pdfmetrics.registerFont(
            TTFont("BusinessFlowFontBold", FONT_PATH)
        )

    PDF_FONT = "BusinessFlowFont"
    PDF_BOLD_FONT = "BusinessFlowFontBold"
else:
    PDF_FONT = "Helvetica"
    PDF_BOLD_FONT = "Helvetica-Bold"


# =========================================================
# INVOICE NUMBER
# =========================================================

def generate_invoice_number():
    today = timezone.localdate()
    date_part = today.strftime("%Y%m%d")
    prefix = f"INV-{date_part}-"

    last_sale = (
        Sale.objects.filter(invoice_number__startswith=prefix)
        .order_by("-id")
        .first()
    )

    if last_sale:
        last_number = int(
            last_sale.invoice_number.replace(prefix, "")
        )
        next_number = last_number + 1
    else:
        next_number = 1

    return f"{prefix}{next_number:04d}"


# =========================================================
# SALES LIST
# =========================================================

@login_required
def sale_list(request):
    sales = (
        Sale.objects.select_related("customer", "created_by")
        .prefetch_related("items__product")
        .order_by("-created_at")
    )

    return render(
        request,
        "sales/sale_list.html",
        {"sales": sales},
    )


# =========================================================
# SALE DETAIL
# =========================================================

@login_required
def sale_detail(request, pk):
    sale = get_object_or_404(
        Sale.objects.select_related("customer", "created_by")
        .prefetch_related("items__product"),
        pk=pk,
    )

    return render(
        request,
        "sales/sale_detail.html",
        {"sale": sale},
    )


# =========================================================
# SALE PDF
# =========================================================

@login_required
def sale_pdf(request, pk):
    sale = get_object_or_404(
        Sale.objects.select_related("customer", "created_by")
        .prefetch_related("items__product"),
        pk=pk,
    )

    local_created_at = timezone.localtime(sale.created_at)

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="{sale.invoice_number}.pdf"'
    )

    document = SimpleDocTemplate(
        response,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title=f"Invoice {sale.invoice_number}",
        author="BusinessFlow",
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "BusinessFlowTitle",
        parent=styles["Normal"],
        fontName=PDF_BOLD_FONT,
        fontSize=20,
        leading=23,
        textColor=colors.HexColor("#172033"),
    )

    invoice_label_style = ParagraphStyle(
        "InvoiceLabel",
        parent=styles["Normal"],
        fontName=PDF_BOLD_FONT,
        fontSize=14,
        leading=17,
        alignment=2,
        textColor=colors.HexColor("#172033"),
    )

    invoice_number_style = ParagraphStyle(
        "InvoiceNumber",
        parent=styles["Normal"],
        fontName=PDF_BOLD_FONT,
        fontSize=10,
        leading=13,
        alignment=2,
        textColor=colors.HexColor("#2563EB"),
    )

    normal_style = ParagraphStyle(
        "InvoiceNormal",
        parent=styles["Normal"],
        fontName=PDF_FONT,
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#374151"),
    )

    bold_style = ParagraphStyle(
        "InvoiceBold",
        parent=styles["Normal"],
        fontName=PDF_BOLD_FONT,
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#172033"),
    )

    section_title_style = ParagraphStyle(
        "SectionTitle",
        parent=styles["Normal"],
        fontName=PDF_BOLD_FONT,
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#172033"),
    )

    small_style = ParagraphStyle(
        "InvoiceSmall",
        parent=styles["Normal"],
        fontName=PDF_FONT,
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#6B7280"),
    )

    table_header_style = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName=PDF_BOLD_FONT,
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#374151"),
    )

    grand_total_label_style = ParagraphStyle(
        "GrandTotalLabel",
        parent=styles["Normal"],
        fontName=PDF_BOLD_FONT,
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#172033"),
    )

    grand_total_value_style = ParagraphStyle(
        "GrandTotalValue",
        parent=styles["Normal"],
        fontName=PDF_BOLD_FONT,
        fontSize=15,
        leading=18,
        alignment=2,
        textColor=colors.HexColor("#2563EB"),
    )

    story = []

    # Header
    header_data = [
        [
            Paragraph("BusinessFlow", title_style),
            Paragraph("INVOICE", invoice_label_style),
        ],
        [
            Paragraph("Business Management System", small_style),
            Paragraph(
                (
                    f"<b>{sale.invoice_number}</b><br/>"
                    f"{local_created_at.strftime('%d %b %Y, %I:%M %p')}"
                ),
                invoice_number_style,
            ),
        ],
    ]

    header_table = Table(
        header_data,
        colWidths=[105 * mm, 65 * mm],
    )

    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                (
                    "LINEBELOW",
                    (0, -1),
                    (-1, -1),
                    1.2,
                    colors.HexColor("#172033"),
                ),
                ("BOTTOMPADDING", (0, -1), (-1, -1), 9),
            ]
        )
    )

    story.append(header_table)
    story.append(Spacer(1, 7 * mm))

    # Customer and payment information
    if sale.customer:
        customer_lines = [f"<b>{sale.customer.name}</b>"]

        if sale.customer.phone:
            customer_lines.append(f"Phone: {sale.customer.phone}")

        if sale.customer.email:
            customer_lines.append(f"Email: {sale.customer.email}")

        if sale.customer.city:
            customer_lines.append(f"City: {sale.customer.city}")

        if sale.customer.address:
            customer_lines.append(f"Address: {sale.customer.address}")

        customer_text = "<br/>".join(customer_lines)
    else:
        customer_text = "<b>Walk-in Customer</b>"

    payment_name = dict(Sale.PAYMENT_METHODS).get(
        sale.payment_method,
        sale.payment_method,
    )

    customer_payment_data = [
        [
            Paragraph(
                "<b>Customer Information</b><br/>" + customer_text,
                normal_style,
            ),
            Paragraph(
                "<b>Payment Information</b><br/>"
                f"Payment Method: {payment_name}<br/>"
                f"Created By: {sale.created_by.username}",
                normal_style,
            ),
        ]
    ]

    customer_payment_table = Table(
        customer_payment_data,
        colWidths=[100 * mm, 70 * mm],
    )

    customer_payment_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    colors.HexColor("#F8FAFC"),
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.7,
                    colors.HexColor("#DCE2EA"),
                ),
                (
                    "INNERGRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#E5E7EB"),
                ),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ]
        )
    )

    story.append(customer_payment_table)
    story.append(Spacer(1, 7 * mm))

    # Products
    product_rows = [
        [
            Paragraph("#", table_header_style),
            Paragraph("Product", table_header_style),
            Paragraph("SKU", table_header_style),
            Paragraph("Qty", table_header_style),
            Paragraph("Unit Price", table_header_style),
            Paragraph("Total", table_header_style),
        ]
    ]

    for index, item in enumerate(sale.items.all(), start=1):
        product_rows.append(
            [
                str(index),
                Paragraph(item.product.name, normal_style),
                Paragraph(item.product.sku, small_style),
                str(item.quantity),
                Paragraph(f"₹{item.unit_price:.2f}", normal_style),
                Paragraph(f"₹{item.total_price:.2f}", bold_style),
            ]
        )

    product_table = Table(
        product_rows,
        colWidths=[
            10 * mm,
            55 * mm,
            30 * mm,
            15 * mm,
            30 * mm,
            30 * mm,
        ],
        repeatRows=1,
    )

    product_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#EEF4FF"),
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#DCE2EA"),
                ),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
                ("ALIGN", (3, 0), (3, -1), "CENTER"),
                ("ALIGN", (4, 0), (5, -1), "RIGHT"),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    story.append(Paragraph("Products", section_title_style))
    story.append(Spacer(1, 2 * mm))
    story.append(product_table)
    story.append(Spacer(1, 7 * mm))

    # Discount label
    if sale.discount_type == "PERCENTAGE":
        discount_label = f"Discount ({sale.discount}%)"
    else:
        discount_label = "Discount (Fixed)"

    # Bill summary
    summary_rows = [
        [
            Paragraph("Subtotal", normal_style),
            Paragraph(f"₹{sale.subtotal:.2f}", normal_style),
        ],
        [
            Paragraph(discount_label, normal_style),
            Paragraph(f"- ₹{sale.discount_amount:.2f}", normal_style),
        ],
        [
            Paragraph("Tax", normal_style),
            Paragraph(f"₹{sale.tax:.2f}", normal_style),
        ],
    ]

    summary_table = Table(
        summary_rows,
        colWidths=[130 * mm, 40 * mm],
    )

    summary_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                (
                    "LINEABOVE",
                    (0, 0),
                    (-1, 0),
                    0.5,
                    colors.HexColor("#E5E7EB"),
                ),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )

    story.append(Paragraph("Bill Summary", section_title_style))
    story.append(Spacer(1, 2 * mm))
    story.append(summary_table)
    story.append(Spacer(1, 3 * mm))

    # Grand total
    grand_total_data = [
        [
            Paragraph(
                "<b>Grand Total</b><br/>"
                "<font size='7'>Total amount payable</font>",
                grand_total_label_style,
            ),
            Paragraph(
                f"₹{sale.total_amount:.2f}",
                grand_total_value_style,
            ),
        ]
    ]

    grand_total_table = Table(
        grand_total_data,
        colWidths=[110 * mm, 60 * mm],
    )

    grand_total_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    colors.HexColor("#F4F7FF"),
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.8,
                    colors.HexColor("#CBD9F7"),
                ),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ]
        )
    )

    story.append(grand_total_table)
    story.append(Spacer(1, 5 * mm))

    # Payment note
    story.append(
        Paragraph(
            f"Payment recorded as <b>{payment_name}</b>",
            small_style,
        )
    )

    story.append(Spacer(1, 8 * mm))
    story.append(
        Paragraph("Thank you for your business.", small_style)
    )

    document.build(story)
    return response


# =========================================================
# NEW SALE
# =========================================================

@login_required
def new_sale(request):
    customers = (
        Customer.objects.filter(is_active=True).order_by("name")
    )

    products = (
        Product.objects.filter(is_active=True)
        .select_related("category")
        .order_by("name")
    )

    if request.method == "POST":
        customer_id = request.POST.get("customer")
        product_ids = request.POST.getlist("product_ids")
        quantities = request.POST.getlist("quantities")
        discount_type = request.POST.get("discount_type", "PERCENTAGE")
        discount_value = request.POST.get("discount", "0")
        tax_value = request.POST.get("tax", "0")
        payment_method = request.POST.get("payment_method", "CASH")

        # Customer validation
        customer = None

        if customer_id:
            customer = Customer.objects.filter(
                pk=customer_id,
                is_active=True,
            ).first()

            if not customer:
                messages.error(
                    request,
                    "Selected customer is not available.",
                )
                return render(
                    request,
                    "sales/new_sale.html",
                    {"customers": customers, "products": products},
                )

        # Product validation
        if not product_ids:
            messages.error(
                request,
                "Please add at least one product.",
            )
            return render(
                request,
                "sales/new_sale.html",
                {"customers": customers, "products": products},
            )

        if len(product_ids) != len(quantities):
            messages.error(
                request,
                "Product and quantity information is invalid.",
            )
            return render(
                request,
                "sales/new_sale.html",
                {"customers": customers, "products": products},
            )

        # Build cart and merge duplicate product rows
        cart = []

        for product_id, quantity_value in zip(
            product_ids,
            quantities,
        ):
            product = Product.objects.filter(
                pk=product_id,
                is_active=True,
            ).first()

            if not product:
                messages.error(
                    request,
                    "One of the selected products is no longer "
                    "available. Please refresh the page and add "
                    "the products again.",
                )
                return render(
                    request,
                    "sales/new_sale.html",
                    {"customers": customers, "products": products},
                )

            try:
                quantity = int(quantity_value)
            except (TypeError, ValueError):
                messages.error(
                    request,
                    f"Invalid quantity for {product.name}.",
                )
                return render(
                    request,
                    "sales/new_sale.html",
                    {"customers": customers, "products": products},
                )

            if quantity < 1:
                messages.error(
                    request,
                    f"Quantity for {product.name} must be at least 1.",
                )
                return render(
                    request,
                    "sales/new_sale.html",
                    {"customers": customers, "products": products},
                )

            existing_item = next(
                (
                    item for item in cart
                    if item["product"].id == product.id
                ),
                None,
            )

            if existing_item:
                existing_item["quantity"] += quantity
            else:
                cart.append(
                    {
                        "product": product,
                        "quantity": quantity,
                    }
                )

        # Initial stock check
        for item in cart:
            product = item["product"]
            quantity = item["quantity"]

            if quantity > product.stock:
                messages.error(
                    request,
                    f"Only {product.stock} unit(s) of "
                    f"{product.name} are available in stock.",
                )
                return render(
                    request,
                    "sales/new_sale.html",
                    {"customers": customers, "products": products},
                )

        # Calculate subtotal
        subtotal = Decimal("0.00")

        for item in cart:
            product = item["product"]
            quantity = item["quantity"]
            item_total = product.price * quantity

            item["unit_price"] = product.price
            item["total_price"] = item_total
            subtotal += item_total

        # Validate discount
        try:
            discount_value = Decimal(discount_value)
        except (InvalidOperation, TypeError, ValueError):
            messages.error(
                request,
                "Please enter a valid discount.",
            )
            return render(
                request,
                "sales/new_sale.html",
                {"customers": customers, "products": products},
            )

        if discount_value < 0:
            messages.error(
                request,
                "Discount cannot be negative.",
            )
            return render(
                request,
                "sales/new_sale.html",
                {"customers": customers, "products": products},
            )

        if discount_type == "PERCENTAGE":
            if discount_value > 100:
                messages.error(
                    request,
                    "Percentage discount cannot be more than 100%.",
                )
                return render(
                    request,
                    "sales/new_sale.html",
                    {"customers": customers, "products": products},
                )

            discount_amount = (
                subtotal * discount_value / Decimal("100")
            )

        elif discount_type == "AMOUNT":
            if discount_value > subtotal:
                messages.error(
                    request,
                    "Fixed discount cannot be greater than the subtotal.",
                )
                return render(
                    request,
                    "sales/new_sale.html",
                    {"customers": customers, "products": products},
                )

            discount_amount = discount_value

        else:
            messages.error(request, "Invalid discount type.")
            return render(
                request,
                "sales/new_sale.html",
                {"customers": customers, "products": products},
            )

        # Validate tax
        try:
            tax = Decimal(tax_value)
        except (InvalidOperation, TypeError, ValueError):
            messages.error(
                request,
                "Please enter a valid tax amount.",
            )
            return render(
                request,
                "sales/new_sale.html",
                {"customers": customers, "products": products},
            )

        if tax < 0:
            messages.error(request, "Tax cannot be negative.")
            return render(
                request,
                "sales/new_sale.html",
                {"customers": customers, "products": products},
            )

        # Calculate final total
        taxable_amount = subtotal - discount_amount

        if taxable_amount < 0:
            taxable_amount = Decimal("0.00")

        total_amount = taxable_amount + tax

        # Create invoice and sale items in one transaction
        with transaction.atomic():
            locked_products = {}

            for item in cart:
                product_id = item["product"].id

                locked_product = (
                    Product.objects.select_for_update()
                    .filter(pk=product_id, is_active=True)
                    .first()
                )

                if not locked_product:
                    messages.error(
                        request,
                        "One of the selected products is no longer "
                        "available.",
                    )
                    return render(
                        request,
                        "sales/new_sale.html",
                        {"customers": customers, "products": products},
                    )

                locked_products[product_id] = locked_product

            # Recheck stock after locking products
            for item in cart:
                product = locked_products[item["product"].id]
                quantity = item["quantity"]

                if quantity > product.stock:
                    messages.error(
                        request,
                        f"Only {product.stock} unit(s) of "
                        f"{product.name} are available in stock.",
                    )
                    return render(
                        request,
                        "sales/new_sale.html",
                        {"customers": customers, "products": products},
                    )

            # Create one invoice for all items
            sale = Sale.objects.create(
                invoice_number=generate_invoice_number(),
                customer=customer,
                created_by=request.user,
                subtotal=subtotal,
                discount_type=discount_type,
                discount=discount_value,
                discount_amount=discount_amount,
                tax=tax,
                total_amount=total_amount,
                payment_method=payment_method,
            )

            # Create sale items and snapshot purchase cost
            for item in cart:
                product = locked_products[item["product"].id]
                quantity = item["quantity"]

                SaleItem.objects.create(
                    sale=sale,
                    product=product,
                    quantity=quantity,
                    unit_price=product.price,
                    cost_price=product.cost_price,
                    total_price=product.price * quantity,
                )

                # Reduce stock
                product.stock -= quantity
                product.save(
                    update_fields=["stock", "updated_at"]
                )

        messages.success(
            request,
            f"Sale {sale.invoice_number} created successfully.",
        )

        return redirect("sale_list")

    return render(
        request,
        "sales/new_sale.html",
        {"customers": customers, "products": products},
    )



@login_required
def sale_edit(request, pk):
    import json
    from collections import defaultdict

    sale = get_object_or_404(Sale, pk=pk)

    products = Product.objects.filter(is_active=True).order_by("name")
    customers = Customer.objects.filter(is_active=True).order_by("name")

    if request.method == "POST":
        customer_id = request.POST.get("customer", "").strip()
        payment_method = request.POST.get("payment_method", "CASH")
        discount_type = request.POST.get("discount_type", "PERCENTAGE")

        try:
            discount = Decimal(request.POST.get("discount", "0") or "0")
            tax = Decimal(request.POST.get("tax", "0") or "0")

            if not discount.is_finite() or not tax.is_finite():
                raise InvalidOperation

        except (InvalidOperation, TypeError, ValueError):
            messages.error(request, "Enter valid discount and tax values.")
            return redirect("sale_edit", pk=pk)

        if discount < 0 or tax < 0:
            messages.error(request, "Discount and tax cannot be negative.")
            return redirect("sale_edit", pk=pk)

        if discount_type not in ("PERCENTAGE", "AMOUNT"):
            messages.error(request, "Invalid discount type.")
            return redirect("sale_edit", pk=pk)

        if payment_method not in ("CASH", "CARD", "UPI", "OTHER"):
            messages.error(request, "Invalid payment method.")
            return redirect("sale_edit", pk=pk)

        customer = None
        if customer_id:
            try:
                customer = Customer.objects.get(
                    pk=int(customer_id),
                    is_active=True,
                )
            except (Customer.DoesNotExist, ValueError, TypeError):
                messages.error(request, "Please select a valid customer.")
                return redirect("sale_edit", pk=pk)

        product_ids = request.POST.getlist("product_ids")
        quantities = request.POST.getlist("quantities")

        if not product_ids or len(product_ids) != len(quantities):
            messages.error(request, "Please add at least one product.")
            return redirect("sale_edit", pk=pk)

        cart = defaultdict(int)

        try:
            for product_id, quantity in zip(product_ids, quantities):
                product_id = int(product_id)
                quantity = int(quantity)

                if product_id <= 0 or quantity <= 0:
                    raise ValueError

                cart[product_id] += quantity

        except (ValueError, TypeError):
            messages.error(request, "Invalid product or quantity.")
            return redirect("sale_edit", pk=pk)

        try:
            with transaction.atomic():
                locked_sale = Sale.objects.select_for_update().get(pk=pk)

                old_items = list(
                    SaleItem.objects.filter(sale=locked_sale)
                    .select_related("product")
                )

                old_quantities = defaultdict(int)
                old_prices = {}

                for item in old_items:
                    old_quantities[item.product_id] += item.quantity

                    # Preserve the original invoice price and cost.
                    if item.product_id not in old_prices:
                        old_prices[item.product_id] = {
                            "unit_price": item.unit_price,
                            "cost_price": item.cost_price,
                        }

                all_product_ids = sorted(
                    set(cart.keys()) | set(old_quantities.keys())
                )

                locked_products = {
                    product.pk: product
                    for product in Product.objects.select_for_update()
                    .filter(pk__in=all_product_ids)
                    .order_by("pk")
                }

                if len(locked_products) != len(all_product_ids):
                    messages.error(
                        request,
                        "One or more products no longer exist.",
                    )
                    return redirect("sale_edit", pk=pk)

                new_items = []
                subtotal = Decimal("0.00")

                for product_id, quantity in cart.items():
                    product = locked_products[product_id]

                    # The current stock excludes this invoice's sold items.
                    available_stock = (
                        product.stock + old_quantities.get(product_id, 0)
                    )

                    if quantity > available_stock:
                        messages.error(
                            request,
                            f"Insufficient stock for {product.name}. "
                            f"Available for this invoice: {available_stock}.",
                        )
                        return redirect("sale_edit", pk=pk)

                    # Keep the original selling price for existing invoice
                    # products. Use the current price for newly added products.
                    if product_id in old_prices:
                        unit_price = old_prices[product_id]["unit_price"]
                        cost_price = old_prices[product_id]["cost_price"]
                    else:
                        unit_price = product.price
                        cost_price = product.cost_price

                    unit_price = Decimal(str(unit_price)).quantize(
                        Decimal("0.01")
                    )
                    cost_price = Decimal(str(cost_price)).quantize(
                        Decimal("0.01")
                    )

                    line_total = (unit_price * quantity).quantize(
                        Decimal("0.01")
                    )
                    subtotal += line_total

                    new_items.append({
                        "product": product,
                        "quantity": quantity,
                        "unit_price": unit_price,
                        "cost_price": cost_price,
                        "total_price": line_total,
                    })

                subtotal = subtotal.quantize(Decimal("0.01"))
                discount = discount.quantize(Decimal("0.01"))

                if discount_type == "PERCENTAGE":
                    if discount > Decimal("100"):
                        messages.error(
                            request,
                            "Percentage discount cannot exceed 100%.",
                        )
                        return redirect("sale_edit", pk=pk)

                    discount_amount = (
                        subtotal * discount / Decimal("100")
                    ).quantize(Decimal("0.01"))

                else:
                    if discount > subtotal:
                        messages.error(
                            request,
                            "Fixed discount cannot exceed the subtotal.",
                        )
                        return redirect("sale_edit", pk=pk)

                    discount_amount = discount

                tax = tax.quantize(Decimal("0.01"))
                total_amount = (
                    subtotal - discount_amount + tax
                ).quantize(Decimal("0.01"))

                # Update stock by applying the difference between the
                # previous invoice quantities and the edited quantities.
                for product_id, product in locked_products.items():
                    previous_quantity = old_quantities.get(product_id, 0)
                    new_quantity = cart.get(product_id, 0)

                    product.stock = (
                        product.stock + previous_quantity - new_quantity
                    )
                    product.save(update_fields=["stock", "updated_at"])

                locked_sale.customer = customer
                locked_sale.payment_method = payment_method
                locked_sale.discount_type = discount_type
                locked_sale.discount = discount
                locked_sale.discount_amount = discount_amount
                locked_sale.subtotal = subtotal
                locked_sale.tax = tax
                locked_sale.total_amount = total_amount
                locked_sale.save()

                SaleItem.objects.filter(sale=locked_sale).delete()

                SaleItem.objects.bulk_create([
                    SaleItem(
                        sale=locked_sale,
                        product=item["product"],
                        quantity=item["quantity"],
                        unit_price=item["unit_price"],
                        cost_price=item["cost_price"],
                        total_price=item["total_price"],
                    )
                    for item in new_items
                ])

            messages.success(
                request,
                f"Invoice {sale.invoice_number} updated successfully.",
            )
            return redirect("sale_detail", pk=sale.pk)

        except Sale.DoesNotExist:
            messages.error(request, "This invoice no longer exists.")
            return redirect("sale_list")

    # Prepare the existing invoice items for the edit form.
    initial_items = {}

    for item in sale.items.select_related("product").all():
        product_id = item.product_id

        if product_id not in initial_items:
            initial_items[product_id] = {
                "product_id": product_id,
                "name": item.product.name,
                "quantity": 0,
                "price": str(item.unit_price),
                "stock": item.product.stock,
                "sku": getattr(item.product, "sku", ""),
            }

        initial_items[product_id]["quantity"] += item.quantity
        initial_items[product_id]["stock"] = (
            item.product.stock + initial_items[product_id]["quantity"]
        )

    initial_cart = list(initial_items.values())

    context = {
        "sale": sale,
        "products": products,
        "customers": customers,
        "initial_cart": json.dumps(initial_cart),
        "edit_mode": True,
    }

    return render(request, "sales/new_sale.html", context)
