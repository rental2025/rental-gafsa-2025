from django.db import models
from datetime import timedelta
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLES = (
        ('Superviseur', 'Superviseur'),
        ('Exploitant', 'Exploitant'),
        ('Caissier', 'Caissier'),
        ('PDG', 'PDG'),
    )
    role = models.CharField(max_length=20, choices=ROLES, default='Superviseur')

    def __str__(self):
        return self.username

class Client(models.Model):
    CLIENT_TYPES = (
        ('personne_physique', 'حريف عادي'),
        ('conventionne', 'حريف متعاقد'),
        ('sakhir', 'سخير من سلطة'),
        ('pdg_permission', 'إذن المدير العام'),
        ('sport_supported', 'حريف مدعوم من مندوبية الرياضة'),
    )
    name = models.CharField(max_length=100)
    email = models.EmailField()
    client_type = models.CharField(max_length=50, choices=CLIENT_TYPES)

    def __str__(self):
        return self.name

class Distance(models.Model):
    destination = models.CharField(max_length=100)
    distance_km = models.FloatField()

    def __str__(self):
        return f"{self.destination} ({self.distance_km} كم)"

class Driver(models.Model):
    name = models.CharField(max_length=100)
    matricule = models.CharField(max_length=50)
    available = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Bus(models.Model):
    CAPACITY_PRICES = {29: 2.5, 50: 3.0, 70: 3.5}
    matricule = models.CharField(max_length=50)
    capacity = models.IntegerField(choices=[(k, str(k)) for k in CAPACITY_PRICES.keys()])
    available = models.BooleanField(default=True)

    def get_price_per_km(self):
        return self.CAPACITY_PRICES.get(self.capacity, 3.0)

    def __str__(self):
        return f"حافلة {self.matricule} ({self.capacity} مقعد)"

class Reservation(models.Model):
    STATUS_CHOICES = (
        ('pending', 'في الانتظار'),
        ('confirmed_exploitant', 'تم التأكيد من المشغل'),
        ('pending_pdg', 'في انتظار تأكيد المدير العام'),
        ('unpaid', 'غير مدفوعة'),
        ('paid', 'مدفوعة'),
        ('confirmed', 'مؤكدة'),
    )
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    departure = models.CharField(max_length=100, default="قفصة")
    destination = models.ForeignKey(Distance, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    days = models.IntegerField(editable=False)
    unit_price = models.FloatField(default=3.0)
    daily_price = models.FloatField(default=250.0)
    discount = models.FloatField(default=0.0)
    tax_rate = models.FloatField(default=0.07)
    stamp_duty = models.FloatField(default=1.0)
    total_price = models.FloatField(editable=False)
    client_share = models.FloatField(default=0.0, editable=False)
    ministry_share = models.FloatField(default=0.0, editable=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reference = models.CharField(max_length=50, unique=True, blank=True)
    is_discount_approved = models.BooleanField(default=True)

    def calculate_days(self):
        """Calcule le nombre de jours selon la nouvelle règle."""
        delta = (self.end_date - self.start_date).days
        return 0 if delta == 0 else 1

    def calculate_km_price(self):
        return self.unit_price * self.destination.distance_km

    def calculate_waiting_hours(self):
        if self.client.client_type != 'sport_supported':
            return 0
        days = self.calculate_days()
        if days == 0:
            return 5
        elif days == 1:
            return 15
        else:
            return 25

    def calculate_waiting_price(self):
        return self.calculate_waiting_hours() * 30

    def calculate_daily_price(self):
        days = self.calculate_days()
        if self.client.client_type == 'sport_supported':
            return 0
        elif self.client.client_type == 'conventionne':
            return 900 * days
        return self.daily_price * days

    def calculate_base_price(self):
        km_price = self.calculate_km_price()
        if self.client.client_type == 'sport_supported':
            waiting_price = self.calculate_waiting_price()
            return km_price + waiting_price
        return km_price + self.calculate_daily_price()

    def calculate_discount_amount(self):
        base_price = self.calculate_base_price()
        if self.client.client_type == 'sport_supported':
            client_share_ht = base_price * 0.5
            discount_amount = client_share_ht * (self.discount / 100)
            return discount_amount if self.is_discount_approved else 0
        return base_price * (self.discount / 100) if self.is_discount_approved else 0

    def calculate_tax_amount(self):
        base_price = self.calculate_base_price()
        discount_amount = self.calculate_discount_amount()
        if self.client.client_type == 'sport_supported':
            client_share_after_discount = (base_price * 0.5) - discount_amount
            ministry_share = base_price * 0.5
            return (client_share_after_discount * self.tax_rate) + (ministry_share * self.tax_rate)
        price_after_discount = base_price - discount_amount
        return price_after_discount * self.tax_rate

    def client_share_before_tax(self):
        """حصة الحريف بدون الأداء"""
        if self.client.client_type == 'sport_supported':
            return (self.calculate_base_price() * 0.5) - self.calculate_discount_amount()
        return None

    def ministry_share_before_tax(self):
        """حصة المندوبية بدون الأداء"""
        if self.client.client_type == 'sport_supported':
            return self.calculate_base_price() * 0.5
        return None

    def client_tax(self):
        """الأداء (7%) الحريف"""
        if self.client.client_type == 'sport_supported':
            return ((self.calculate_base_price() * 0.5) - self.calculate_discount_amount()) * self.tax_rate
        return None

    def ministry_tax(self):
        """الأداء (7%) المندوبية"""
        if self.client.client_type == 'sport_supported':
            return (self.calculate_base_price() * 0.5) * self.tax_rate
        return None

    def calculate_total(self):
        base_price = self.calculate_base_price()
        discount_amount = self.calculate_discount_amount()
        if self.client.client_type == 'sport_supported':
            client_share_ht = base_price * 0.5
            ministry_share_ht = base_price * 0.5
            client_share_after_discount = client_share_ht - discount_amount
            client_tax = client_share_after_discount * self.tax_rate
            ministry_tax = ministry_share_ht * self.tax_rate
            self.client_share = client_share_after_discount + client_tax + self.stamp_duty
            self.ministry_share = ministry_share_ht + ministry_tax
            return self.client_share + self.ministry_share
        price_after_discount = base_price - discount_amount
        tax = price_after_discount * self.tax_rate
        return price_after_discount + tax + self.stamp_duty

    def save(self, *args, **kwargs):
        self.days = self.calculate_days()
        if self.discount > 20 and not self.is_discount_approved:
            self.status = 'pending_pdg'
        if not self.reference:
            self.reference = f"REF-{Reservation.objects.count() + 1}-{self.start_date.strftime('%Y%m%d')}"
        self.total_price = self.calculate_total()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"حجز {self.reference}"

class Trip(models.Model):
    reservation = models.OneToOneField(Reservation, on_delete=models.CASCADE)
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE)
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE)

    def __str__(self):
        return f"رحلة {self.id}"