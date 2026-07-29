# Destination: umlm/urls.py  (replace the whole file)
# NOTE: this one was already correct in your last paste — included here
# just so you have the full matching set together.
from django.contrib import admin
from django.urls import path, include
from core.views import dashboard_page, select_user_view, logout_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('core.urls')),
    path('logout/', logout_view, name='logout'),
    path('dashboard/', dashboard_page, name='dashboard'),
    path('', select_user_view, name='select_user'),
]
