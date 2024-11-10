from django.db import models
from django.utils import timezone
from datetime import timedelta


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
    name = models.CharField(max_length=50)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='institutes')

    def __str__(self):
        return self.name


class Duty(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class Member(models.Model):
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('technician', 'Technician'),
        ('researcher', 'Researcher'),
        ('affiliated', 'Affiliated'),
    ]

    name = models.CharField(max_length=50)
    surname = models.CharField(max_length=50)
    primary_email = models.EmailField(unique=True)  # Mandatory
    secondary_email = models.EmailField(unique=True, null=True, blank=True)  # Optional
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_author = models.BooleanField(default=False)
    authorship_start = models.DateField(null=True, blank=True)
    authorship_end = models.DateField(null=True, blank=True)
    institute = models.ForeignKey(Institute, on_delete=models.SET_NULL, null=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    #duty = models.ForeignKey(Duty, on_delete=models.SET_NULL, null=True)

    def save(self, *args, **kwargs):
        # Automatically set authorship dates if the member is an author
        if self.is_author:
            if not self.authorship_start:
                self.authorship_start = self.start_date + timedelta(days=180)  # 6 months after start date
            if self.end_date and not self.authorship_end:
                self.authorship_end = self.end_date + timedelta(days=180)  # 6 months after end date
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.first_name} {self.second_name} ({self.institute})"


class MemberDuty(models.Model):
    """
    This structure enables tracking both current and past duties for each member and allows
    multiple duties with overlapping or different periods.

    Attributes:
        member (ForeignKey): A reference to the Member model, representing the member to whom
                             the duty is assigned.
        duty (ForeignKey): A reference to the Duty model, specifying the assigned duty.
        start_date (DateField): The date when the duty assignment begins.
        end_date (DateField): The date when the duty assignment ends. This field can be left
                              null, indicating the duty is ongoing.

    Custom Manager:
        ActiveDutyManager: Provides methods to filter active and inactive duties across all
                           assignments, making it easy to retrieve duties based on their
                           current status.

    Properties:
        is_active (bool): A property that returns True if the duty is currently active
                          (i.e., the end date is in the future or null), and False if
                          the duty has ended.

    Usage:
        - `MemberDuty.objects.active()`: Retrieves all active duty assignments.
        - `MemberDuty.objects.inactive()`: Retrieves all past (inactive) duty assignments.
        - `member.duties.active()`: Retrieves active duties for a specific member.
        - `member.duties.inactive()`: Retrieves inactive duties for a specific member.

    It support historical duty tracking, each member past and present duties are recorded.
    Once a duty period expires, it is no longer considered active, but remains part of the member's
    duty history.
    """
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='duties')
    duty = models.ForeignKey(Duty, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.duty.name} for {self.member.name} {self.member.surname}"

    @property
    def is_active(self):
        return self.end_date is None or self.end_date >= timezone.now().date()


class ActiveDutyManager(models.Manager):
    def active(self):
        return self.filter(end_date__gte=timezone.now().date()) | self.filter(end_date__isnull=True)

    def inactive(self):
        return self.filter(end_date__lt=timezone.now().date())
