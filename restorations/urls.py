from django.urls import path

from . import views

app_name = "restorations"

urlpatterns = [
    path("", views.restoration_add, name="case-new"),
    path("case/<int:pk>/", views.case_detail, name="case-detail"),
    path("api/options/", views.restoration_type_options, name="options"),
    path("api/products/", views.material_products, name="material-products"),
    path("api/implant-sizes/", views.implant_sizes, name="implant-sizes"),
]
