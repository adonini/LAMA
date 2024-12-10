from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from django.utils.timezone import now


class Country(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class Group(models.Model):
    name = models.CharField(max_length=50)
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='groups')

    def __str__(self):
        return self.name


class Institute(models.Model):
    name = models.CharField(max_length=150)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='institutes')

    def __str__(self):
        return self.name


class Duty(models.Model):
    """
    Represents a predefined list of duties that can be assigned to members.
    """
    name = models.CharField(max_length=100, unique=True)  # Duty names must be unique
    description = models.TextField(blank=True)  # Optional description for the duty

    def __str__(self):
        return self.name


class MembershipPeriod(models.Model):
    member = models.ForeignKey('Member', on_delete=models.CASCADE, related_name='membership_periods')
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)  # Null means still active
    institute = models.ForeignKey('Institute', on_delete=models.SET_NULL, null=True, blank=True)

    def is_active(self):
        return not self.end_date or self.end_date >= now().date()

    def __str__(self):
        return f"{self.member.name} - {self.start_date} to {self.end_date or 'Active'}"


class AuthorshipPeriod(models.Model):
    member = models.ForeignKey('Member', on_delete=models.CASCADE, related_name='authorship_periods')
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)  # Null means still active

    def is_active(self):
        return not self.end_date or self.end_date >= now().date()

    def __str__(self):
        return f"{self.member.name} - {self.start_date} to {self.end_date or 'Active'}"


class Member(models.Model):
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('technician', 'Technician'),
        ('researcher', 'Researcher'),
        ('associate', 'Associate'),
        ('engineer', 'Engineer'),
        ('administrator', 'Administrator'),
    ]

    name = models.CharField(max_length=50)
    surname = models.CharField(max_length=50)
    primary_email = models.EmailField(unique=True)  # Mandatory
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    def clean(self):
        super().clean()

    def current_membership(self):
        """Get the current membership period."""
        return self.membership_periods.filter(end_date__isnull=True).first()

    def current_authorship(self):
        """Get the current authorship period."""
        return self.authorship_periods.filter(end_date__isnull=True).first()

    def is_active_member(self):
        """Check if the member has an active membership."""
        return self.membership_periods.filter(end_date__isnull=True).exists()

    def is_active_author(self):
        """Check if the member has an active authorship."""
        return self.authorship_periods.filter(end_date__isnull=True).exists()

    def current_institute(self):
        """Get the current institute from the active membership period."""
        current_membership = self.current_membership()
        return current_membership.institute if current_membership else None

    def active_duties(self):
        """Get all active duties for this member."""
        return self.duties.filter(end_date__isnull=True) | self.duties.filter(end_date__gte=timezone.now().date())

    def inactive_duties(self):
        """Get all inactive duties for this member."""
        return self.duties.filter(end_date__lt=timezone.now().date())

    def __str__(self):
        return f"{self.name} {self.surname}"

    def save(self, *args, **kwargs):
        # Check if the instance is new or updated
        is_new = not self.pk
        old_instance = None if is_new else Member.objects.get(pk=self.pk)

        # Handle institute changes
        if not is_new and old_instance.institute != self.institute:
            # End the current membership period if the institute changes
            current_membership = old_instance.current_membership()
            if current_membership:
                current_membership.end_date = now().date()
                current_membership.save()

            # Start a new membership period with the new institute
            MembershipPeriod.objects.create(
                member=self,
                start_date=now().date(),
                institute=self.institute
            )

        # Handle membership periods in case of stopping or restarting
        if not is_new:
            is_stopping_membership = old_instance.is_active_member() and not self.is_active_member()
            is_restarting_membership = not old_instance.is_active_member() and self.is_active_member()

            # End membership if stopping
            if is_stopping_membership:
                current_membership = old_instance.current_membership()
                if current_membership:
                    current_membership.end_date = now().date()
                    current_membership.save()
            # Start a new membership if restarting
            elif is_restarting_membership:
                MembershipPeriod.objects.create(
                    member=self,
                    start_date=now().date(),
                    institute=self.institute
                )

        # Handle authorship periods for stopping or restarting
        if not is_new:
            is_stopping_authorship = old_instance.is_active_author() and not self.is_active_author()
            is_restarting_authorship = not old_instance.is_active_author() and self.is_active_author()

            # End authorship if stopping
            if is_stopping_authorship:
                current_authorship = old_instance.current_authorship()
                if current_authorship:
                    current_authorship.end_date = now().date()
                    current_authorship.save()
            # Start a new authorship if restarting
            elif is_restarting_authorship:
                AuthorshipPeriod.objects.create(
                    member=self,
                    start_date=now().date()
                )

        super().save(*args, **kwargs)


class MemberDuty(models.Model):
    """
    Tracks the assignment of duties to members.
    """
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='duties')
    duty = models.ForeignKey(Duty, on_delete=models.CASCADE, related_name='assignments')
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)  # Null means ongoing

    class Meta:
        unique_together = ('member', 'duty', 'start_date')  # Prevent duplicate assignments for the same start date

    def __str__(self):
        return f"{self.duty.name} for {self.member.name} {self.member.surname}"

    @property
    def is_active(self):
        """
        Check if the duty assignment is currently active.
        """
        return self.end_date is None or self.end_date >= timezone.now().date()


class ActiveDutyManager(models.Manager):
    """
    Provides convenient methods to filter active and inactive duties.
    """
    def active(self):
        today = timezone.now().date()
        return self.filter(models.Q(end_date__gte=today) | models.Q(end_date__isnull=True))

    def inactive(self):
        today = timezone.now().date()
        return self.filter(end_date__lt=today)
