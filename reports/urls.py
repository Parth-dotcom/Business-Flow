
from django.urls import path

from .views import (
    dashboard,
    sales_report,
    inventory_report,
    monthly_profit_loss_report,
)

urlpatterns = [
    path(
        "",
        dashboard,
        name="dashboard",
    ),

    path(
        "reports/sales/",
        sales_report,
        name="sales_report",
    ),

    path(
        "reports/inventory/",
        inventory_report,
        name="inventory_report",
    ),

    path(
        "reports/monthly-profit-loss/",
        monthly_profit_loss_report,
        name="monthly_profit_loss_report",
    ),
]
