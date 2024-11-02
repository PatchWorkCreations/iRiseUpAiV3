from . import views
from django.urls import path

urlpatterns = [
    path("", views.index, name='index'),
    path('contact/', views.contact, name='contact'),

    path('password_reset/', views.CustomPasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', views.CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', views.custom_password_reset_confirm, name='password_reset_confirm'),
    path('reset/done/', views.CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path('change-password/', views.CustomPasswordChangeView.as_view(), name='password_change'),
    path('change-password/done/', views.CustomPasswordChangeDoneView.as_view(), name='password_change_done'),
    
    path('password-reset/invalid/', views.password_reset_invalid_link, name='password_reset_invalid_link'),

    path('sign_in', views.sign_in, name='sign_in'),
    path('sign_out/', views.sign_out, name='sign_out'),
]