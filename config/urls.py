from django.contrib.auth import views as auth_views
from django.urls import include, path
from projects.views import ThrottledLoginView
from projects.health import health

urlpatterns = [
    path('healthz/', health, name='health'),
    path('accounts/login/', ThrottledLoginView.as_view(), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('', include('projects.urls')),
]
