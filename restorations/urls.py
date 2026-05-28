from django.urls import path

from . import views

app_name = "restorations"

urlpatterns = [
    path("", views.restoration_add, name="case-new"),
    path("orders/", views.orders, name="orders"),
    path("case/<int:pk>/", views.case_detail, name="case-detail"),
    path("<int:pk>/cancel/", views.cancel_restoration, name="cancel-restoration"),
    path("api/options/", views.restoration_type_options, name="options"),
    path("api/products/", views.material_products, name="material-products"),
    path("api/implant-sizes/", views.implant_sizes, name="implant-sizes"),
]
