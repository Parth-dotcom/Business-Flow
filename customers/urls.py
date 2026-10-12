from django.urls import path

from .views import (
    customer_list,
    customer_create,
    customer_edit,
    customer_detail,
    customer_delete,
)

from .quick_create import quick_create_customer


urlpatterns = [

    path(
        "",
        customer_list,
        name="customer_list",
    ),

    path(
        "add/",
        customer_create,
        name="customer_create",
    ),

    path(
        "quick-create/",
        quick_create_customer,
        name="quick_create_customer",
    ),

    path(
        "<int:pk>/",
        customer_detail,
        name="customer_detail",
    ),

    path(
        "<int:pk>/edit/",
        customer_edit,
        name="customer_edit",
    ),

    path(
        "<int:pk>/delete/",
        customer_delete,
        name="customer_delete",
    ),
]