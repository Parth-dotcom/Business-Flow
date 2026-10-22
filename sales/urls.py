
from django.urls import path

from .sale_list_view import sale_list
from .sale_search import sale_search
from .whatsapp import sale_whatsapp
from .views import (
    sale_detail,
    sale_pdf,
    sale_delete,
    new_sale,
    sale_edit,
)


urlpatterns = [
    path(
        "",
        sale_list,
        name="sale_list",
    ),
    path(
        "search/",
        sale_search,
        name="sale_search",
    ),
    path(
        "new/",
        new_sale,
        name="new_sale",
    ),
    path(
        "<int:pk>/edit/",
        sale_edit,
        name="sale_edit",
    ),
    path(
        "<int:pk>/",
        sale_detail,
        name="sale_detail",
    ),
    path(
        "<int:pk>/pdf/",
        sale_pdf,
        name="sale_pdf",
    ),
    path(
        "<int:pk>/delete/",
        sale_delete,
        name="sale_delete",
    ),
    path(
        "<int:pk>/whatsapp/",
        sale_whatsapp,
        name="sale_whatsapp",
    ),
]
