from django.contrib import admin
from django.urls import path, include


urlpatterns = [
    path('avocado/', admin.site.urls),
    path('', include('members.urls'))
]
