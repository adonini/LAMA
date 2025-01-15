from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from django.utils.timezone import now
from django.db.models import Q


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
    long_name = models.CharField(max_length=100)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='institutes', null=True, blank=True)
    long_description = models.TextField(blank=True)
    is_lst = models.BooleanField(default=True)  # Flag to indicate LST-specific institutes

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
        ('affiliated', 'Affiliated'),
        ('engineer', 'Engineer'),
        ('administrator', 'Administrator'),
    ]

    name = models.CharField(max_length=50)
    surname = models.CharField(max_length=50)
    primary_email = models.EmailField(unique=True)  # Mandatory
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    def clean(self):
        super().clean()

    def current_membership(self, include_inactive=False):
        """
        Get the current active membership period or the most recent membership if include_inactive=True.
        """
        today = timezone.now().date()
        if include_inactive:
            # Return the most recent membership, active or inactive
            return self.membership_periods.order_by('-start_date').first()
        else:
            # Return only the active membership
            return self.membership_periods.filter(
                Q(start_date__lte=today) & (Q(end_date__isnull=True) | Q(end_date__gte=today))
            ).order_by('-start_date').first()

    def current_authorship(self, include_inactive=False):
        """
        Get the current active authorship period or the most recent authorship if include_inactive=True.
        """
        today = timezone.now().date()

        if include_inactive:
            # Return the most recent authorship, active or inactive
            return self.authorship_periods.order_by('-start_date').first()
        else:
            # Return only the active authorship
            return self.authorship_periods.filter(
                Q(start_date__lte=today) & (Q(end_date__isnull=True) | Q(end_date__gte=today))
            ).order_by('-start_date').first()

    def future_membership(self):
        """
        Get the upcoming membership period, if any.
        """
        today = timezone.now().date()
        return self.membership_periods.filter(start_date__gt=today).order_by('start_date').first()

    def future_authorship(self):
        """
        Get the upcoming authorship period, if any.
        """
        today = timezone.now().date()
        return self.authorship_periods.filter(start_date__gt=today).order_by('start_date').first()

    def is_active_member(self):
        """
        Check if the member has an active membership.
        A membership is active if its end_date is null or greater than today.
        """
        today = timezone.now().date()
        return self.membership_periods.filter(
            Q(end_date__isnull=True) | Q(end_date__gte=today)
        ).exists()

    def is_active_author(self):
        """
        Check if the member has an active authorship.
        An authorship is active if its end_date is null or greater than today.
        """
        today = timezone.now().date()
        return self.authorship_periods.filter(
            Q(start_date__lte=today) & (Q(end_date__isnull=True) | Q(end_date__gte=today))
        ).exists()

    def current_institute(self, include_inactive=False):
        """
        Get the current institute from the active membership period.
        If no active membership exists, fallback to the most recent membership period if include_inactive=True.
        """
        current_membership = self.current_membership(include_inactive=include_inactive)
        if current_membership:
            return current_membership.institute
        return None

    def active_duties(self):
        """Get all active duties for this member."""
        return self.duties.filter(end_date__isnull=True) | self.duties.filter(end_date__gte=timezone.now().date())

    def inactive_duties(self):
        """Get all inactive duties for this member."""
        return self.duties.filter(end_date__lt=timezone.now().date())

    def __str__(self):
        return f"{self.name} {self.surname}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


class AuthorDetails(models.Model):
    member = models.OneToOneField(Member, on_delete=models.CASCADE, related_name='author_details',
                                  help_text="The member associated with this author information.")
    author_name = models.CharField(max_length=150, blank=True,
                                   help_text="Full author name as it appears in publications.")
    author_name_given = models.CharField(max_length=80, blank=True,
                                         help_text="Given name as it appears in publications.")
    author_name_family = models.CharField(max_length=80, blank=True,
                                          help_text="Family name as it appears in publications.")
    author_email = models.EmailField(blank=True,
                                     help_text="Email used for publications.")
    orcid = models.CharField(max_length=25, blank=True)  # ORCID has 19 characters including hyphens

    def __str__(self):
        return f"Author Info: {self.member.name} {self.member.surname}"

    def ordered_institutes(self):
        """
        Return the institutes in the specified order.
        """
        return [affiliation.institute for affiliation in self.institute_affiliations.all()]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


class AuthorInstituteAffiliation(models.Model):
    author_details = models.ForeignKey('AuthorDetails', on_delete=models.CASCADE, related_name='institute_affiliations',
                                       help_text="The author details associated with this institute.")
    institute = models.ForeignKey('Institute', on_delete=models.CASCADE,
                                  help_text="Institute affiliated with this author.")
    order = models.PositiveIntegerField(help_text="The order in which the institute appears for the author.")

    class Meta:
        unique_together = ('author_details', 'institute')  # Prevent duplicates
        ordering = ['order']  # Always return institutes in the specified order

    def __str__(self):
        return f"{self.institute.name} ({self.order})"

    def save(self, *args, **kwargs):
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
