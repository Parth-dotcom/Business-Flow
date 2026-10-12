from django.contrib.auth.decorators import login_required
from django.core.validators import validate_email
from django.http import JsonResponse
from django.core.exceptions import ValidationError

from .models import Customer


@login_required
def quick_create_customer(request):

    if request.method != "POST":
        return JsonResponse(
            {
                "success": False,
                "message": "Invalid request method.",
            },
            status=405,
        )

    name = request.POST.get("name", "").strip()
    phone = request.POST.get("phone", "").strip()
    email = request.POST.get("email", "").strip()
    address = request.POST.get("address", "").strip()
    city = request.POST.get("city", "").strip()

    # =========================================
    # NAME VALIDATION
    # =========================================

    if not name:
        return JsonResponse(
            {
                "success": False,
                "message": "Customer name is required.",
            },
            status=400,
        )

    # =========================================
    # PHONE VALIDATION
    # =========================================

    if not phone:
        return JsonResponse(
            {
                "success": False,
                "message": "Phone number is required.",
            },
            status=400,
        )

    if len(phone) > 15:
        return JsonResponse(
            {
                "success": False,
                "message": "Phone number cannot be longer than 15 characters.",
            },
            status=400,
        )

    # =========================================
    # DUPLICATE PHONE
    # =========================================

    if Customer.objects.filter(phone=phone).exists():

        existing_customer = (
            Customer.objects
            .filter(phone=phone)
            .first()
        )

        return JsonResponse(
            {
                "success": False,
                "message": (
                    f"This phone number is already registered "
                    f"for {existing_customer.name}."
                ),
            },
            status=400,
        )

    # =========================================
    # EMAIL VALIDATION
    # =========================================

    if email:

        try:
            validate_email(email)

        except ValidationError:

            return JsonResponse(
                {
                    "success": False,
                    "message": "Please enter a valid email address.",
                },
                status=400,
            )

    # =========================================
    # CREATE CUSTOMER
    # =========================================

    customer = Customer.objects.create(
        name=name,
        phone=phone,
        email=email,
        address=address,
        city=city,
        is_active=True,
    )

    return JsonResponse(
        {
            "success": True,
            "message": "Customer created successfully.",
            "customer": {
                "id": customer.id,
                "name": customer.name,
                "phone": customer.phone,
                "email": customer.email,
                "address": customer.address,
                "city": customer.city,
            },
        }
    )
