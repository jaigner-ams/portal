from django.urls import path

from . import views

app_name = "restorations"

urlpatterns = [
    path("api/options/", views.restoration_type_options, name="options"),
    path("api/products/", views.material_products, name="material-products"),
    path("api/implant-sizes/", views.implant_sizes, name="implant-sizes"),
]
