from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('create/', views.create_game, name='create_game'),
    path('join/', views.join_game, name='join_game'),
    path('lobby/<str:game_code>/', views.lobby, name='lobby'),
    path('play/<str:game_code>/', views.play, name='play'),
    path('leave/<str:game_code>/', views.leave_game, name='leave_game'),
]
