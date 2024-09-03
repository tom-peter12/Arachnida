from django.urls import path
from .views import home, spider

urlpatterns = [
    path('', home, name='home page'),
	path('spider/', spider, name='spider')
]