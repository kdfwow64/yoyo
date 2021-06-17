from django.conf.urls import url
from django.contrib import admin
from django.urls import include, path
from rest_framework_swagger.views import get_swagger_view

schema_view = get_swagger_view(title='API Documentation')

# urls
urlpatterns = [
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('api/documentation/', schema_view),
    path('api/locations/', include('locations.urls')),
    path('api/auth/', include('authentication.urls')),
    path('admin/', admin.site.urls),
]
