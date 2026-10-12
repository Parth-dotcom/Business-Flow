from django.urls import path

from .views import (
    product_list,
    product_detail,
    product_create,
    product_edit,
    product_delete,
    category_list,
    category_create,
    category_edit,
    category_delete,
)


urlpatterns = [
    path(
        "",
        product_list,
        name="product_list",
    ),

    path(
        "categories/",
        category_list,
        name="category_list",
    ),

    path(
        "categories/add/",
        category_create,
        name="category_create",
    ),

    path(
        "categories/<int:pk>/edit/",
        category_edit,
        name="category_edit",
    ),

    path(
        "categories/<int:pk>/delete/",
        category_delete,
        name="category_delete",
    ),

    path(
        "add/",
        product_create,
        name="product_create",
    ),

    path(
        "<int:pk>/",
        product_detail,
        name="product_detail",
    ),

    path(
        "<int:pk>/edit/",
        product_edit,
        name="product_edit",
    ),

    path(
        "<int:pk>/delete/",
        product_delete,
        name="product_delete",
    ),
]