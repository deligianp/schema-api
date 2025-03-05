"""schema_api URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
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
from django.urls import path, include
from drf_spectacular.views import SpectacularSwaggerView, SpectacularAPIView

from django.conf import settings

urlpatterns = [
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    # Optional UI:
    path('api/workflows', include('workflows.urls')),
    path('api/', include('api.urls')),
    path('admin/', admin.site.urls),
    path('monitor/', include('monitor.urls')),
    path('reproducibility/', include('experiments.urls')),
    path('', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

if settings.USE_AUTH:
    urlpatterns.insert(-1, path('api_auth/', include('api_auth.urls')))

if settings.USE_FILES:
    urlpatterns.insert(-1, path('storage/', include('files.urls')))
