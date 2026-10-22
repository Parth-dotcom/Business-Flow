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
from products.models import Product, ProductSize
from .models import Sale, SaleItem


# =========================================================
# DELETE SALE
# =========================================================

@login_required
def sale_delete(request, pk):
    sale = get_object_or_404(
        Sale.objects.prefetch_related("items__product", "items__product_size"),
        pk=pk,
    )

    if request.method == "POST":
        with transaction.atomic():
            for item in sale.items.select_related("product", "product_size").all():
                product = Product.objects.select_for_update().get(pk=item.product_id)
                if item.product_size_id:
                    size_row = ProductSize.objects.select_for_update().get(pk=item.product_size_id)
                    size_row.stock += item.quantity
                    size_row.save(update_fields=["stock"])
                product.stock += item.quantity
                product.save(update_fields=["stock", "updated_at"])
            sale.delete()

        messages.success(request, "Invoice deleted successfully and stock has been restored.")
        return redirect("sale_list")

    return render(request, "sales/sale_confirm_delete.html", {"sale": sale})


# =========================================================
# PDF FONT SETUP
# =========================================================

# Arial is used for normal invoice text when available.
FONT_PATH = "C:/Windows/Fonts/arial.ttf"
FONT_BOLD_PATH = "C:/Windows/Fonts/arialbd.ttf"

# Optional Cormorant Garamond font files for the Ananta Aura brand heading.
# Download/install these fonts and update the paths if needed.
LUXURY_FONT_PATH = "C:/Windows/Fonts/CormorantGaramond-Regular.ttf"
LUXURY_FONT_BOLD_PATH = "C:/Windows/Fonts/CormorantGaramond-SemiBold.ttf"

if os.path.exists(FONT_PATH):
    pdfmetrics.registerFont(TTFont("AnantaAuraBody", FONT_PATH))
    if os.path.exists(FONT_BOLD_PATH):
        pdfmetrics.registerFont(TTFont("AnantaAuraBodyBold", FONT_BOLD_PATH))
    else:
        pdfmetrics.registerFont(TTFont("AnantaAuraBodyBold", FONT_PATH))
    PDF_FONT = "AnantaAuraBody"
    PDF_BOLD_FONT = "AnantaAuraBodyBold"
else:
    PDF_FONT = "Helvetica"
    PDF_BOLD_FONT = "Helvetica-Bold"

if os.path.exists(LUXURY_FONT_PATH):
    pdfmetrics.registerFont(TTFont("AnantaAuraBrand", LUXURY_FONT_PATH))
    PDF_BRAND_FONT = "AnantaAuraBrand"
else:
    PDF_BRAND_FONT = PDF_BOLD_FONT

if os.path.exists(LUXURY_FONT_BOLD_PATH):
    pdfmetrics.registerFont(TTFont("AnantaAuraBrandBold", LUXURY_FONT_BOLD_PATH))
    PDF_BRAND_BOLD_FONT = "AnantaAuraBrandBold"
else:
    PDF_BRAND_BOLD_FONT = PDF_BOLD_FONT


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
        .prefetch_related(
            "items__product",
            "items__product_size",
        )
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
        .prefetch_related("items__product", "items__product_size"),
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
        Sale.objects.select_related(
            "customer",
            "created_by",
        ).prefetch_related(
            "items__product",
            "items__product_size",
        ),
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
        title=f"Ananta Aura Invoice {sale.invoice_number}",
        author="Ananta Aura",
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "AnantaAuraTitle",
        parent=styles["Normal"],
        fontName=PDF_BRAND_FONT,
        fontSize=25,
        leading=29,
        textColor=colors.HexColor("#231F20"),
    )

    address_style = ParagraphStyle(
        "AnantaAuraAddress",
        parent=styles["Normal"],
        fontName=PDF_FONT,
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#555555"),
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

    # -----------------------------------------------------
    # BRAND HEADER
    # -----------------------------------------------------

    header_data = [
        [
            Paragraph("ANANTA AURA", title_style),
            Paragraph("INVOICE", invoice_label_style),
        ],
        [
            Paragraph(
                "WOMEN'S ETHNIC WEAR<br/>"
                "Shop No. 8, 9th Avenue Building,<br/>"
                "Near Nanavati Chowk, Rajkot - 360007",
                address_style,
            ),
            Paragraph(
                f"<b>{sale.invoice_number}</b><br/>"
                f"{local_created_at.strftime('%d %b %Y, %I:%M %p')}",
                invoice_number_style,
            ),
        ],
    ]

    header_table = Table(
        header_data,
        colWidths=[105 * mm, 65 * mm],
    )

    header_table.setStyle(
        TableStyle([
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
        ])
    )

    story.append(header_table)
    story.append(Spacer(1, 7 * mm))

    # -----------------------------------------------------
    # CUSTOMER INFORMATION
    # -----------------------------------------------------

    if sale.customer:
        customer_lines = [
            f"<b>{sale.customer.name}</b>"
        ]

        if sale.customer.phone:
            customer_lines.append(
                f"Phone: {sale.customer.phone}"
            )

        if sale.customer.email:
            customer_lines.append(
                f"Email: {sale.customer.email}"
            )

        if sale.customer.city:
            customer_lines.append(
                f"City: {sale.customer.city}"
            )

        if sale.customer.address:
            customer_lines.append(
                f"Address: {sale.customer.address}"
            )

        customer_text = "<br/>".join(customer_lines)

    else:
        customer_text = "<b>Walk-in Customer</b>"

    payment_name = dict(Sale.PAYMENT_METHODS).get(
        sale.payment_method,
        sale.payment_method,
    )

    created_by_name = (
        sale.created_by.username
        if sale.created_by
        else "Admin"
    )

    customer_payment_data = [[
        Paragraph(
            "<b>Customer Information</b><br/>"
            + customer_text,
            normal_style,
        ),
        Paragraph(
            "<b>Payment Information</b><br/>"
            f"Payment Method: {payment_name}<br/>"
            f"Created By: {created_by_name}<br/>"
            f"Invoice Number: {sale.invoice_number}",
            normal_style,
        ),
    ]]

    customer_payment_table = Table(
        customer_payment_data,
        colWidths=[100 * mm, 70 * mm],
    )

    customer_payment_table.setStyle(
        TableStyle([
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
        ])
    )

    story.append(customer_payment_table)
    story.append(Spacer(1, 7 * mm))

    # -----------------------------------------------------
    # PRODUCTS — INCLUDING SIZE
    # -----------------------------------------------------

    product_rows = [[
        Paragraph("#", table_header_style),
        Paragraph("Product", table_header_style),
        Paragraph("SKU", table_header_style),
        Paragraph("Size", table_header_style),
        Paragraph("Quantity", table_header_style),
        Paragraph("Unit Price", table_header_style),
        Paragraph("Total", table_header_style),
    ]]

    sale_items = sale.items.select_related(
        "product",
        "product_size",
    ).all()

    for index, item in enumerate(sale_items, start=1):
        product_name = (
            str(item.product.name)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

        sku = (
            str(getattr(item.product, "sku", "") or "")
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

        size_name = (
            str(item.product_size.size)
            if item.product_size_id
            else "Not recorded"
        )

        product_rows.append([
            str(index),
            Paragraph(product_name, normal_style),
            Paragraph(sku, small_style),
            str(size_name),
            str(item.quantity),
            Paragraph(
                f"Rs. {item.unit_price:.2f}",
                normal_style,
            ),
            Paragraph(
                f"Rs. {item.total_price:.2f}",
                bold_style,
            ),
        ])

    product_table = Table(
        product_rows,
        colWidths=[
            7 * mm,
            39 * mm,
            22 * mm,
            19 * mm,
            17 * mm,
            30 * mm,
            29 * mm,
        ],
        repeatRows=1,
    )

    product_table.setStyle(
        TableStyle([
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
            ("ALIGN", (3, 0), (4, -1), "CENTER"),
            ("ALIGN", (5, 0), (6, -1), "RIGHT"),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ])
    )

    story.append(
        Paragraph("Products", section_title_style)
    )
    story.append(Spacer(1, 2 * mm))
    story.append(product_table)
    story.append(Spacer(1, 7 * mm))

    # -----------------------------------------------------
    # BILL SUMMARY
    # -----------------------------------------------------

    if sale.discount_type == "PERCENTAGE":
        discount_label = (
            f"Discount ({sale.discount}%)"
        )
    else:
        discount_label = "Discount (Fixed)"

    summary_rows = [
        [
            Paragraph("Subtotal", normal_style),
            Paragraph(
                f"Rs. {sale.subtotal:.2f}",
                normal_style,
            ),
        ],
        [
            Paragraph(discount_label, normal_style),
            Paragraph(
                f"- Rs. {sale.discount_amount:.2f}",
                normal_style,
            ),
        ],
        [
            Paragraph("Tax", normal_style),
            Paragraph(
                f"Rs. {sale.tax:.2f}",
                normal_style,
            ),
        ],
    ]

    summary_table = Table(
        summary_rows,
        colWidths=[130 * mm, 40 * mm],
    )

    summary_table.setStyle(
        TableStyle([
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
        ])
    )

    story.append(
        Paragraph("Bill Summary", section_title_style)
    )
    story.append(Spacer(1, 2 * mm))
    story.append(summary_table)
    story.append(Spacer(1, 3 * mm))

    grand_total_data = [[
        Paragraph(
            "<b>Grand Total</b><br/>"
            "<font size='7'>Total amount payable</font>",
            grand_total_label_style,
        ),
        Paragraph(
            f"Rs. {sale.total_amount:.2f}",
            grand_total_value_style,
        ),
    ]]

    grand_total_table = Table(
        grand_total_data,
        colWidths=[110 * mm, 60 * mm],
    )

    grand_total_table.setStyle(
        TableStyle([
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
        ])
    )

    story.append(grand_total_table)
    story.append(Spacer(1, 5 * mm))
    story.append(
        Paragraph(
            f"Payment recorded as <b>{payment_name}</b>",
            small_style,
        )
    )
    story.append(Spacer(1, 8 * mm))
    story.append(
        Paragraph(
            "Thank you for shopping with Ananta Aura.",
            small_style,
        )
    )

    document.build(story)
    return response

# =========================================================
# NEW SALE
# =========================================================

@login_required
def new_sale(request):
    customers = Customer.objects.filter(is_active=True).order_by("name")
    products = (
        Product.objects.filter(is_active=True)
        .select_related("category")
        .prefetch_related("sizes")
        .order_by("name")
    )

    def render_form():
        return render(request, "sales/new_sale.html", {"customers": customers, "products": products})

    if request.method == "POST":
        customer_id = request.POST.get("customer", "").strip()
        product_ids = request.POST.getlist("product_ids")
        product_size_ids = request.POST.getlist("product_size_ids")
        quantities = request.POST.getlist("quantities")
        discount_type = request.POST.get("discount_type", "PERCENTAGE")
        payment_method = request.POST.get("payment_method", "CASH")

        if not product_ids or len(product_ids) != len(product_size_ids) or len(product_ids) != len(quantities):
            messages.error(request, "Please add at least one product with a size and quantity.")
            return render_form()
        if discount_type not in ("PERCENTAGE", "AMOUNT"):
            messages.error(request, "Invalid discount type.")
            return render_form()
        if payment_method not in ("CASH", "CARD", "UPI", "OTHER"):
            messages.error(request, "Invalid payment method.")
            return render_form()

        customer = None
        if customer_id:
            customer = Customer.objects.filter(pk=customer_id, is_active=True).first()
            if not customer:
                messages.error(request, "Selected customer is not available.")
                return render_form()

        # Each cart line is identified by product AND size.
        cart = {}
        try:
            for product_id_raw, size_id_raw, quantity_raw in zip(product_ids, product_size_ids, quantities):
                product_id = int(product_id_raw)
                size_id = int(size_id_raw)
                quantity = int(quantity_raw)
                if product_id <= 0 or size_id <= 0 or quantity < 1:
                    raise ValueError
                key = (product_id, size_id)
                cart[key] = cart.get(key, 0) + quantity
        except (TypeError, ValueError):
            messages.error(request, "Invalid product, size, or quantity.")
            return render_form()

        try:
            discount_value = Decimal(request.POST.get("discount", "0") or "0")
            tax = Decimal(request.POST.get("tax", "0") or "0")
            if not discount_value.is_finite() or not tax.is_finite():
                raise InvalidOperation
        except (InvalidOperation, TypeError, ValueError):
            messages.error(request, "Enter valid discount and tax values.")
            return render_form()
        if discount_value < 0 or tax < 0:
            messages.error(request, "Discount and tax cannot be negative.")
            return render_form()

        with transaction.atomic():
            locked_lines = []
            subtotal = Decimal("0.00")
            for (product_id, size_id), quantity in sorted(cart.items()):
                product = Product.objects.select_for_update().filter(pk=product_id, is_active=True).first()
                size_row = ProductSize.objects.select_for_update().filter(pk=size_id, product_id=product_id).first()
                if not product or not size_row:
                    messages.error(request, "A selected product or size is no longer available. Please refresh and try again.")
                    return render_form()
                if quantity > size_row.stock:
                    messages.error(request, f"Only {size_row.stock} piece(s) of {product.name} size {size_row.size} are available.")
                    return render_form()
                line_total = (product.price * quantity).quantize(Decimal("0.01"))
                subtotal += line_total
                locked_lines.append({"product": product, "size": size_row, "quantity": quantity, "unit_price": product.price, "cost_price": product.cost_price, "total_price": line_total})

            subtotal = subtotal.quantize(Decimal("0.01"))
            if discount_type == "PERCENTAGE":
                if discount_value > 100:
                    messages.error(request, "Percentage discount cannot exceed 100%.")
                    return render_form()
                discount_amount = (subtotal * discount_value / Decimal("100")).quantize(Decimal("0.01"))
            else:
                if discount_value > subtotal:
                    messages.error(request, "Fixed discount cannot exceed the subtotal.")
                    return render_form()
                discount_amount = discount_value.quantize(Decimal("0.01"))
            tax = tax.quantize(Decimal("0.01"))
            total_amount = (subtotal - discount_amount + tax).quantize(Decimal("0.01"))

            sale = Sale.objects.create(
                invoice_number=generate_invoice_number(), customer=customer,
                created_by=request.user, subtotal=subtotal,
                discount_type=discount_type, discount=discount_value,
                discount_amount=discount_amount, tax=tax,
                total_amount=total_amount, payment_method=payment_method,
            )
            for line in locked_lines:
                SaleItem.objects.create(
                    sale=sale, product=line["product"], product_size=line["size"],
                    quantity=line["quantity"], unit_price=line["unit_price"],
                    cost_price=line["cost_price"], total_price=line["total_price"],
                )
                line["size"].stock -= line["quantity"]
                line["size"].save(update_fields=["stock"])
                line["product"].stock -= line["quantity"]
                line["product"].save(update_fields=["stock", "updated_at"])

        messages.success(request, f"Sale {sale.invoice_number} created successfully.")
        return redirect("sale_list")

    return render_form()



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
