from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render

from .models import Sale


@login_required
def sale_list(request):

    sales = (
        Sale.objects
        .select_related(
            "customer",
            "created_by",
        )
        .prefetch_related(
            "items__product",
        )
        .order_by("-created_at")
    )

    # =========================================
    # PAGINATION
    # =========================================

    paginator = Paginator(
        sales,
        10,
    )

    page_number = request.GET.get(
        "page",
        1,
    )

    page_obj = paginator.get_page(
        page_number
    )

    return render(
        request,
        "sales/sale_list.html",
        {
            "sales": page_obj,
            "page_obj": page_obj,
            "paginator": paginator,
        },
    )