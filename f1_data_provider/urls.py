# urls.py
from django.contrib import admin
from django.urls import path, re_path, include
from django.http import HttpResponse
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi


def default_view(request):
    return HttpResponse("Welcome to f1_data_provider!")


schema_view = get_schema_view(
    openapi.Info(
        title="f1_data_provider API",
        default_version='v1',
        description="API description for f1_data_provider",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('lap_comparison.urls')),
    path('', default_view),
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]
