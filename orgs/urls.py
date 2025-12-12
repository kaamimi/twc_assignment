from django.urls import path
from . import views

urlpatterns = [
    path('org/create', views.create_organization, name='create_organization'),
    path('org/get', views.get_organization, name='get_organization'),
    path('org/update', views.update_organization, name='update_organization'),
    path('org/delete', views.delete_organization, name='delete_organization'),
    path('admin/login', views.admin_login, name='admin_login'),
]