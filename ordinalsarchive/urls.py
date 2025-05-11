"""
URL configuration for ordinalsarchive project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path

from pages import views


urlpatterns = [
    path("", views.index),
    path("block/<str:block_identifier>", views.block),
    path("context/<int:context_id>", views.context),
    path("context/revision/<int:context_id>", views.context_revision),
    path("content_types", views.content_types),
    path("lit", views.lit),
    path("bit", views.bit),
    path("media/<str:filename>", views.media),
    path("admin/", admin.site.urls),
]
