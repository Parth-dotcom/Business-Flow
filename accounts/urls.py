from django.urls import path
from .views import BusinessFlowLoginView


urlpatterns = [
    path("login/", BusinessFlowLoginView.as_view(), name="login"),
]