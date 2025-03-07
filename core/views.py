from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from datetime import timedelta
from .models import Reservation, Trip, Driver, Bus
from .forms import ReservationForm, DiscountForm, TripForm
from django.db.models import Count
from django.http import HttpResponse
from django.core.management import call_command
import os
from django.contrib.auth.models import User

def run_migrations_and_superuser(request):
    # Exécute les migrations
    call_command('migrate')
    
    # Crée un superutilisateur programmatiquement
    try:
        User.objects.get(username='souheil')
    except User.DoesNotExist:
        User.objects.create_superuser(
            username='souheil',
            email='souheil@example.com',
            password='ton_mot_de_passe'  # Remplace par un vrai mot de passe sécurisé
        )
    
    return HttpResponse("Migrations et superutilisateur créés !")

def reservation_create(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if request.method == 'POST':
        form = ReservationForm(request.POST)
        if form.is_valid():
            reservation = form.save(commit=False)
            discount = form.cleaned_data['discount']
            if discount <= 20:
                reservation.status = 'unpaid'
                reservation.is_discount_approved = True
            else:
                reservation.status = 'pending_pdg'
                reservation.is_discount_approved = False
            reservation.save()
            return redirect('reservation_detail', reservation_id=reservation.id)
    else:
        form = ReservationForm()
    return render(request, 'core/reservation_create.html', {'form': form})

def reservation_detail(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id)
    return render(request, 'core/invoice.html', {'reservation': reservation})

@login_required
def confirm_reservation(request, reservation_id):
    if request.user.role != 'Exploitant':
        return redirect('dashboard')
    reservation = get_object_or_404(Reservation, id=reservation_id)
    if request.method == 'POST':
        reservation.status = 'unpaid'
        reservation.save()
        return redirect('reservation_detail', reservation_id=reservation.id)
    return render(request, 'core/confirm_reservation.html', {'reservation': reservation})

@login_required
def apply_discount(request, reservation_id):
    if request.user.role != 'PDG':
        return redirect('dashboard')
    reservation = get_object_or_404(Reservation, id=reservation_id)
    if request.method == 'POST':
        form = DiscountForm(request.POST, instance=reservation)
        if form.is_valid():
            reservation.is_discount_approved = True  # PDG approuve
            reservation.status = 'unpaid'
            reservation.save()
            return redirect('reservation_detail', reservation_id=reservation.id)
    else:
        form = DiscountForm(instance=reservation)
    return render(request, 'core/apply_discount.html', {'form': form, 'reservation': reservation})

@login_required
def confirm_payment(request, reservation_id):
    if request.user.role != 'Caissier':
        return redirect('dashboard')
    reservation = get_object_or_404(Reservation, id=reservation_id)
    if request.method == 'POST':
        reservation.status = 'paid'
        reservation.save()
        return redirect('dashboard')
    return render(request, 'core/payment_confirmation.html', {'reservation': reservation})

@login_required
def create_trip(request, reservation_id):
    if request.user.role != 'Exploitant':
        return redirect('dashboard')
    reservation = get_object_or_404(Reservation, id=reservation_id)
    if reservation.status != 'paid':
        return redirect('dashboard')
    if request.method == 'POST':
        form = TripForm(request.POST)
        if form.is_valid():
            trip = form.save(commit=False)
            trip.reservation = reservation
            trip.save()
            reservation.status = 'confirmed'
            reservation.save()
            return redirect('transport_order', trip_id=trip.id)
    else:
        form = TripForm()
    return render(request, 'core/trip_create.html', {'form': form, 'reservation': reservation})

@login_required
def transport_order(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)
    return render(request, 'core/transport_order.html', {'trip': trip})

def calendar_events(request):
    reservations = Reservation.objects.filter(status__in=['confirmed', 'paid'])
    events = [
        {
            'title': f'حجز {r.reference}',
            'start': r.start_date.isoformat(),
            'end': (r.end_date + timedelta(days=1)).isoformat(),
            'color': '#1a3c34' if r.status == 'confirmed' else '#f4a261',
        } for r in reservations
    ]
    return JsonResponse(events, safe=False)

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from datetime import timedelta
from .models import Reservation, Trip, Driver, Bus
from .forms import ReservationForm, DiscountForm, TripForm
from django.db.models import Count

# ... (autres fonctions inchangées)

@login_required
def dashboard(request):
    if request.user.role == 'Superviseur':
        total_reservations = Reservation.objects.count()
        total_drivers = Driver.objects.count()
        total_buses = Bus.objects.count()
        available_drivers = Driver.objects.filter(available=True).count()
        available_buses = Bus.objects.filter(available=True).count()
        reservations_by_status = Reservation.objects.values('status').annotate(count=Count('id'))
        all_reservations = Reservation.objects.all().select_related('client', 'destination')
        pending_count = Reservation.objects.filter(status='pending').count()  # Notification

        monthly_data = []
        for month in range(1, 13):
            count = Reservation.objects.filter(start_date__month=month).count()
            monthly_data.append(count)

        context = {
            'total_reservations': total_reservations,
            'total_drivers': total_drivers,
            'total_buses': total_buses,
            'available_drivers': available_drivers,
            'available_buses': available_buses,
            'reservations_by_status': reservations_by_status,
            'all_reservations': all_reservations,
            'monthly_data': monthly_data,
            'pending_count': pending_count,  # Ajouté pour les notifications
        }
        return render(request, 'core/dashboard.html', context)
    elif request.user.role == 'Exploitant':
        paid_reservations = Reservation.objects.filter(status='paid')
        paid_count = paid_reservations.count()  # Notification
        return render(request, 'core/dashboard.html', {
            'paid_reservations': paid_reservations,
            'paid_count': paid_count,  # Ajouté pour les notifications
        })
    elif request.user.role == 'Caissier':
        unpaid_reservations = Reservation.objects.filter(status='unpaid')
        paid_reservations = Reservation.objects.filter(status='paid')
        unpaid_count = unpaid_reservations.count()  # Notification
        return render(request, 'core/dashboard.html', {
            'unpaid_reservations': unpaid_reservations,
            'paid_reservations': paid_reservations,
            'unpaid_count': unpaid_count,  # Ajouté pour les notifications
        })
    elif request.user.role == 'PDG':
        pending_pdg_reservations = Reservation.objects.filter(status='pending_pdg')
        confirmed_reservations = Reservation.objects.filter(status__in=['unpaid', 'paid', 'confirmed'])
        pending_pdg_count = pending_pdg_reservations.count()  # Notification
        return render(request, 'core/dashboard.html', {
            'pending_pdg_reservations': pending_pdg_reservations,
            'confirmed_reservations': confirmed_reservations,
            'pending_pdg_count': pending_pdg_count,  # Ajouté pour les notifications
        })
    else:
        return render(request, 'core/dashboard.html', {'message': 'غير مصرح لك بأي دور'})