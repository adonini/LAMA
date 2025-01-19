import json
import logging
from datetime import date, datetime, timedelta
from .forms import LoginForm, AddMemberForm, AddAuthorDetailsForm, AddInstituteForm
from .models import (Member, Institute, Group, Duty, Country, MemberDuty,
                     MembershipPeriod, AuthorshipPeriod, AuthorDetails,
                     AuthorInstituteAffiliation)
from dateutil.relativedelta import relativedelta
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.views.generic import TemplateView
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.db.models import Q
from django.utils.timezone import now, make_aware
from django.db.models import Prefetch
from pytz import UTC


logger = logging.getLogger('lama')


def parse_date(date_string):
    try:
        return datetime.strptime(date_string, '%Y-%m-%d').date() if date_string else None
    except ValueError:
        return None


def logout_user(request):
    logout(request)
    messages.warning(request, "You Have Been Logged Out...")
    return redirect('index')


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('index')
    else:
        form = LoginForm()
    return render(request, 'login/login.html', {'form': form})


def calculate_12_months_avg(queryset, date_field, today):
    """
    Calculates the average count of members or authors over the last 12 months,
    considering data on the 15th of each month.
    If the current date is before the 15th of the month, the function starts the calculation
    from the 15th of the previous month and excludes the current month. If the current date
    is on or after the 15th, the calculation includes the current month, starting from the
    15th of the current month.
    Args:
        queryset: The queryset of members or authors to be counted.
        date_field: The date field used to filter the data (e.g., membership 'start_date' or 'authorship_start').
        today: The current date, used to determine whether the current month should be included.
    Returns:
        float: The average count over the last 12 months.
    """
    # List to hold member counts for the 12 months
    months_data = []

    # Determine the starting point for the calculation
    if today.day < 15:
        # If today is before the 15th, exclude the current month and start from the previous month
        start_month = today + relativedelta(months=-1)
        start_month = start_month.replace(day=15)
    else:
        # If today is after the 15th, include the current month
        start_month = today.replace(day=15)

    # Now loop back through the last 12 months, considering the 15th of each month
    for i in range(12):
        # Calculate the target date for the 15th of each month
        month_date = start_month + relativedelta(months=-i)
        # Get the count of members/authors active until the 15th of the month
        monthly_count = queryset.filter(**{f"{date_field}__lte": month_date}) \
                                .filter(
                                    Q(membership_periods__end_date__isnull=True) | Q(membership_periods__end_date__gt=month_date)
                                ).distinct().count()
        months_data.append(monthly_count)
    # Calculate the average over the 12 months
    return sum(months_data) / len(months_data) if months_data else 0


def calculate_averages(queryset, date_field, year, current_year, current_month):
    """
    Calculates the average count of members or authors for a specific year, based on activity on the 15th of each month.
    If the year is the current year, it includes months up to the current month; for previous years, all 12 months are considered.
    Args:
        queryset: The queryset of members or authors to be counted.
        date_field: The date field to filter by (e.g., 'start_date').
        year: The year to calculate the average for.
        current_year: The current year, used for limiting months if needed.
        current_month: The current month, used for limiting months in the current year.
    Returns:
        float: The average count of active members or authors for the specified year.
    """
    months = range(1, (current_month + 1) if year == current_year else 13)
    total = 0

    for month in months:
        count = queryset.filter(**{f"{date_field}__lte": datetime(year, month, 15)}) \
            .filter(
                Q(membership_periods__end_date__isnull=True) | Q(membership_periods__end_date__gt=datetime(year, month, 15))
            ).distinct().count()

        #logger.debug(f"Year: {year}, Month: {month}, Active Members Count: {count}")
        total += count

    divisor = len(months)
    average = total / divisor if divisor > 0 else 0

    return average


def get_active_member_count(queryset, date_field, year, month):
    check_date = datetime(year, month, 15).date()
    return queryset.filter(**{f"{date_field}__lte": check_date}).filter(
        Q(membership_periods__end_date__isnull=True) | Q(membership_periods__end_date__gt=check_date)
    ).count()


def get_active_author_count(queryset, year, month):
    check_date = datetime(year, month, 15).date()
    return queryset.filter(authorship_periods__start_date__lte=check_date).filter(
        Q(authorship_periods__end_date__isnull=True) | Q(authorship_periods__end_date__gt=check_date)
    ).count()


def get_active_periods_count(queryset, period_field, year, month):
    """
    Calculates and returns the total number of members who were active during a given month, considering
    all of their membership or authorship periods (both past and current). The function checks if any of
    a member's periods overlap with the 15th day of the specified month and counts them as active if they were.
    Args:
        queryset (QuerySet): A filtered Django queryset containing the member records to be evaluated.
                              The queryset is expected to already be filtered by parameters such as country, group, or institute.
        period_field (str): The name of the related field (either 'membership_periods' or 'authorship_periods')
                            in the Member model that holds the historical periods of membership or authorship.
        year (int): The year for which the activity is being checked.
        month (int): The month for which the activity is being checked.
    Returns:
        int: The count of members who were active during the specified month, considering all their periods.
    """
    check_date = datetime(year, month, 15).date()  # Checking the 15th day of the month
    active_count = 0

    #print(f"Checking activity for {period_field} in {year}-{month}")

    for member in queryset:
        # Get all the periods for the specified field (membership or authorship)
        periods = getattr(member, period_field).all()  # Get the membership or authorship periods
        #print(f"  Checking member: {member.id} - {member.name} for {period_field} periods")
        for period in periods:
            #print(f"    Checking period: {period.start_date} to {period.end_date if period.end_date else 'None'}")
            # Check if the period is active on the 15th day of the month
            if period.start_date <= check_date and (not period.end_date or period.end_date >= check_date):
                active_count += 1
                #print(f"  member: {member.id} - {member.name} for {period_field} periods")
                #print(f"    Period {period.start_date} to {period.end_date if period.end_date else 'None'} is active, member counted. Active count now: {active_count}")
                break  # No need to count the same member multiple times
    print(f"Total active members for {period_field} in {year}-{month}: {active_count}")
    return active_count


def get_valid_authors_for_date(selected_date_str):
    """
    Returns a list of authors and their affiliations that are valid on the given date.
    The function ensures that the authorship periods overlap with the selected date.
    """
    try:
        # Parse the date string and convert it to a UTC-aware datetime object at midnight
        selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
        selected_date = make_aware(datetime.combine(selected_date, datetime.min.time()), timezone=UTC)
    except ValueError:
        return None, "Invalid date format"

    # Step 1: Find all members with valid authorship periods on the selected date
    valid_authors = Member.objects.filter(
        Q(authorship_periods__start_date__lte=selected_date) &
        (Q(authorship_periods__end_date__gte=selected_date) | Q(authorship_periods__end_date__isnull=True))
    ).distinct()

    # Step 2: Fetch AuthorDetails for those members, prefetching related institute affiliations
    authors = AuthorDetails.objects.filter(member__in=valid_authors).prefetch_related(
        Prefetch('institute_affiliations', queryset=AuthorInstituteAffiliation.objects.select_related('institute'))
    ).order_by('author_name_family', 'author_name_given')  # Order by surname and given name

    return authors, selected_date, valid_authors


def get_missing_authors(valid_authors):
    """
    Takes a list of valid authors and returns a list of authors who don't have AuthorDetails.
    It also appends a warning message if there are missing authors.
    """
    missing_authors = []

    # Step 3: Identify authors without AuthorDetails or missing info
    for member in valid_authors:
        try:
            author_details = AuthorDetails.objects.get(member=member)
            # Check if the author has a full name and at least one affiliation
            has_full_name = bool(author_details.author_name)
            has_affiliation = author_details.institute_affiliations.exists()

            if not has_full_name or not has_affiliation:
                missing_authors.append(f"{member.name} {member.surname}")
        except AuthorDetails.DoesNotExist:
            # If AuthorDetails doesn't exist for the member, they are considered missing
            missing_authors.append(f"{member.name} {member.surname}")
    return missing_authors


class Index(TemplateView):
    template_name = 'login/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()

        # Count of active members, defined as those with no end date or an end date in the future
        total_members = MembershipPeriod.objects.filter(
            Q(start_date__lte=today) & (Q(end_date__isnull=True) | Q(end_date__gte=today))
        ).values('member').distinct().count()

        # Count of members who have an authorship start date on or before today and either no authorship end date or an authorship end date in the future
        total_authors = AuthorshipPeriod.objects.filter(
            Q(start_date__lte=today) & (Q(end_date__isnull=True) | Q(end_date__gte=today))
        ).values('member').distinct().count()

        # Members becoming authors within the last 6 months
        six_months_ago = timezone.now() - relativedelta(months=6)
        members_becoming_authors = AuthorshipPeriod.objects.filter(
            member__membership_periods__start_date__gte=six_months_ago
        ).values('member').distinct().count()

        # Non-members with active authorship
        non_members_with_authorship = AuthorshipPeriod.objects.filter(
            start_date__lte=today,
            end_date__gt=today,
            member__membership_periods__end_date__lt=today
        ).values('member').distinct().count()

        # People leaving authorship in the next 6 months
        six_months_future = today + relativedelta(months=6)
        people_leaving_authorship = AuthorshipPeriod.objects.filter(
            end_date__gt=today, end_date__lte=six_months_future
        ).values('member').distinct().count()

        # Contributing to CF
        cf = AuthorshipPeriod.objects.filter(
            start_date__lte=six_months_future
        ).filter(Q(end_date__isnull=True) | Q(end_date__gt=six_months_future)).values('member').distinct().count()

        # Count institutes and groups per country
        #total_institutes = Institute.objects.count()
        total_institutes = Institute.objects.filter(is_lst=True).count()
        total_groups = Group.objects.count()
        total_countries = Country.objects.count()

        institutes_per_country = {}
        groups_per_country = {}
        for country in Country.objects.all():
            lst_institutes = Institute.objects.filter(group__country=country, is_lst=True)
            institutes_per_country[country.name] = lst_institutes.count()

            #institutes_per_country[country.name] = Institute.objects.filter(group__country=country).count()
            groups_per_country[country.name] = Group.objects.filter(country=country).count()

        # Prepare the context to pass to the template
        context.update({
            'total_members': total_members,
            'total_authors': total_authors,
            'members_becoming_authors': members_becoming_authors,
            'non_members_with_authorship': non_members_with_authorship,
            'people_leaving_authorship': people_leaving_authorship,
            'cf': cf,
            'total_institutes': total_institutes,
            'total_groups': total_groups,
            'total_countries': total_countries,
            'institutes_per_country': institutes_per_country,
            'groups_per_country': groups_per_country,
            'current_date': datetime.now().strftime('%B %d, %Y')
        })
        return context


class MemberList(LoginRequiredMixin, View):
    def get(self, request):
        today = timezone.now().date()
        six_months_future = today + relativedelta(months=6)

        # Determine whether to show all members
        show_all = request.GET.get('show_all', 'false').lower() == 'true'

        # Prefetch related data
        members = Member.objects.prefetch_related(
            'membership_periods__institute__group__country',
            'authorship_periods'
        ).distinct()

        # Filter out inactive members when show_all is False
        if not show_all:
            members = members.filter(
                Q(membership_periods__end_date__isnull=True) | Q(membership_periods__end_date__gte=today)
            )

        member_list = []

        for member in members:
            # Determine current institute and membership
            active_membership = member.current_membership(include_inactive=show_all)
            future_membership = member.future_membership()
            membership = active_membership or future_membership  # Use future membership if no active membership

            current_institute = membership.institute if membership else None

            authorship_period = member.current_authorship(include_inactive=show_all) or member.future_authorship()
            # logger.debug(f"Authorship period for member {member.pk}, {member.name}: {authorship_period}")
            # logger.debug(f"{authorship_period.start_date.strftime('%Y-%m-%d') if authorship_period else None}")
            # Determine authorship and contribution status
            is_author = (
                authorship_period
                and authorship_period.start_date <= today
                and (authorship_period.end_date is None or authorship_period.end_date >= today)
            )
            # Determine if the member will be an author within the next 6 months
            will_become_author = (
                authorship_period
                and authorship_period.start_date > today
                and authorship_period.start_date <= six_months_future
            )

            # Adjusted logic for CF contribution
            is_cf = (is_author or will_become_author) and (  # Consider members who will become authors in the next 6 months
                authorship_period.start_date <= six_months_future
                and (authorship_period.end_date is None or authorship_period.end_date > six_months_future)
            )
            # Prepare the dictionary for JSON serialization
            member_list.append({
                'pk': member.pk,
                'name': member.name,
                'surname': member.surname,
                'primary_email': member.primary_email,
                'start_date': str(membership.start_date) if membership else None,
                'end_date': str(membership.end_date) if membership and membership.end_date else None,
                'role': member.role,
                'is_author': is_author,
                'is_cf': is_cf,
                'authorship_start': authorship_period.start_date.strftime('%Y-%m-%d') if authorship_period else None,
                'authorship_end': authorship_period.end_date.strftime('%Y-%m-%d') if authorship_period and authorship_period.end_date else None,
                'group_name': current_institute.group.name if current_institute and current_institute.group else 'No Group',
                'country_name': current_institute.group.country.name if current_institute and current_institute.group and current_institute.group.country else 'No Country',
                'institute_name': current_institute.name if current_institute else 'No Institute',
            })

        # Data for the filters
        countries = Country.objects.prefetch_related('groups__institutes').order_by('name')
        filters_data = {
            country.name: {
                "groups": {
                    group.name: list(group.institutes.filter(is_lst=True).values_list('name', flat=True))
                    for group in country.groups.all()
                }
            }
            for country in countries
        }

        context = {
            'page_title': 'Member List',
            'members': member_list,
            'member_data': json.dumps(member_list),
            'duties': list(Duty.objects.order_by('name').values('id', 'name')),
            'institutes': list(Institute.objects.filter(is_lst=True).order_by('name').values('id', 'name')),
            'groups': list(Group.objects.order_by('name').values('id', 'name')),
            'countries': list(Country.objects.order_by('name').values('id', 'name')),
            'userGroups': list(request.user.groups.values_list('name', flat=True)),
            'filters': filters_data,
            'current_date': datetime.now().strftime('%B %d, %Y'),
            'show_all': show_all,
        }
        return render(request, 'member_list.html', context)


class MemberRecord(LoginRequiredMixin, View):
    def get(self, request, pk=None):
        context = {}
        context['page_title'] = 'Member Information'
        if pk is None:
            messages.error(request, "Member ID is not recognized")
            return redirect('member_list')
        else:
            try:
                member = Member.objects.get(id=pk)
            except Member.DoesNotExist:
                messages.error(request, "Member not found")
                return redirect('member_list')

            # Fetch the current active membership and authorship periods
            current_membership = member.current_membership()
            current_authorship = member.current_authorship()

            # Fetch related duties and roles for the member
            # duties = MemberDuty.objects.filter(member=member).order_by('start_date')
            # current_duties = [duty for duty in duties if duty.end_date is None]
            # historical_duties = [duty for duty in duties if duty.end_date is not None]
            duties = MemberDuty.objects.filter(member=member)
            role = member.role if member.role else None

            # Get the institutes and their related group information
            institute = member.current_institute() if member.current_institute() else None
            group = institute.group if institute else None
            country = group.country if group else None

            # Get historical duties if any
            historical_duties = MemberDuty.objects.filter(member=member).order_by('start_date') if MemberDuty.objects.filter(member=member) else []

            # Pass all membership periods
            membership_periods = member.membership_periods.order_by('-start_date')
            authorship_periods = member.authorship_periods.order_by('-start_date')

            context.update({
                'member': member,
                'current_membership': current_membership,
                'current_authorship': current_authorship,
                'duties': duties,
                'role': role,
                'institute': institute,
                'group': group,
                'country': country,
                'historical_duties': historical_duties,
                'institutes': Institute.objects.all(),
                'membership_periods': membership_periods,
                'authorship_periods': authorship_periods,
            })
            return render(request, 'member_record.html', context)


class AddMember(LoginRequiredMixin, View):
    def get(self, request):
        context = {
            'page_title': "Manage Member",
            'today': date.today(),
            'countries': Country.objects.all(),
        }
        institute_data = {}
        countries = Country.objects.all()
        for country in countries:
            institutes = list(Institute.objects.filter(group__country=country).values('id', 'name', 'group'))
            if institutes:
                institute_data[country.id] = institutes
        context['institute_data'] = json.dumps(institute_data)
        context['member'] = {}
        context['roles'] = Member.ROLE_CHOICES
        context['institutes'] = Institute.objects.all()
        return render(request, 'manage_member.html', context)

    def get_member(self, member_id):
        """Retrieve an existing member or return None if ID is not provided or invalid."""
        if member_id and member_id.isnumeric():
            return Member.objects.filter(pk=member_id).first()
        return None

    def handle_institute_change(self, member, new_institute_id, is_author, membership_start_date):
        """Handle changes to institute, including stopping and restarting membership."""
        old_institute = member.current_institute(include_inactive=True)
        new_institute = Institute.objects.get(pk=new_institute_id) if new_institute_id else None
        future_authorship = member.future_authorship()

        previous_end_date = membership_start_date - timedelta(days=1)
        if old_institute != new_institute:
            # Step 1: Handle current membership
            current_membership = member.current_membership(include_inactive=False)
            if current_membership and current_membership.is_active():
                current_membership.end_date = previous_end_date
                current_membership.save()

            # Step 2: Adjust authorship if `is_author` is unchecked (member was an author)
            if member.is_active_author():
                if not is_author:  # If `is_author` is unchecked
                    AuthorshipPeriod.objects.filter(member=member, end_date__isnull=True).update(
                        end_date=previous_end_date + relativedelta(months=6)  # Stop after 6 months
                    )
            # Step 3: Create new membership if a new institute is selected
            if new_institute:
                new_membership = MembershipPeriod.objects.create(
                    member=member,
                    start_date=membership_start_date,
                    institute=new_institute
                )
                new_membership.save()

                # Step 4: Handle new authorship period if `is_author` is checked (before was not)
                if is_author:
                    if not member.is_active_author():
                        # Case 4.1: If there is no future authorship, create a new one
                        if not future_authorship:
                            authorship_period = AuthorshipPeriod.objects.create(
                                member=member,
                                start_date=new_membership.start_date + relativedelta(months=6)
                            )
                            authorship_period.save()
                        else:
                            # Case 4.2: If a future authorship already exists, do nothing
                            pass

            # Step 5: Update future authorship if applicable
            if future_authorship:
                if not is_author:  # If `is_author` is unchecked,  end the future authorship
                    future_authorship.end_date = previous_end_date + relativedelta(months=6)
                    future_authorship.save()
            return True  # Member/authorship was updated
        return False  # No change

    def handle_membership_change(self, member, is_stopping_membership, is_author, end_date, start_date, institute_id):
        """Handle stopping or restarting membership."""
        current_membership = member.current_membership(include_inactive=False)
        if is_stopping_membership:
            if current_membership:
                # Step 1: End the current membership
                current_membership.end_date = end_date
                current_membership.save()

                # Step 2: Stop eventual active authorship 6 months later
                if member.is_active_author():
                    current_authorship = member.current_authorship(include_inactive=False)
                    if current_authorship:
                        current_authorship.end_date = end_date + relativedelta(months=6)
                        current_authorship.save()

                # Step 3: Stop future authorship 6 months later if it exists
                future_authorship = member.future_authorship()
                if future_authorship:
                    future_authorship.end_date = end_date + relativedelta(months=6)
                    future_authorship.save()
        else:  # Restart or adjust membership
            if current_membership:
                logger.debug(f"Current membership exists for Member ID={member.id}")
                # Check if the start_date has changed
                if current_membership.start_date != start_date:
                    current_membership.start_date = start_date
                    logger.debug(f"Updated start date {current_membership.start_date}")
                    current_membership.save()
            # Step 1: Create a new membership if no active one exists
            else:
                new_membership = MembershipPeriod.objects.create(
                    member=member,
                    start_date=start_date,
                    institute=Institute.objects.get(pk=institute_id) if institute_id else None
                )
                new_membership.save()

            # Step 2: Handle authorship if `is_author` is checked
            if is_author and not member.is_active_author():
                # Ensure AuthorDetails is created if it doesn't exist
                author_details, created = AuthorDetails.objects.get_or_create(member=member)
                if created:
                    logger.debug(f"Created new AuthorDetails for Member ID={member.id}")

                authorship_period = AuthorshipPeriod.objects.create(
                    member=member,
                    start_date=new_membership.start_date + relativedelta(months=6)
                )
                authorship_period.save()

    def handle_authorship_change(self, member, is_author, auth_start, auth_end):
        """Handle starting or stopping authorship."""
        if is_author and not member.is_active_author():
            # Ensure AuthorDetails is created if it doesn't exist
            author_details, created = AuthorDetails.objects.get_or_create(member=member)
            if created:
                logger.debug(f"Created new AuthorDetails for Member ID={member.id}")

            authorship_period = AuthorshipPeriod.objects.create(
                member=member,
                start_date=auth_start + relativedelta(months=6)
            )
            authorship_period.save()
        else:
            if member.is_active_author():
                # Stopping authorship
                current_authorship = member.current_authorship(include_inactive=False)
                if current_authorship:
                    current_authorship.end_date = auth_end + relativedelta(months=6)
                    current_authorship.save()

    def post(self, request, pk=None):
        resp = {'status': 'failed', 'msg': ''}
        if request.method == 'POST':
            member = self.get_member(request.POST.get('id'))  # Fetch the existing member if ID is provided
            if member:
                current_email = member.primary_email.strip()
            form = AddMemberForm(request.POST, instance=member)

            if form.is_valid():
                logger.info(f"Form is valid. Data: {form.cleaned_data}")
                new_member = form.save(commit=False)  # Don't save yet to handle custom logic
                start_date = form.cleaned_data['start_date']
                end_date = form.cleaned_data.get('end_date')
                institute_id = request.POST.get('institute')
                is_author = request.POST.get('is_author') == 'on'
                authorship_start = parse_date(request.POST.get('authorship_start'))
                authorship_end = parse_date(request.POST.get('authorship_end'))

                if member:  # Editing an existing member
                    # Check if any authorship-related field has changed
                    authorship_changed = False
                    current_authorship = member.current_authorship(include_inactive=False) if member.is_active_author() else None

                    # Check for changes in start and end dates
                    if authorship_start != (current_authorship.start_date if current_authorship else None) or authorship_end != (current_authorship.end_date if current_authorship else None):
                        authorship_changed = True
                    # Check for email update
                    updated_email = form.cleaned_data.get('primary_email').strip()
                    email_changed = current_email != updated_email

                    if email_changed:
                        member.primary_email = updated_email.strip()
                        member.save()
                        logger.debug(f"Successfully updated email for Member ID={member.id}: {member.primary_email}")

                    # Handle case 1: Changing institute
                    institute_changed = self.handle_institute_change(member, institute_id, is_author, start_date)
                    # Handle case 2: Stopping membership
                    # Check if membership has changed
                    current_membership = member.current_membership(include_inactive=False)
                    is_stopping_membership = end_date is not None and member.is_active_member()
                    start_date_changed = (current_membership and current_membership.start_date != start_date)
                    membership_changed = not institute_changed and (is_stopping_membership or start_date_changed)
                    if membership_changed:
                        self.handle_membership_change(member, is_stopping_membership, is_author, end_date, start_date, institute_id)
                    # Handle case 3: Stopping or starting authorship
                    #if not institute_changed and not membership_changed:
                    if authorship_changed:
                        self.handle_authorship_change(member, is_author, authorship_start, authorship_end)
                else:  # Creating a new member
                    new_member.save()  # Save the new member instance
                    # Handle case 4: Starting new membership
                    MembershipPeriod.objects.create(member=new_member,
                                                    start_date=start_date,
                                                    institute=Institute.objects.get(pk=institute_id))
                    # Handle case 5: Starting new authorship if applicable
                    if is_author:
                        try:
                            authorship_period = AuthorshipPeriod.objects.create(
                                member=new_member,
                                start_date=start_date + relativedelta(months=6)
                            )
                            authorship_period.save()
                            # Ensure AuthorDetails is created if it doesn't exist
                            author_details, created = AuthorDetails.objects.get_or_create(member=new_member)
                            if created:
                                logger.debug(f"Created new AuthorDetails for Member ID={new_member.id}")

                            #logger.debug(f"AuthorshipPeriod successfully created for Member ID={new_member.id}")
                        except Exception as e:
                            logger.error(f"Failed to create AuthorshipPeriod for Member ID={new_member.id}: {e}")
                resp['status'] = 'success'
                messages.success(request, 'Member has been saved successfully!')
            else:
                # If form has errors, include them in the response
                logger.error(f"Form is invalid. Errors: {form.errors}")
                resp['status'] = 'failed'
                resp['msg'] = '<br>'.join(
                    f"{form[field_name].label if field_name in form.fields else field_name}: {', '.join(set(errors))}"
                    for field_name, errors in form.errors.items()
                )
        else:
            resp['msg'] = 'No data has been sent.'
        return HttpResponse(json.dumps(resp), content_type='application/json')


class ManageMember(LoginRequiredMixin, View):
    def get(self, request, pk=None):
        context = {
            'page_title': "Manage Member",
            'today': date.today(),
            'countries': Country.objects.all(),
        }

        # Dynamically gather the institutes for each country
        institute_data = {}
        countries = Country.objects.all()
        for country in countries:
            institutes = list(Institute.objects.filter(group__country=country).values('id', 'name', 'group'))
            if institutes:
                institute_data[country.id] = institutes
        context['institute_data'] = json.dumps(institute_data)

        if pk:
            # Retrieve and display a specific member if pk is provided
            #logger.debug(pk)
            try:
                member = Member.objects.get(id=pk)
                context['member'] = member
                current_authorship = member.current_authorship()
                current_membership = member.current_membership()
                if current_membership:
                    context['membership_start'] = current_membership.start_date
                    context['membership_end'] = current_membership.end_date
                else:
                    context['membership_start'] = None
                    context['membership_end'] = None
                # Check if the member is an active author
                context['is_author'] = member.is_active_author()
                if current_authorship:
                    context['authorship_start'] = current_authorship.start_date
                    context['authorship_end'] = current_authorship.end_date
                else:
                    context['authorship_start'] = None
                    context['authorship_end'] = None
                # Future authorship periods
                future_auth_periods = AuthorshipPeriod.objects.filter(
                    member=member, start_date__gt=now()
                ).order_by('start_date')
                context['future_auth_periods'] = future_auth_periods

                context['member_institute'] = member.current_institute()
                context['duties'] = MemberDuty.objects.filter(member=member)
                context['institute_list'] = Institute.objects.all()
                context['is_edit'] = True  # Flag to indicate editing
                return render(request, 'manage_member.html', context)
            except Member.DoesNotExist:
                messages.error(request, "Member not found.")
                return redirect('member-list')
        else:
            context['member'] = {}
            context['roles'] = Member.ROLE_CHOICES
            context['is_edit'] = False  # Flag to indicate adding a new member
        context['institute_list'] = Institute.objects.all()
        return render(request, 'manage_member.html', context)


class Statistics(TemplateView):
    template_name = 'statistics.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()

        # Get countries for filtering options
        country_list = Country.objects.values_list('name', flat=True).order_by('name')

        # Year range for the histogram and filters
        start_year = 2018
        end_year = today.year
        years = range(start_year, end_year + 1)

        #####################################################
        # Calculations total active members and authors for tables
        #####################################################
        # Filter members whose membership is currently active as of today (used in table and cards)
        total_members = Member.objects.filter(
            Q(membership_periods__end_date__isnull=True) | Q(membership_periods__end_date__gt=today),
            membership_periods__start_date__lte=today
        ).distinct().count()

        # Filter authors with a valid authorship period as of today (used in table and cards)
        active_authors = Member.objects.filter(
            authorship_periods__start_date__lte=today
        ).filter(
            Q(authorship_periods__end_date__isnull=True) | Q(authorship_periods__end_date__gt=today)
        ).distinct()
        total_authors = active_authors.count()

        # Members and authors by country with percentage calculations
        countries_data = []
        for country in Country.objects.order_by('name'):
            # Current members in each country as of today (used in table)
            country_members = Member.objects.filter(
                membership_periods__institute__group__country=country,
                membership_periods__start_date__lte=today,
            ).filter(Q(membership_periods__end_date__isnull=True) | Q(membership_periods__end_date__gt=today)).count()

            # Current authors in each country as of today (used in table)
            country_authors = Member.objects.filter(
                membership_periods__institute__group__country=country,
                authorship_periods__start_date__lte=today
            ).filter(Q(authorship_periods__end_date__isnull=True) | Q(authorship_periods__end_date__gt=today)).count()

            # Calculate percentages as of today (used in table)
            member_percentage = (country_members / total_members * 100) if total_members > 0 else 0
            author_percentage = (country_authors / total_authors * 100) if total_authors > 0 else 0

            # Calculate monthly averages for the last 12 months based on the 15th of each month
            avg_members_12 = calculate_12_months_avg(
                Member.objects.filter(membership_periods__institute__group__country=country),
                'membership_periods__start_date',
                today
            )

            avg_authors_12 = calculate_12_months_avg(
                Member.objects.filter(membership_periods__institute__group__country=country),
                'authorship_periods__start_date',
                today
            )

            countries_data.append({
                'country': country.name,
                'members_count': country_members,
                'authors_count': country_authors,
                'member_percentage': member_percentage,
                'author_percentage': author_percentage,
                'avg_members_12': avg_members_12,
                'avg_authors_12': avg_authors_12,
            })

        # Members and authors by group with percentage calculations
        groups_data = []
        for group in Group.objects.order_by('name'):
            # Current members in each group as of today (used in table)
            group_members = Member.objects.filter(
                membership_periods__institute__group=group,
                membership_periods__start_date__lte=today,
            ).filter(Q(membership_periods__end_date__isnull=True) | Q(membership_periods__end_date__gt=today)).count()

            # Current authors in each group as of today (used in table)
            group_authors = Member.objects.filter(
                membership_periods__institute__group=group,
                authorship_periods__start_date__lte=today
            ).filter(Q(authorship_periods__end_date__isnull=True) | Q(authorship_periods__end_date__gt=today)).count()

            # Calculate percentages as of today (used in table)
            member_percentage = (group_members / total_members * 100) if total_members > 0 else 0
            author_percentage = (group_authors / total_authors * 100) if total_authors > 0 else 0

            # Calculate monthly averages for the last 12 months based on the 15th of each month
            avg_members_12 = calculate_12_months_avg(
                Member.objects.filter(membership_periods__institute__group=group),
                'membership_periods__start_date',
                today
            )

            avg_authors_12 = calculate_12_months_avg(
                Member.objects.filter(membership_periods__institute__group=group),
                'authorship_periods__start_date',
                today
            )

            groups_data.append({
                'group': group.name,
                'members_count': group_members,
                'authors_count': group_authors,
                'member_percentage': member_percentage,
                'author_percentage': author_percentage,
                'avg_members_12': avg_members_12,
                'avg_authors_12': avg_authors_12,
            })

        context.update({
            'total_members': total_members,  # for card
            'total_authors': total_authors,  # for card
            'countries_data': countries_data,  # country table
            'groups_data': groups_data,  # group table
            'years_list': list(years),
            'country_list': country_list,
            'current_date': datetime.now().strftime('%B %d, %Y'),  # navbar date
        })
        return context


def get_filtered_chart_data(request):
    """
    Returns average members and authors for the selected filters.
    """
    # Extract filter parameters from GET request
    country_name = request.GET.get('country', None)
    group_name = request.GET.get('group', None)
    institute_name = request.GET.get('institute', None)

    # Initialize base queryset
    queryset = Member.objects.all()
    # Apply filters to the queryset
    if country_name and country_name != 'all':
        queryset = queryset.filter(membership_periods__institute__group__country__name=country_name)
    if group_name:
        queryset = queryset.filter(membership_periods__institute__group__name=group_name)
    if institute_name:
        queryset = queryset.filter(membership_periods__institute__name=institute_name)

    # Determine years range for averages
    today = datetime.now().date()
    current_year = today.year
    years = range(2018, current_year + 1)

    # Compute averages for members and authors per year
    filtered_data = {
        'years': list(years),
        'members': [],
        'authors': [],
    }

    for year in years:
        # Average members
        avg_members = calculate_averages(queryset, "membership_periods__start_date", year, current_year, today.month)

        # Average authors
        avg_authors = calculate_averages(queryset.filter(authorship_periods__start_date__isnull=False),
                                         "authorship_periods__start_date", year, current_year, today.month)

        filtered_data['members'].append(avg_members)
        filtered_data['authors'].append(avg_authors)

    return JsonResponse(filtered_data)


def get_groups(request):
    country_name = request.GET.get('country', None)
    if not country_name:
        return JsonResponse({"error": "Country parameter is missing."}, status=400)

    try:
        groups = Group.objects.filter(country__name=country_name).distinct()
        group_list = [group.name for group in groups]
        return JsonResponse(group_list, safe=False)
    except Group.DoesNotExist:
        return JsonResponse({"error": "No groups found for the specified country."}, status=404)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error fetching groups for country '{country_name}': {str(e)}")
        return JsonResponse({"error": "An error occurred while fetching groups."}, status=500)


def get_institutes(request):
    group_name = request.GET.get('group', None)
    if not group_name:
        return JsonResponse({"error": "Group parameter is missing."}, status=400)

    try:
        institutes = Institute.objects.filter(group__name=group_name).distinct()
        institute_list = [institute.name for institute in institutes]
        return JsonResponse(institute_list, safe=False)
    except Institute.DoesNotExist:
        return JsonResponse({"error": "No institutes found for the specified group."}, status=404)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error fetching institutes for group '{group_name}': {str(e)}")
        return JsonResponse({"error": "An error occurred while fetching institutes."}, status=500)


def get_filtered_monthly_data(request):
    """
    Returns monthly members and authors data for the selected filters (country, group, institute, and year).
    """
    # Extract filter parameters from GET request
    year = int(request.GET.get('year'))  # Convert the year from string to integer
    country = request.GET.get('country', None)
    group = request.GET.get('group', None)
    institute = request.GET.get('institute', None)

    # Get the current year and month
    current_year = datetime.now().year
    current_month = datetime.now().month
    # Determine the last month to calculate data for
    last_month = current_month if year == current_year else 12

    # Initialize base queryset
    queryset = Member.objects.all()

    # Apply filters dynamically
    if country and country != 'all':
        queryset = queryset.filter(membership_periods__institute__group__country__name=country)
    if group:
        queryset = queryset.filter(membership_periods__institute__group__name=group)
    if institute:
        queryset = queryset.filter(membership_periods__institute__name=institute)

    # Calculate monthly data
    # members = [
    #     get_active_member_count(queryset, "membership_periods__start_date", year, month)
    #     for month in range(1, last_month + 1)
    # ]
    # authors = [
    #     get_active_author_count(queryset, year, month)
    #     for month in range(1, last_month + 1)
    # ]
    members = [
        get_active_periods_count(queryset, "membership_periods", year, month)
        for month in range(1, last_month + 1)
    ]
    authors = [
        get_active_periods_count(queryset, "authorship_periods", year, month)
        for month in range(1, last_month + 1)
    ]
    # Fill remaining months with zero for consistency
    members.extend([0] * (12 - last_month))
    authors.extend([0] * (12 - last_month))

    #logger.debug(f"Received filter parameters: Year={year}, Country={country}, Group={group}, Institute={institute}")
    #logger.debug(f"members: {members}, authors: {authors}")
    return JsonResponse({"members": members, "authors": authors})


def get_years(request):
    """
    Returns the list of years available for selection in the dropdown.
    """
    today = datetime.now().date()
    current_year = today.year
    years = range(2018, current_year + 1)
    return JsonResponse({'years': list(years)})


def get_countries(request):
    """
    Returns the list of countries for the selected filters.
    """
    countries = Country.objects.all()
    countries_data = [{'id': country.id, 'name': country.name} for country in countries]
    return JsonResponse({'countries': countries_data})


class AuthorList(LoginRequiredMixin, View):
    def get(self, request):
        today = now().date()

        # Fetch members with active authorships
        authors = Member.objects.prefetch_related(
            'membership_periods__institute__group__country',
            'authorship_periods'
        ).distinct().filter(
            Q(authorship_periods__start_date__lte=today) & (
                Q(authorship_periods__end_date__isnull=True) | Q(authorship_periods__end_date__gte=today)
            )
        )

        author_list = []
        authors_missing_details = []  # To track authors without details
        authors_missing_full_name = []  # To track authors missing full name
        authors_missing_affiliation = []  # To track authors missing affiliation

        for author in authors:
            # Determine active membership
            membership = author.current_membership(include_inactive=True)
            current_institute = membership.institute if membership else None

            # Active authorship period
            authorship_period = author.current_authorship()
            is_author = (
                authorship_period
                and authorship_period.start_date <= today
                and (authorship_period.end_date is None or authorship_period.end_date >= today)
            )

            if is_author:
                main_affiliation = None
                full_name_missing = False
                affiliation_missing = False
                try:
                    # Attempt to fetch author details
                    author_details = author.author_details
                    if author_details:
                        institutes = author_details.ordered_institutes()
                        if institutes:
                            main_affiliation = institutes[0].name  # Get the first institute name
                        else:
                            affiliation_missing = True  # No affiliation found
                        # Check if full name is missing
                        if not author_details.author_name:
                            full_name_missing = True
                except Member.author_details.RelatedObjectDoesNotExist:
                    # Handle the case where there are no author details
                    authors_missing_details.append(author)
                    main_affiliation = 'No Affiliation'

                # Track authors missing full name or affiliation
                if full_name_missing:
                    authors_missing_full_name.append(author)
                if affiliation_missing:
                    authors_missing_affiliation.append(author)

                author_list.append({
                    'pk': author.pk,
                    'name': author.name,
                    'surname': author.surname,
                    'primary_email': author.primary_email,
                    'authorship_start': authorship_period.start_date.strftime('%Y-%m-%d') if authorship_period else None,
                    'authorship_end': authorship_period.end_date.strftime('%Y-%m-%d') if authorship_period and authorship_period.end_date else None,
                    'group_name': current_institute.group.name if current_institute and current_institute.group else 'No Group',
                    'country_name': current_institute.group.country.name if current_institute and current_institute.group and current_institute.group.country else 'No Country',
                    'institute_name': current_institute.name if current_institute else 'No Institute',
                    'main_affiliation': main_affiliation or 'No Affiliation',
                })

        # Data for the filters
        countries = Country.objects.prefetch_related('groups__institutes').order_by('name')
        filters_data = {
            country.name: {
                "groups": {
                    group.name: list(group.institutes.values_list('name', flat=True))
                    for group in country.groups.all()
                }
            }
            for country in countries
        }

        context = {
            'page_title': 'Author List',
            'authors': author_list,
            'author_data': json.dumps(author_list),
            'institutes': list(Institute.objects.order_by('name').values('id', 'name')),
            'groups': list(Group.objects.order_by('name').values('id', 'name')),
            'countries': list(Country.objects.order_by('name').values('id', 'name')),
            'userGroups': list(request.user.groups.values_list('name', flat=True)),
            'filters': filters_data,
            'current_date': now().strftime('%B %d, %Y'),
            'authors_missing_details': authors_missing_details,
            'authors_missing_full_name': authors_missing_full_name,
            'authors_missing_affiliation': authors_missing_affiliation,
        }
        return render(request, 'author_list.html', context)


class AuthorRecord(LoginRequiredMixin, View):
    def get(self, request, pk=None):
        context = {}
        context['page_title'] = 'Author Information'
        if pk is None:
            messages.error(request, "Author ID is not recognized")
            return redirect('author_list')
        else:
            try:
                author = Member.objects.get(id=pk)
            except Member.DoesNotExist:
                messages.error(request, "Author not found")
                return redirect('author_list')

            # Fetch author details
            author_details = getattr(author, 'author_details', None)

            # Fetch current institute, group, and country
            institute = author.current_institute() if author.current_institute() else None
            group = institute.group if institute else None
            country = group.country if group else None

            # Fetch authorship periods
            authorship_periods = author.authorship_periods.order_by('-start_date') if hasattr(author, 'authorship_periods') else []

            context.update({
                'member': author,
                'author_details': author_details,
                'institute': institute,
                'group': group,
                'country': country,
                'authorship_periods': authorship_periods,
            })
            return render(request, 'author_record.html', context)


class ManageAuthor(LoginRequiredMixin, View):
    def get(self, request, pk=None):
        """Fetch and display existing author details."""
        context = {
            'page_title': "Manage Author",
            'today': date.today(),
            #'countries': Country.objects.all(),
        }
        institute_list = Institute.objects.all()
        context['institute_list'] = sorted(institute_list, key=lambda x: x.name)
        if pk:
            # Retrieve and display a specific member if pk is provided
            logger.debug(f"Received pk: {pk}")
            try:
                # Fetch the author details and affiliations
                author_details = AuthorDetails.objects.get(member__id=pk)
                #logger.debug(f"AuthorDetails found: {author_details}")

                context['author_details'] = author_details
                context['member'] = author_details.member

                affiliations = AuthorInstituteAffiliation.objects.filter(author_details=author_details).order_by('order')
                context['affiliations'] = affiliations

                # Set the edit flag
                context['is_edit'] = True

                return render(request, 'manage_author.html', context)
            except AuthorDetails.DoesNotExist:
                # Handle case where author details are not found
                logger.error(f"AuthorDetails with pk {pk} not found.")
                messages.error(request, "Author not found.")
                return redirect('author_list')
            except Exception as e:
                # Log any unexpected exceptions
                logger.exception(f"Error occurred while fetching AuthorDetails: {e}")
                messages.error(request, "An unexpected error occurred.")
                return redirect('author_list')
        else:
            # No pk, setting up for creating a new member
            context['author_details'] = {}
            context['is_edit'] = False  # Flag to indicate adding a new author
            context['institute_list'] = Institute.objects.all()
        return render(request, 'manage_author.html', context)


class AddAuthor(LoginRequiredMixin, View):
    def get(self, request):
        """Render the form for editing an author's details."""
        context = {
            'page_title': "Add Author",
            'today': date.today(),
        }
        return render(request, 'manage_author.html', context)

    def post(self, request, pk=None):
        """Handle the submission of the form."""
        resp = {'status': 'failed', 'msg': ''}
        if request.method == 'POST':
            member_id = request.POST.get('id')
            member = Member.objects.get(id=member_id)
            author_details = AuthorDetails.objects.get(member=member)
            form = AddAuthorDetailsForm(request.POST, instance=author_details)
            #logger.debug(f"POST data: {request.POST}")
            if form.is_valid():
                logger.info(f"Form is valid. Data: {form.cleaned_data}")

                # Save the AuthorDetails instance first
                author_details = form.save()

                # Handle updating affiliations if provided
                affiliations = request.POST.getlist('affiliations[]', [])
                logger.debug(f"Affiliations to be updated: {affiliations}")

                if affiliations:
                    # Clear existing affiliations
                    author_details.institute_affiliations.all().delete()  # Deletes all related AuthorInstituteAffiliation objects

                    for i, affiliation_id in enumerate(affiliations):
                        institute = Institute.objects.filter(id=affiliation_id.strip()).first()  # Use ID for lookup
                        if institute:
                            # Create or update the affiliation
                            affiliation, created = AuthorInstituteAffiliation.objects.get_or_create(
                                author_details=author_details,
                                institute=institute,
                                defaults={'order': i + 1}
                            )
                            if not created:
                                affiliation.order = i + 1
                                affiliation.save()

                author_details.save()
                resp = {'status': 'success'}
                messages.success(request, "Author details updated successfully.")
                #return redirect('author_list')
            else:
                # Log and return form errors
                logger.error(f"Form is invalid. Errors: {form.errors}")
                logger.error(f"Form is invalid. Errors: {form.errors.as_json()}")
                resp['msg'] = '<br>'.join(
                    f"{form[field_name].label if field_name in form.fields else field_name}: {', '.join(set(errors))}"
                    for field_name, errors in form.errors.items()
                )
        else:
            resp['msg'] = 'No data has been sent.'
        return HttpResponse(json.dumps(resp), content_type='application/json')


def generate_aa_email(request):
    """Generates LaTeX for A&A with emails, filtering by authorship validity on a specified date in UTC."""
    selected_date_str = request.GET.get('date')  # Get the selected date from query parameters
    if not selected_date_str:
        return JsonResponse({'error': 'No date provided'}, status=400)

    authors, selected_date, valid_authors = get_valid_authors_for_date(selected_date_str)
    if authors is None:
        return JsonResponse({'error': selected_date}, status=400)

    latex_content = []
    institute_dict = {}
    institute_counter = 1
    institute_lines = []
    missing_authors = []

    # Add warning at the top if there are missing authors
    missing_authors = get_missing_authors(valid_authors)
    if missing_authors:
        latex_content.append("% WARNING: The following members were skipped. They are listed as authors, but no AuthorDetails are available for them, or they are incomplete:\n")
        latex_content.append("% " + ", ".join(missing_authors) + "\n\n")

    # Build institute dictionary and LaTeX content for valid authors
    for author in authors:
        # Skip authors without affiliations or valid names
        if not author.institute_affiliations.exists() or not author.author_name:
            continue
        for affiliation in author.institute_affiliations.all():
            institute = affiliation.institute
            if institute.name not in institute_dict:
                institute_dict[institute.name] = institute_counter
                prefix = "\\and " if institute_counter > 1 else ""
                institute_lines.append(f"{prefix}{institute.long_description}")
                institute_counter += 1

    latex_content.append(f"% AA format\n% Generated on {selected_date.strftime('%Y-%m-%d')}\n")
    latex_content.append("\\author{\n")
    for author in authors:
        if not author.institute_affiliations.exists() or not author.author_name:
            continue
        institute_indices = sorted(
            [institute_dict[aff.institute.name] for aff in author.institute_affiliations.all()]
        )
        indices_str = ",".join(map(str, institute_indices))
        latex_content.append(f"{author.author_name.replace(' ', '~')}\\inst{{{indices_str}}}\\email{{{author.author_email}}} \\and\n")

    latex_content.append("}\n")
    latex_content.append("\\institute{\n")
    latex_content.append("\n".join(institute_lines))
    latex_content.append("}\n")

    # Join the LaTeX content and return as response
    response = HttpResponse("".join(latex_content), content_type="application/x-tex")
    response['Content-Disposition'] = 'attachment; filename=LST_authors_AA_w_emails.tex'
    return response


def generate_aa(request):
    """Generates LaTeX for A&A without emails, filtering by authorship validity on a specified date in UTC."""
    selected_date_str = request.GET.get('date')  # Get the selected date from query parameters
    if not selected_date_str:
        return JsonResponse({'error': 'No date provided'}, status=400)

    authors, selected_date, valid_authors = get_valid_authors_for_date(selected_date_str)
    if authors is None:
        return JsonResponse({'error': selected_date}, status=400)

    latex_content = []
    institute_dict = {}
    institute_counter = 1
    institute_lines = []

    # Add warning at the top if there are missing authors
    missing_authors = get_missing_authors(valid_authors)
    if missing_authors:
        latex_content.append("% WARNING: The following members were skipped. They are listed as authors, but no AuthorDetails are available for them, or they are incomplete:\n")
        latex_content.append("% " + ", ".join(missing_authors) + "\n\n")

    # Build institute dictionary
    for author in authors:
        # Skip authors without affiliations or valid names
        if not author.institute_affiliations.exists() or not author.author_name:
            continue
        for affiliation in author.institute_affiliations.all():
            institute = affiliation.institute
            if institute.name not in institute_dict:
                institute_dict[institute.name] = institute_counter
                prefix = "\\and " if institute_counter > 1 else ""
                institute_lines.append(f"{prefix}{institute.long_description}")
                institute_counter += 1

    latex_content.append(f"% AA format\n% Generated on {selected_date.strftime('%Y-%m-%d')}\n")
    latex_content.append("\\author{\n")
    for author in authors:
        if not author.institute_affiliations.exists() or not author.author_name:
            continue
        institute_indices = sorted(
            [institute_dict[aff.institute.name] for aff in author.institute_affiliations.all()]
        )
        indices_str = ",".join(map(str, institute_indices))
        latex_content.append(f"{author.author_name.replace(' ', '~')}\\inst{{{indices_str}}} \\and\n")

    latex_content.append("}\n")
    latex_content.append("\\institute{\n")
    latex_content.append("\n".join(institute_lines))
    latex_content.append("}\n")

    # Join the LaTeX content and return as response
    response = HttpResponse("".join(latex_content), content_type="application/x-tex")
    response['Content-Disposition'] = 'attachment; filename=LST_authors_AA.tex'
    return response


def generate_apj(request):
    """Generates LaTeX for The Astrophysical Journal (ApJ) without emails, filtering by authorship validity on a specified date in UTC."""
    selected_date_str = request.GET.get('date')  # Get the selected date from query parameters
    if not selected_date_str:
        return JsonResponse({'error': 'No date provided'}, status=400)

    authors, selected_date, valid_authors = get_valid_authors_for_date(selected_date_str)
    if authors is None:
        return JsonResponse({'error': selected_date}, status=400)

    latex_content = []

    # Add warning at the top if there are missing authors
    missing_authors = get_missing_authors(valid_authors)
    if missing_authors:
        latex_content.append("% WARNING: The following members were skipped. They are listed as authors, but no AuthorDetails are available for them, or they are incomplete:\n")
        latex_content.append("% " + ", ".join(missing_authors) + "\n\n")

    latex_content.append("% ApJ format\n")
    latex_content.append(f"% Generated on {selected_date.strftime('%Y-%m-%d')}\n")
    latex_content.append("\\usepackage[T1]{fontenc}\n")

    # Generate LaTeX for authors
    for author in authors:
        # Skip authors without affiliations or valid names
        if not author.institute_affiliations.exists() or not author.author_name:
            continue
        # Get affiliations sorted by the 'order' field
        affiliations = author.institute_affiliations.all().order_by('order')

        # Build author string
        author_name = author.author_name.replace("  ", " ").replace(" ", "~")
        orcid = getattr(author, 'orcid', None)  # Assuming `orcid` is a field in the author model
        if orcid:
            author_string = f"\\author[{orcid}]{{{author_name}}}\n"
        else:
            author_string = f"\\author{{{author_name}}}\n"

        # Add affiliations in the correct order
        for affiliation in affiliations:
            author_string += f"\\affiliation{{{affiliation.institute.long_description}}}\n"

        latex_content.append(author_string)

    # Join and finalize the LaTeX document
    response = HttpResponse("".join(latex_content), content_type="application/x-tex")
    response['Content-Disposition'] = 'attachment; filename=LST_authors_ApJ.tex'
    return response


def generate_arxiv(request):
    """Generates LaTeX for ArXiv without emails, filtering by authorship validity on a specified date in UTC."""
    selected_date_str = request.GET.get('date')  # Get the selected date from query parameters
    if not selected_date_str:
        return JsonResponse({'error': 'No date provided'}, status=400)

    authors, selected_date, valid_authors = get_valid_authors_for_date(selected_date_str)
    if authors is None:
        return JsonResponse({'error': selected_date}, status=400)

    latex_content = []
    institute_dict = {}
    institute_counter = 1
    institute_lines = []

    # Add a warning for missing authors
    missing_authors = get_missing_authors(valid_authors)
    if missing_authors:
        latex_content.append("% WARNING: The following members were skipped. They are listed as authors, but no AuthorDetails are available for them, or they are incomplete:\n")
        latex_content.append("% " + ", ".join(missing_authors) + "\n\n")

    # Add LaTeX header
    latex_content.append("% ArXiv format\n")
    latex_content.append(f"% Generated on {selected_date.strftime('%Y-%m-%d')}\n")
    latex_content.append("CTA-LST Project: ")

    # Build and sort institute dictionary
    for author in authors:
        # Skip authors without affiliations or valid names
        if not author.institute_affiliations.exists() or not author.author_name:
            continue
        affiliations = sorted(
            author.institute_affiliations.all(),
            key=lambda aff: aff.order  # Sort by the 'order' field
        )
        for affiliation in affiliations:
            institute = affiliation.institute
            if institute.name not in institute_dict:
                institute_dict[institute.name] = institute_counter
                institute_lines.append(f"({institute_counter}) {institute.long_description}")
                institute_counter += 1

    # Generate author strings
    author_strings = []
    for author in authors:
        # Skip authors without affiliations or valid names
        if not author.institute_affiliations.exists() or not author.author_name:
            continue
        affiliations = sorted(
            author.institute_affiliations.all(),
            key=lambda aff: aff.order  # Sort by the 'order' field
        )
        institute_indices = sorted([institute_dict[aff.institute.name] for aff in affiliations])
        indices_str = ",".join(map(str, institute_indices))
        author_strings.append(f"{author.author_name} ({indices_str})")

    # Combine authors into a single line
    latex_content.append(", ".join(author_strings))
    latex_content.append("\n")

    # Append institute details
    latex_content.append(" ".join(institute_lines))

    # Finalize LaTeX content and return as a response
    response = HttpResponse("".join(latex_content), content_type="application/x-tex")
    response['Content-Disposition'] = 'attachment; filename=LST_authors_ArXiv.tex'
    return response


def generate_mnras(request):
    """Generates LaTeX for The Monthly Notices of the Royal Astronomy Society (MNRAS) without emails, filtering by authorship validity on a specified date in UTC."""
    selected_date_str = request.GET.get('date')
    if not selected_date_str:
        return JsonResponse({'error': 'No date provided'}, status=400)

    authors, selected_date, valid_authors = get_valid_authors_for_date(selected_date_str)
    if authors is None:
        return JsonResponse({'error': selected_date}, status=400)

    institute_dict = {}
    latex_content = []
    institute_lines = []

    # Add warning for missing authors
    missing_authors = get_missing_authors(valid_authors)
    if missing_authors:
        latex_content.append("% WARNING: The following members were skipped. They are listed as authors, but no AuthorDetails are available for them, or they are incomplete:\n")
        latex_content.append("% " + ", ".join(missing_authors) + "\n\n")

    # Start LaTeX document
    latex_content.append("% MNRAS format\n")
    latex_content.append(f"% Generated on {selected_date.strftime('%Y-%m-%d')}\n")

    # Build and sort institutes for each author
    all_institutes = {}
    for author in authors:
        # Skip authors without affiliations or valid names
        if not author.institute_affiliations.exists() or not author.author_name:
            continue
        affiliations = sorted(
            author.institute_affiliations.all(),
            key=lambda aff: aff.order  # Sort by 'order'
        )
        for affiliation in affiliations:
            institute = affiliation.institute
            if institute.name not in all_institutes:
                all_institutes[institute.name] = institute

    # Assign unique indices to institutes
    for idx, institute in enumerate(all_institutes.values(), start=1):
        institute_dict[institute.name] = idx
        institute_lines.append(f"$^{{{idx}}}$ {{ {institute.long_description} }}\\\\")

    # Generate author strings
    author_lines = []
    for author in authors:
        # Skip authors without affiliations or valid names
        if not author.institute_affiliations.exists() or not author.author_name:
            continue
        affiliations = sorted(
            author.institute_affiliations.all(),
            key=lambda aff: aff.order  # Sort by 'order'
        )
        institute_indices = [institute_dict[aff.institute.name] for aff in affiliations]
        indices_str = ",".join(map(str, institute_indices))
        author_name = author.author_name.replace("  ", " ").replace(" ", "~")
        author_lines.append(f"{author_name} $^{{{indices_str}}}$")

    # Combine authors into the LaTeX structure
    first_author = authors[0].author_name.replace("  ", " ").replace(" ", "~")
    latex_content.append(f"\\author[{first_author}~et.~al.]{{\\parbox{{\\textwidth}}{{\\Large{{\n")
    latex_content.append(",\n".join(author_lines))
    latex_content.append("}}\\\\\n")

    # Add sorted institutes
    latex_content.append("\n".join(institute_lines))
    latex_content.append("}")

    # Finalize LaTeX document
    response = HttpResponse("".join(latex_content), content_type="application/x-tex")
    response['Content-Disposition'] = 'attachment; filename=LST_authors_MNRAS.tex'
    return response


def generate_pos(request):
    """Generates LaTeX for The POS format without emails, ensuring affiliations are in the correct order and formatting institutes properly."""
    selected_date_str = request.GET.get('date')  # Get the selected date from query parameters
    if not selected_date_str:
        return JsonResponse({'error': 'No date provided'}, status=400)

    authors, selected_date, valid_authors = get_valid_authors_for_date(selected_date_str)
    if authors is None:
        return JsonResponse({'error': selected_date}, status=400)

    latex_content = []
    institute_dict = {}
    institute_counter = 1
    institute_lines = []

    # Add warning at the top if there are missing authors
    missing_authors = get_missing_authors(valid_authors)
    if missing_authors:
        latex_content.append("% WARNING: The following members were skipped. They are listed as authors, but no AuthorDetails are available for them, or they are incomplete:\n")
        latex_content.append("% " + ", ".join(missing_authors) + "\n\n")

    latex_content.append("% POS format\n")
    latex_content.append(f"% Generated on {selected_date.strftime('%Y-%m-%d')}\n")

    # Build institute dictionary with corrected formatting
    for author in authors:
        # Skip authors without affiliations or valid names
        if not author.institute_affiliations.exists() or not author.author_name:
            continue
        affiliations = author.institute_affiliations.order_by('order')  # Ensure affiliations are in the correct order
        for affiliation in affiliations:
            institute = affiliation.institute
            if institute.name not in institute_dict:
                institute_dict[institute.name] = institute_counter
                # Correct formatting for institute, keeping {} for the descriptions
                institute_lines.append(f"$^{{{institute_counter}}}${{{institute.long_description}}}.\n")
                institute_counter += 1

    # Write author details
    latex_content.append("\\tiny{\\noindent\n")
    for i, author in enumerate(authors):
        # Skip authors without affiliations or valid names
        if not author.institute_affiliations.exists() or not author.author_name:
            continue
        affiliations = author.institute_affiliations.order_by('order')  # Ensure affiliations are in the correct order
        if not affiliations:
            print(f"Author {author.author_name} has no affiliation!")
            continue

        # Generate indices in the correct order (only one set of curly braces for the indices)
        institute_indices = [institute_dict[aff.institute.name] for aff in affiliations]
        indices_str = ",".join(map(str, institute_indices))
        author_string = f"{author.author_name.replace(' ', '~')}$^{{{indices_str}}}$"  # Correct LaTeX format

        # Add comma if not the last author
        if i < len(authors) - 1:
            author_string += ",\n"
        else:
            author_string += "\n"

        latex_content.append(author_string)

    latex_content.append("}\\\\\n\n")
    latex_content.append("\\tiny{\\noindent")
    latex_content.append("".join(institute_lines))
    latex_content.append("}")

    # Join the LaTeX content and return as response
    response = HttpResponse("".join(latex_content), content_type="application/x-tex")
    response['Content-Disposition'] = 'attachment; filename=LST_authors_POS.tex'
    return response


def generate_nature(request):
    """Generates LaTeX for the Nature format, filtering by authorship validity on a specified date in UTC."""
    selected_date_str = request.GET.get('date')  # Get the selected date from query parameters
    if not selected_date_str:
        return JsonResponse({'error': 'No date provided'}, status=400)

    authors, selected_date, valid_authors = get_valid_authors_for_date(selected_date_str)
    if authors is None:
        return JsonResponse({'error': selected_date}, status=400)

    latex_content = []
    institute_dict = {}
    institute_counter = 1
    institute_lines = []

    # Add warning at the top if there are missing authors
    missing_authors = get_missing_authors(valid_authors)
    if missing_authors:
        latex_content.append("% WARNING: The following members were skipped. They are listed as authors, but no AuthorDetails are available for them, or they are incomplete:\n")
        latex_content.append("% " + ", ".join(missing_authors) + "\n\n")

    latex_content.append("% Nature format\n")
    latex_content.append(f"% Generated on {selected_date.strftime('%Y-%m-%d')}\n")

    # Build institute dictionary
    for author in authors:
        # Skip authors without affiliations or valid names
        if not author.institute_affiliations.exists() or not author.author_name:
            continue
        for affiliation in author.institute_affiliations.all():
            institute = affiliation.institute
            if institute.name not in institute_dict:
                institute_dict[institute.name] = institute_counter
                institute_lines.append(f"\\normalsize{{$^{{{institute_counter}}}$ {{{institute.long_description}}},}}\\\\\n")
                institute_counter += 1

    # Write author details
    for index, author in enumerate(authors):
        # Skip authors without affiliations or valid names
        if not author.institute_affiliations.exists() or not author.author_name:
            continue
        author_name = author.author_name.replace("  ", " ").replace(" ", "~")
        number_of_affiliations = len(author.institute_affiliations.all())

        if number_of_affiliations == 0:
            print(f"Author {author_name} has no affiliation!")
            continue  # Or handle this case more explicitly

        author_string = f"{author_name} $^{{"
        institute_indices = sorted(
            [institute_dict[aff.institute.name] for aff in author.institute_affiliations.all()]
        )
        author_string += ",".join(str(idx) for idx in institute_indices) + "}$"

        if index != len(authors) - 1:
            author_string += ",\n"
        else:
            author_string += "\n\\\\\n"

        latex_content.append(author_string)

    # Add institute details
    latex_content.append("".join(institute_lines))

    # Join the LaTeX content and return as response
    response = HttpResponse("".join(latex_content), content_type="application/x-tex")
    response['Content-Disposition'] = 'attachment; filename=LST_authors_Nature.tex'
    return response


def generate_science(request):
    """Generates LaTeX for the Science format, filtering by authorship validity on a specified date in UTC."""
    selected_date_str = request.GET.get('date')  # Get the selected date from query parameters
    if not selected_date_str:
        return JsonResponse({'error': 'No date provided'}, status=400)

    authors, selected_date, valid_authors = get_valid_authors_for_date(selected_date_str)
    if authors is None:
        return JsonResponse({'error': selected_date}, status=400)

    latex_content = []
    institute_dict = {}
    institute_counter = 1
    institute_lines = []

    # Add warning at the top if there are missing authors
    missing_authors = get_missing_authors(valid_authors)
    if missing_authors:
        latex_content.append("% WARNING: The following members were skipped. They are listed as authors, but no AuthorDetails are available for them, or they are incomplete:\n")
        latex_content.append("% " + ", ".join(missing_authors) + "\n\n")

    latex_content.append("% Science format\n")
    latex_content.append(f"% Generated on {selected_date.strftime('%Y-%m-%d')}\n")

    # Build institute dictionary
    for author in authors:
        # Skip authors without affiliations or valid names
        if not author.institute_affiliations.exists() or not author.author_name:
            continue
        for affiliation in author.institute_affiliations.all():
            institute = affiliation.institute
            if institute.name not in institute_dict:
                institute_dict[institute.name] = institute_counter
                institute_lines.append(f"\\normalsize{{${{{institute_counter}}}$ {{{institute.long_description}}},}}\\\\\n")
                institute_counter += 1

    # Write author details
    for index, author in enumerate(authors):
        # Skip authors without affiliations or valid names
        if not author.institute_affiliations.exists() or not author.author_name:
            continue
        author_name = author.author_name.replace("  ", " ").replace(" ", "~")
        number_of_affiliations = len(author.institute_affiliations.all())

        if number_of_affiliations == 0:
            print(f"Author {author_name} has no affiliation!")
            continue  # Or handle this case more explicitly

        author_string = f"{author_name} $^{{"
        institute_indices = sorted(
            [institute_dict[aff.institute.name] for aff in author.institute_affiliations.all()]
        )
        author_string += ",".join(str(idx) for idx in institute_indices) + "}$"

        if index != len(authors) - 1:
            author_string += ",\n"
        else:
            author_string += "\n\\\\\n"

        latex_content.append(author_string)

    # Add institute details
    latex_content.append("".join(institute_lines))

    # Join the LaTeX content and return as response
    response = HttpResponse("".join(latex_content), content_type="application/x-tex")
    response['Content-Disposition'] = 'attachment; filename=LST_authors_Science.tex'
    return response


class InstituteList(LoginRequiredMixin, View):
    def get(self, request):
        # Fetch institutes with related group and country
        institutes = Institute.objects.select_related('group__country').all()

        # Optional filtering based on the LST flag
        show_all = request.GET.get('show_all', 'false').lower() == 'true'
        # Filter out non-LST institutes if show_all is False
        if not show_all:
            institutes = institutes.filter(is_lst=True)

        institute_list = []

        for institute in institutes:
            # Extract related data (group and country)
            group_name = institute.group.name if institute.group else 'No Group'
            country_name = institute.group.country.name if institute.group and institute.group.country else 'No Country'

            # Add the institute details to the list
            institute_list.append({
                'pk': institute.pk,
                'name': institute.name,
                'long_name': institute.long_name,
                'group_name': group_name,
                'country_name': country_name,
                'long_description': institute.long_description,
                'is_lst': "Yes" if institute.is_lst else "No",
            })

        # Data for the filters (countries, groups, institutes)
        countries = Country.objects.prefetch_related('groups__institutes').order_by('name')
        filters_data = {
            country.name: {
                "groups": {
                    group.name: list(
                        group.institutes.values_list('name', flat=True)
                        if show_all else
                        group.institutes.filter(is_lst=True).values_list('name', flat=True)
                    )
                    for group in country.groups.all()
                }
            }
            for country in countries
        }

        context = {
            'page_title': 'Institute List',
            'institutes': institute_list,
            'institute_data': json.dumps(institute_list),
            'groups': list(Group.objects.order_by('name').values('id', 'name')),
            'countries': list(Country.objects.order_by('name').values('id', 'name')),
            'filters': filters_data,
            'current_date': timezone.now().strftime('%B %d, %Y'),
            'show_all': show_all,
        }
        return render(request, 'institute_list.html', context)


class InstituteRecord(LoginRequiredMixin, View):
    def get(self, request, pk=None):
        context = {}
        context['page_title'] = 'Institute Information'

        if pk is None:
            messages.error(request, "Institute ID is not recognized")
            return redirect('institute_list')  # Adjust 'institute_list' to your relevant URL name

        try:
            institute = Institute.objects.get(id=pk)
        except Institute.DoesNotExist:
            messages.error(request, "Institute not found")
            return redirect('institute_list')  # Adjust 'institute_list' to your relevant URL name

        # Get the related group and country information
        group = institute.group if institute.group else None
        country = group.country if group else None

        # Add to context the institute details along with the group and country information
        context.update({
            'institute': institute,
            'group': group,
            'country': country,
        })
        return render(request, 'institute_record.html', context)


class ManageInstitute(LoginRequiredMixin, View):
    def get(self, request, pk=None):
        context = {
            'page_title': "Manage Institute",
            'countries': Country.objects.all(),
            'groups': Group.objects.all(),
            'today': date.today(),
        }

        if pk:
            # Retrieve and display a specific ember institute
            try:
                institute = Institute.objects.get(id=pk)
                context['institute'] = institute
                context['is_edit'] = True  # Flag to indicate editing
                # Set the selected group and its associated country
                context['selected_group_country'] = institute.group.country if institute.group else None
            except Institute.DoesNotExist:
                messages.error(request, "Institute not found.")
                return redirect('institute_list')
        else:
            context['institute'] = {}
            context['is_edit'] = False  # Flag to indicate adding a new institute
            context['selected_group_country'] = None
        return render(request, 'manage_institute.html', context)


class AddInstitute(LoginRequiredMixin, View):
    def get_inst(self, institute_id):
        """Retrieve an existing institute or return None if ID is not provided or invalid."""
        if institute_id and institute_id.isnumeric():
            return Institute.objects.filter(pk=institute_id).first()
        return None

    def get(self, request):
        context = {
            'page_title': "Add Institute",
            'today': date.today(),
            'countries': Country.objects.all(),
            'groups': Group.objects.all(),  # For the group dropdown
        }
        return render(request, 'manage_institute.html', context)

    def post(self, request, pk=None):
        resp = {'status': 'failed', 'msg': ''}
        if request.method == 'POST':
            institute_id = request.POST.get('id')
            institute = self.get_inst(institute_id)
            logger.debug(f"Received institute ID: {institute_id}")
            form = AddInstituteForm(request.POST, instance=institute)

            if form.is_valid():
                logger.info(f"Form is valid. Data: {form.cleaned_data}")
                new_inst = form.save(commit=False)
                # Extract form data
                name = form.cleaned_data['name']
                long_name = form.cleaned_data['long_name']
                long_description = form.cleaned_data['long_description']
                group = form.cleaned_data['group']
                #group = Group.objects.filter(id=group_id).first() if group_id else None
                # If no group is selected, set to None
                if not group:
                    group = None
                is_lst = request.POST.get('is_lst') == 'on'

                if institute:
                    # Update the existing institute
                    institute.name = name
                    institute.long_name = long_name
                    institute.long_description = long_description
                    institute.group = group
                    institute.is_lst = is_lst
                    institute.save()
                    resp = {'status': 'success'}
                    messages.success(request, "Institute updated successfully.")
                else:
                    new_inst.save()  # Save the new_institute instance
                    logger.debug(f"New institute saved: {new_inst.id}, {new_inst.name}")
                    resp = {'status': 'success'}
                    messages.success(request, "Institute added successfully.")
            else:
                # If form has errors, include them in the response
                logger.error(f"Form is invalid. Errors: {form.errors}")
                resp['status'] = 'failed'
                resp['msg'] = '<br>'.join([
                    f"{form[field_name].label if field_name in form.fields else field_name}: {', '.join(set(errors))}"
                    for field_name, errors in form.errors.items()
                ])
        else:
            resp['msg'] = 'No data has been sent.'
        return HttpResponse(json.dumps(resp), content_type='application/json')
