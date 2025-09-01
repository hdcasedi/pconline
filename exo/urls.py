from django.urls import path
from . import views

app_name = "exo"
urlpatterns = [
    path("rescan-parent/<int:page_id>/", views.rescan_parent, name="rescan_parent"),
    path("param-config/<int:param_id>/", views.param_config, name="param_config"),
    path("param-sync/<int:param_id>/", views.param_sync, name="param_sync"),
    path("param-name/<int:param_id>/", views.param_name, name="param_name"),
    path("param-field/<int:param_id>/", views.param_field, name="param_field"),
    path("validate-params/<int:page_id>/", views.validate_params, name="validate_params"),
    path("test-content/<int:page_id>/", views.test_content_extraction, name="test_content"),
    path("ping/", views.ping, name="ping"),
]
