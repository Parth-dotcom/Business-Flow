from datetime import datetime, time, timedelta
from decimal import Decimal
from expenses.services import generate_recurring_expenses

from django.contrib.auth.decorators import login_required
from django.db.models import (
    Sum,
    F,
    Count,
    DecimalField,
    ExpressionWrapper,
)
from django.shortcuts import render
from django.utils import timezone

from customers.models import Customer
from products.models import Product
from sales.models import Sale, SaleItem
from expenses.models import Expense


ZERO = Decimal("0.00")


# =========================================================
# SHARED FINANCIAL HELPERS
# =========================================================

def calculate_profit(sales_queryset):
    """
    Estimated profit before operating expenses:
    subtotal - discounts - cost of goods sold.
    Tax and operating expenses are excluded.
    """
    totals = sales_queryset.aggregate(
        subtotal=Sum("subtotal"),
        discount=Sum("discount_amount"),
    )

    cost_data = SaleItem.objects.filter(
        sale__in=sales_queryset
    ).aggregate(
        total_cost=Sum(
            ExpressionWrapper(
                F("cost_price") * F("quantity"),
                output_field=DecimalField(
                    max_digits=16,
                    decimal_places=2,
                ),
            )
        )
    )

    subtotal = totals["subtotal"] or ZERO
    discount = totals["discount"] or ZERO
    cost = cost_data["total_cost"] or ZERO

    return (subtotal - discount - cost).quantize(ZERO)


def get_monthly_financial_data(year):
    """
    Return monthly sales, product costs, expenses,
    estimated profit before expenses, and net profit.
    """
    monthly_data = []
    generate_recurring_expenses()

    for month in range(1, 13):
        month_start = datetime(year, month, 1)

        if month == 12:
            next_month_start = datetime(year + 1, 1, 1)
        else:
            next_month_start = datetime(year, month + 1, 1)

        if timezone.is_naive(month_start):
            month_start = timezone.make_aware(month_start)

        if timezone.is_naive(next_month_start):
            next_month_start = timezone.make_aware(
                next_month_start
            )

        month_sales = Sale.objects.filter(
            created_at__gte=month_start,
            created_at__lt=next_month_start,
        )

        totals = month_sales.aggregate(
            sales_total=Sum("total_amount"),
            subtotal=Sum("subtotal"),
            discount=Sum("discount_amount"),
        )

        cost_data = SaleItem.objects.filter(
            sale__in=month_sales
        ).aggregate(
            total_cost=Sum(
                ExpressionWrapper(
                    F("cost_price") * F("quantity"),
                    output_field=DecimalField(
                        max_digits=16,
                        decimal_places=2,
                    ),
                )
            )
        )

        monthly_expenses = Expense.objects.filter(
            expense_date__year=year,
            expense_date__month=month,
        ).aggregate(
            total=Sum("amount")
        )["total"] or ZERO

        sales_total = totals["sales_total"] or ZERO
        subtotal = totals["subtotal"] or ZERO
        discount = totals["discount"] or ZERO
        product_cost = cost_data["total_cost"] or ZERO

        net_sales = subtotal - discount

        estimated_profit = (
            net_sales - product_cost
        ).quantize(ZERO)

        estimated_net_profit = (
            estimated_profit - monthly_expenses
        ).quantize(ZERO)

        if net_sales > 0:
            profit_margin = (
                estimated_profit / net_sales * Decimal("100")
            ).quantize(ZERO)

            net_profit_margin = (
                estimated_net_profit / net_sales
                * Decimal("100")
            ).quantize(ZERO)
        else:
            profit_margin = ZERO
            net_profit_margin = ZERO

        monthly_data.append({
            "month_number": month,
            "month": datetime(year, month, 1).strftime("%b"),
            "month_name": datetime(
                year, month, 1
            ).strftime("%B"),
            "invoice_count": month_sales.count(),
            "sales": sales_total,
            "total": float(sales_total),
            "subtotal": subtotal,
            "discount": discount,
            "net_sales": net_sales,
            "cost": product_cost,
            "profit": estimated_profit,
            "expenses": monthly_expenses,
            "net_profit": estimated_net_profit,
            "profit_margin": profit_margin,
            "net_profit_margin": net_profit_margin,
        })

    return monthly_data


def get_date_range(start_date, end_date):
    """
    Convert optional YYYY-MM-DD date filters into an inclusive
    start and exclusive end datetime range.
    """
    start_datetime = None
    end_datetime = None

    if start_date:
        try:
            parsed_start = datetime.strptime(
                start_date, "%Y-%m-%d"
            ).date()

            start_datetime = timezone.make_aware(
                datetime.combine(parsed_start, time.min)
            )
        except ValueError:
            start_date = ""

    if end_date:
        try:
            parsed_end = datetime.strptime(
                end_date, "%Y-%m-%d"
            ).date()

            end_datetime = timezone.make_aware(
                datetime.combine(
                    parsed_end + timedelta(days=1),
                    time.min,
                )
            )
        except ValueError:
            end_date = ""

    return start_datetime, end_datetime, start_date, end_date


# =========================================================
# DASHBOARD
# =========================================================


@login_required
def dashboard(request):
    today = timezone.localdate()

    start_of_day = timezone.make_aware(
        datetime.combine(today, time.min)
    )
    start_of_next_day = start_of_day + timedelta(days=1)

    # TODAY'S SALES
    today_sales_queryset = Sale.objects.filter(
        created_at__gte=start_of_day,
        created_at__lt=start_of_next_day,
    )

    today_sales = (
        today_sales_queryset.aggregate(
            total=Sum("total_amount")
        )["total"]
        or ZERO
    )

    # ALL-TIME SALES
    total_sales = (
        Sale.objects.aggregate(
            total=Sum("total_amount")
        )["total"]
        or ZERO
    )

    today_invoice_count = today_sales_queryset.count()
    total_customers = Customer.objects.count()

    # LOW STOCK COUNTS
    low_stock_count = Product.objects.filter(
        is_active=True,
        stock__lte=F("low_stock_limit"),
    ).count()

    # LOW-STOCK AND OUT-OF-STOCK PRODUCTS FOR THE DASHBOARD
    stock_alert_products = (
        Product.objects.filter(
            is_active=True,
            stock__lte=F("low_stock_limit"),
        )
        .select_related("category")
        .order_by("stock", "name")[:10]
    )

    # RECENT SALES
    recent_sales = (
        Sale.objects.select_related("customer")
        .prefetch_related("items__product")
        .order_by("-created_at")[:5]
    )

    # MONTHLY FINANCIAL DATA
    current_year = today.year
    monthly_sales = get_monthly_financial_data(current_year)

    # TOP CUSTOMERS
    top_customers = (
        Sale.objects.filter(customer__isnull=False)
        .values(
            "customer__id",
            "customer__name",
            "customer__phone",
        )
        .annotate(
            invoice_count=Count("id"),
            total_purchases=Sum("total_amount"),
        )
        .order_by("-total_purchases")[:5]
    )

    # INVENTORY OVERVIEW
    active_products = (
        Product.objects.filter(is_active=True)
        .annotate(
            inventory_value=ExpressionWrapper(
                F("stock") * F("price"),
                output_field=DecimalField(
                    max_digits=14,
                    decimal_places=2,
                ),
            )
        )
    )

    inventory_product_count = active_products.count()

    inventory_summary = active_products.aggregate(
        total_stock=Sum("stock"),
        total_inventory_value=Sum("inventory_value"),
    )

    inventory_total_stock = (
        inventory_summary["total_stock"] or 0
    )

    inventory_total_value = (
        inventory_summary["total_inventory_value"] or ZERO
    )

    inventory_low_stock_count = active_products.filter(
        stock__gt=0,
        stock__lte=F("low_stock_limit"),
    ).count()

    inventory_out_of_stock_count = active_products.filter(
        stock=0,
    ).count()

    # PROFIT BEFORE OPERATING EXPENSES
    today_profit = calculate_profit(today_sales_queryset)
    total_profit = calculate_profit(Sale.objects.all())

    # TODAY'S RECORDED BUSINESS EXPENSES
    today_expenses = (
        Expense.objects.filter(
            expense_date=today
        ).aggregate(
            total=Sum("amount")
        )["total"]
        or ZERO
    )

    # ALL-TIME RECORDED BUSINESS EXPENSES
    total_expenses = (
        Expense.objects.aggregate(
            total=Sum("amount")
        )["total"]
        or ZERO
    )

    # ESTIMATED NET PROFIT AFTER RECORDED EXPENSES
    today_net_profit = (
        today_profit - today_expenses
    ).quantize(ZERO)

    estimated_net_profit = (
        total_profit - total_expenses
    ).quantize(ZERO)

    # NET SALES AND PROFIT MARGINS
    total_net_sales = Sale.objects.aggregate(
        subtotal=Sum("subtotal"),
        discount=Sum("discount_amount"),
    )

    net_sales = (
        (total_net_sales["subtotal"] or ZERO)
        - (total_net_sales["discount"] or ZERO)
    )

    if net_sales > 0:
        profit_margin = (
            total_profit / net_sales * Decimal("100")
        ).quantize(ZERO)

        net_profit_margin = (
            estimated_net_profit
            / net_sales
            * Decimal("100")
        ).quantize(ZERO)
    else:
        profit_margin = ZERO
        net_profit_margin = ZERO

    # DASHBOARD CONTEXT
    context = {
        "today_sales": today_sales,
        "total_sales": total_sales,
        "today_invoice_count": today_invoice_count,

        "today_profit": today_profit,
        "total_profit": total_profit,
        "profit_margin": profit_margin,

        "today_expenses": today_expenses,
        "total_expenses": total_expenses,
        "today_net_profit": today_net_profit,
        "estimated_net_profit": estimated_net_profit,
        "net_profit_margin": net_profit_margin,

        "total_customers": total_customers,
        "top_customers": top_customers,
        "low_stock_count": low_stock_count,
        "stock_alert_products": stock_alert_products,
        "recent_sales": recent_sales,

        "monthly_sales": monthly_sales,
        "monthly_financial_data": monthly_sales,

        "inventory_product_count": inventory_product_count,
        "inventory_total_stock": inventory_total_stock,
        "inventory_total_value": inventory_total_value,
        "inventory_low_stock_count": inventory_low_stock_count,
        "inventory_out_of_stock_count": inventory_out_of_stock_count,
    }

    return render(
        request,
        "dashboard/dashboard.html",
        context,
    )


# =========================================================
# SALES REPORT
# =========================================================

@login_required
def sales_report(request):
    sales = (
        Sale.objects.select_related("customer", "created_by")
        .prefetch_related("items__product")
        .order_by("-created_at")
    )

    start_date = request.GET.get("start_date", "")
    end_date = request.GET.get("end_date", "")

    start_datetime, end_datetime, start_date, end_date = (
        get_date_range(start_date, end_date)
    )

    if start_datetime:
        sales = sales.filter(
            created_at__gte=start_datetime
        )

    if end_datetime:
        sales = sales.filter(
            created_at__lt=end_datetime
        )

    report_totals = sales.aggregate(
        total_sales=Sum("total_amount"),
        total_subtotal=Sum("subtotal"),
        total_discount=Sum("discount_amount"),
        total_tax=Sum("tax"),
    )

    total_sales_amount = report_totals["total_sales"] or ZERO
    total_subtotal = report_totals["total_subtotal"] or ZERO
    total_discount = report_totals["total_discount"] or ZERO
    total_tax = report_totals["total_tax"] or ZERO

    invoice_count = sales.count()

    payment_breakdown = []

    payment_methods = [
        ("CASH", "Cash"),
        ("CARD", "Card"),
        ("UPI", "UPI"),
        ("OTHER", "Other"),
    ]

    for payment_code, payment_name in payment_methods:
        payment_data = sales.filter(
            payment_method=payment_code
        ).aggregate(
            total=Sum("total_amount"),
            invoices=Count("id"),
        )

        payment_breakdown.append({
            "code": payment_code,
            "name": payment_name,
            "total": payment_data["total"] or ZERO,
            "invoices": payment_data["invoices"],
        })

    product_breakdown = (
        SaleItem.objects.filter(sale__in=sales)
        .values(
            "product__id",
            "product__name",
            "product__sku",
        )
        .annotate(
            quantity_sold=Sum("quantity"),
            sales_amount=Sum("total_price"),
            invoice_count=Count("sale", distinct=True),
        )
        .order_by("-sales_amount", "product__name")
    )

    category_breakdown = (
        SaleItem.objects.filter(sale__in=sales)
        .values(
            "product__category__id",
            "product__category__name",
        )
        .annotate(
            quantity_sold=Sum("quantity"),
            sales_amount=Sum("total_price"),
            invoice_count=Count("sale", distinct=True),
        )
        .order_by(
            "-sales_amount",
            "product__category__name",
        )
    )

    customer_breakdown = (
        sales.values(
            "customer__id",
            "customer__name",
            "customer__phone",
        )
        .annotate(
            invoice_count=Count("id"),
            total_purchases=Sum("total_amount"),
        )
        .order_by("-total_purchases")
    )

    report_profit = calculate_profit(sales)

    context = {
        "sales": sales,
        "total_sales_amount": total_sales_amount,
        "total_subtotal": total_subtotal,
        "total_discount": total_discount,
        "total_tax": total_tax,
        "invoice_count": invoice_count,
        "start_date": start_date,
        "end_date": end_date,
        "payment_breakdown": payment_breakdown,
        "product_breakdown": product_breakdown,
        "category_breakdown": category_breakdown,
        "customer_breakdown": customer_breakdown,
        "report_profit": report_profit,
    }

    return render(
        request,
        "reports/sales_report.html",
        context,
    )


# =========================================================
# INVENTORY REPORT
# =========================================================

@login_required
def inventory_report(request):
    stock_status = request.GET.get(
        "stock_status", "all"
    ).strip().lower()

    valid_statuses = {
        "all",
        "in_stock",
        "low_stock",
        "out_of_stock",
    }

    if stock_status not in valid_statuses:
        stock_status = "all"

    products = (
        Product.objects.filter(is_active=True)
        .select_related("category")
        .annotate(
            inventory_value=ExpressionWrapper(
                F("stock") * F("price"),
                output_field=DecimalField(
                    max_digits=14,
                    decimal_places=2,
                ),
            )
        )
    )

    if stock_status == "in_stock":
        products = products.filter(
            stock__gt=F("low_stock_limit")
        )

    elif stock_status == "low_stock":
        products = products.filter(
            stock__gt=0,
            stock__lte=F("low_stock_limit"),
        )

    elif stock_status == "out_of_stock":
        products = products.filter(stock=0)

    products = products.order_by("name")

    total_products = products.count()

    stock_summary = products.aggregate(
        total_stock=Sum("stock"),
        total_inventory_value=Sum("inventory_value"),
    )

    total_stock = stock_summary["total_stock"] or 0

    total_inventory_value = (
        stock_summary["total_inventory_value"] or ZERO
    )

    low_stock_count = products.filter(
        stock__lte=F("low_stock_limit"),
        stock__gt=0,
    ).count()

    out_of_stock_count = products.filter(
        stock=0
    ).count()

    context = {
        "products": products,
        "total_products": total_products,
        "total_stock": total_stock,
        "total_inventory_value": total_inventory_value,
        "low_stock_count": low_stock_count,
        "out_of_stock_count": out_of_stock_count,
        "stock_status": stock_status,
    }

    return render(
        request,
        "reports/inventory_report.html",
        context,
    )


# =========================================================
# MONTHLY PROFIT & LOSS REPORT
# =========================================================

@login_required
def monthly_profit_loss_report(request):
    today = timezone.localdate()
    current_year = today.year

    try:
        selected_year = int(
            request.GET.get("year", current_year)
        )

        if selected_year < 2000 or selected_year > current_year + 1:
            selected_year = current_year

    except (TypeError, ValueError):
        selected_year = current_year

    monthly_data = get_monthly_financial_data(selected_year)

    yearly_sales = sum(
        (row["sales"] for row in monthly_data),
        ZERO,
    )

    yearly_subtotal = sum(
        (row["subtotal"] for row in monthly_data),
        ZERO,
    )

    yearly_discount = sum(
        (row["discount"] for row in monthly_data),
        ZERO,
    )

    yearly_net_sales = yearly_subtotal - yearly_discount

    yearly_cost = sum(
        (row["cost"] for row in monthly_data),
        ZERO,
    )

    # Profit before business operating expenses.
    yearly_profit = (
        yearly_net_sales - yearly_cost
    ).quantize(ZERO)

    # Total recorded operating expenses for the selected year.
    yearly_expenses = sum(
        (row["expenses"] for row in monthly_data),
        ZERO,
    ).quantize(ZERO)

    # Estimated net profit after recorded expenses.
    yearly_net_profit = (
        yearly_profit - yearly_expenses
    ).quantize(ZERO)

    yearly_invoice_count = sum(
        row["invoice_count"] for row in monthly_data
    )

    if yearly_net_sales > 0:
        yearly_profit_margin = (
            yearly_profit / yearly_net_sales * Decimal("100")
        ).quantize(ZERO)

        yearly_net_profit_margin = (
            yearly_net_profit / yearly_net_sales
            * Decimal("100")
        ).quantize(ZERO)
    else:
        yearly_profit_margin = ZERO
        yearly_net_profit_margin = ZERO

    current_month_data = next(
        (
            row for row in monthly_data
            if row["month_number"] == today.month
        ),
        None,
    )

    available_years = list(
        range(current_year, max(1999, current_year - 9), -1)
    )

    context = {
        "monthly_data": monthly_data,
        "selected_year": selected_year,
        "current_year": current_year,
        "available_years": available_years,
        "yearly_sales": yearly_sales,
        "yearly_subtotal": yearly_subtotal,
        "yearly_discount": yearly_discount,
        "yearly_net_sales": yearly_net_sales,
        "yearly_cost": yearly_cost,
        "yearly_profit": yearly_profit,
        "yearly_expenses": yearly_expenses,
        "yearly_net_profit": yearly_net_profit,
        "yearly_invoice_count": yearly_invoice_count,
        "yearly_profit_margin": yearly_profit_margin,
        "yearly_net_profit_margin": yearly_net_profit_margin,
        "current_month_data": current_month_data,
    }

    return render(
        request,
        "reports/monthly_profit_loss_report.html",
        context,
    )