from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('projects/new/', views.project_form, name='project_create'),
    path('projects/<int:pk>/', views.project_detail, name='project'),
    path('projects/<int:pk>/edit/', views.project_form, name='project_edit'),
    path('drawings/<uuid:pk>/', views.drawing_detail, name='drawing'),
    path('drawings/<uuid:pk>/objects/<str:handle>/', views.decision_edit, name='decision'),
    path('drawings/<uuid:pk>/run/', views.run_takeoff, name='run'),
    path('drawings/<uuid:pk>/original/', views.original, name='original'),
    path('jobs/<uuid:pk>/', views.job_detail, name='job'),
    path('jobs/<uuid:pk>/retry/', views.retry_job, name='retry'),
    path('jobs/<uuid:pk>/files/<str:name>/', views.artifact, name='artifact'),
]
