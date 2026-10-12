from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("admin/", admin.site.urls),

    path("accounts/", include("accounts.urls")),

    path("products/", include("products.urls")),

    path("customers/", include("customers.urls")),

    path("sales/", include("sales.urls")),

    path("expenses/", include("expenses.urls")),

    path("", include("reports.urls")),
]