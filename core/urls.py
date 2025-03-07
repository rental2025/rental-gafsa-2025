from django.urls import path
from . import views

urlpatterns = [
    path('setup/', views.run_migrations_and_superuser, name='setup'),
    path('', views.reservation_create, name='reservation_create'),
    path('reservation/<int:reservation_id>/', views.reservation_detail, name='reservation_detail'),
    path('reservation/<int:reservation_id>/confirm/', views.confirm_reservation, name='confirm_reservation'),
    path('reservation/<int:reservation_id>/discount/', views.apply_discount, name='apply_discount'),
    path('reservation/<int:reservation_id>/pay/', views.confirm_payment, name='confirm_payment'),  # Vérifié ici
    path('trip/<int:reservation_id>/create/', views.create_trip, name='create_trip'),
    path('trip/<int:trip_id>/order/', views.transport_order, name='transport_order'),
    path('calendar/events/', views.calendar_events, name='calendar_events'),
    path('dashboard/', views.dashboard, name='dashboard'),
]