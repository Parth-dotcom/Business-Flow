from django.urls import path

from .views import BusinessFlowLoginView, businessflow_logout


urlpatterns = [
    path("login/", BusinessFlowLoginView.as_view(), name="login"),
    path("logout/", businessflow_logout, name="logout"),
]