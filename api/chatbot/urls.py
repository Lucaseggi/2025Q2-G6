from django.urls import path
from . import views

app_name = 'chatbot'

urlpatterns = [
    path('ask/', views.ask_question, name='ask_question'),
]