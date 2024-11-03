from django.urls import path
from . import views

urlpatterns = [
    path('', views.personalized_plan, name='personalized_plan'),
    path('set-selected-plan/', views.setSelectedPlanInSession, name='set_selected_plan'),
    path('process-payment/', views.process_payment, name='process_payment'),
    path('grant-service-access/', views.grant_service_access, name='grant_service_access'),
    path('course-menu/', views.coursemenu, name='course_menu'),
]
