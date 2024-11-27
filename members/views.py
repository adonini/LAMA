import json
import logging
from datetime import date, datetime
from .forms import LoginForm, AddMemberForm
from .models import Member, Institute, Group, Duty, Country, MemberDuty
from dateutil.relativedelta import relativedelta
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.views.generic import TemplateView
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.db.models import Q
from django.utils.timezone import now


logger = logging.getLogger(__name__)


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
                                .filter(Q(end_date__isnull=True) | Q(end_date__gt=month_date)) \
                                .count()
        months_data.append(monthly_count)
    # Calculate the average over the 12 months
    return sum(months_data) / len(months_data) if months_data else 0


def calculate_averages(queryset, date_field, year, current_year, current_month):
    """
    Calculates the average count of members or authors for a specific year, considering data on the 15th of each month.
    If the requested year is the current year, the calculation is based on the months up to the current month.
    If it's a previous year, the calculation considers all 12 months of that year.
    The function filters the queryset for each month, counting members or authors who are active on the 15th
    of each month, based on the provided `date_field` (e.g., membership 'start_date' or 'authorship_start').
    Args:
        queryset: The queryset of members or authors to be counted.
        date_field: The date field used to filter the data (e.g., membership 'start_date' or 'authorship_start').
        year: The year for which the average is being calculated.
        current_year: The current year, used to adjust the calculation if the requested year is the current one.
        current_month: The current month, used to limit the months considered for the current year.
    Returns:
        float: The average count of members or authors for the specified year.
    """
    months = range(1, (current_month + 1) if year == current_year else 13)
    total = sum(
        queryset.filter(**{f"{date_field}__lte": datetime(year, month, 15)})
        .filter(Q(end_date__isnull=True) | Q(end_date__gt=datetime(year, month, 15)))
        .count()
        for month in months
    )
    divisor = current_month if year == current_year else 12
    return total / divisor if divisor > 0 else 0


def get_active_member_count(queryset, date_field, year, month):
    check_date = datetime(year, month, 15).date()
    return queryset.filter(**{f"{date_field}__lte": check_date}).filter(
        Q(end_date__isnull=True) | Q(end_date__gt=check_date)
    ).count()


def get_active_author_count(queryset, year, month):
    check_date = datetime(year, month, 15).date()
    return queryset.filter(authorship_start__lte=check_date).filter(
        Q(authorship_end__isnull=True) | Q(authorship_end__gt=check_date)
    ).count()


class Index(TemplateView):
    template_name = 'login/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Calculate the total counts
        today = timezone.now().date()
        # Count of active members, defined as those with no end date or an end date in the future
        total_members = (Member.objects.filter(end_date__gt=today) | Member.objects.filter(end_date__isnull=True)).count()
        # Count of members who have an authorship start date on or before today and either no authorship end date or an authorship end date in the future
        total_authors = Member.objects.filter(authorship_start__lte=today).filter(
            Q(authorship_end__isnull=True) | Q(authorship_end__gt=today)
        ).count()
        # Calculate a date six months ago from today, approximating a month as 30 days
        six_months_ago = timezone.now() - relativedelta(months=6)
        six_months_future = timezone.now() + relativedelta(months=6)
        # Count of members who joined within the last six months and have an authorship start date
        members_becoming_authors = Member.objects.filter(start_date__gte=six_months_ago, authorship_start__isnull=False).count()
        # Count of non-members (with an end date in the past) who still have an active authorship period (authorship end date is in the future).
        non_members_with_authorship = Member.objects.filter(end_date__lt=timezone.now(), authorship_end__gt=today).count()
        # Count of all people leaving auth in the next 6 months
        people_leaving_authorship = Member.objects.filter(authorship_end__gt=today, authorship_end__lt=six_months_future).count()
        # Count members contributing to CF
        cf = Member.objects.filter(authorship_start__lte=six_months_future).filter(
            Q(authorship_end__isnull=True) | Q(authorship_end__gt=six_months_future)
        ).count()
        total_institutes = Institute.objects.count()
        total_groups = Group.objects.count()
        total_countries = Country.objects.count()
        # Count institutes and groups per country
        institutes_per_country = {}
        groups_per_country = {}
        for country in Country.objects.all():
            institutes_per_country[country.name] = Institute.objects.filter(group__country=country).count()
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
        # Fetch all members with related data
        members = Member.objects.all().select_related('institute', 'institute__group__country')
        member_list = []
        today = date.today()
        six_months_future = (now() + relativedelta(months=6)).date()  # Convert to date

        for member in members:
            # Calculate is_author status
            # Initialize as False
            is_author = False

            # Authorship start must exist to define is_author
            if member.authorship_start:
                if (member.authorship_start < today and (member.authorship_end is None or member.authorship_end > today)):
                    is_author = True

            # Update and save the is_author field only if it has changed
            if member.is_author != is_author:
                member.is_author = is_author
                member.save()

            # Check if the member is contributing to CF
            is_cf = (member.authorship_start and member.authorship_start <= six_months_future and (member.authorship_end is None or member.authorship_end > six_months_future))

            # Prepare the dictionary for JSON serialization
            member_list.append({
                'pk': member.pk,
                'name': member.name,
                'surname': member.surname,
                'primary_email': member.primary_email,
                'start_date': str(member.start_date),
                'end_date': str(member.end_date) if member.end_date else None,
                'role': member.role,
                'is_author': member.is_author,
                'is_cf': is_cf,
                'authorship_start': member.authorship_start.strftime('%Y-%m-%d') if member.authorship_start else None,
                'authorship_end': member.authorship_end.strftime('%Y-%m-%d') if member.authorship_end else None,
                'group_name': member.institute.group.name if member.institute and member.institute.group else 'No Group',
                'country_name': member.institute.group.country.name if member.institute and member.institute.group and member.institute.group.country else 'No Country',
                'institute_name': member.institute.name if member.institute else 'No Institute',
            })

        member_json = json.dumps(member_list)

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
            'page_title': 'Member List',
            'members': member_list,
            'member_data': member_json,
            'duties': list(Duty.objects.order_by('name').values('id', 'name')),
            'institutes': list(Institute.objects.order_by('name').values('id', 'name')),
            'groups': list(Group.objects.order_by('name').values('id', 'name')),
            'countries': list(Country.objects.order_by('name').values('id', 'name')),
            'userGroups': list(request.user.groups.values_list('name', flat=True)),
            'filters': filters_data,
            'current_date': datetime.now().strftime('%B %d, %Y')
        }

        # Render the template with context data
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
            # Fetch related duties and roles for the member
            duties = MemberDuty.objects.filter(member=member)
            role = member.role if member.role else 'No role assigned'
            # Get the institutes and their related group information
            institute = member.institute if member.institute else 'No institute assigned'
            group = institute.group if institute else 'No group assigned'
            country = group.country if group else 'No country assigned'
            # Get the member's historical duties if any
            historical_duties = []
            if MemberDuty.objects.filter(member=member):
                historical_duties = MemberDuty.objects.filter(member=member).order_by('start_date')

            context['member'] = member
            context['duties'] = duties
            context['role'] = role
            context['institute'] = institute
            context['group'] = group
            context['country'] = country
            context['historical_duties'] = historical_duties
            context['institutes'] = Institute.objects.all()
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
        # Return the context to the template for rendering
        return render(request, 'manage_member.html', context)

    def post(self, request, pk=None):
        resp = {'status': 'failed', 'msg': ''}
        currentUser = User.objects.get(username=request.user)
        if request.method == 'POST':
            if request.POST['id'].isnumeric():
                member = Member.objects.get(pk=request.POST['id'])
            else:
                member = None
            if member is None:
                form = AddMemberForm(request.POST)
            else:
                form = AddMemberForm(request.POST, instance=member)

            if form.is_valid():
                # Saving the member instance
                newMember = form.save(commit=False)
                if not form.cleaned_data['end_date']:
                    newMember.end_date = None

                if 'is_author' in request.POST:
                    newMember.is_author = True
                    newMember.authorship_start = request.POST.get('authorship_start') or None
                    newMember.authorship_end = request.POST.get('authorship_end') or None
                else:
                    newMember.is_author = False
                    newMember.authorship_start = None
                    newMember.authorship_end = None
                newMember.save()
                messages.success(request, 'Member has been saved successfully!')
                resp['status'] = 'success'
            else:
                # If form has errors, display them
                for fields in form:
                    for error in fields.errors:
                        resp['msg'] += f"{fields.label}: {error}<br>"
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
            logger.debug(pk)
            try:
                member = Member.objects.get(id=pk)
                context['member'] = member
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
        # Return the context to the template for rendering
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
        total_members = (Member.objects.filter(end_date__gt=today) | Member.objects.filter(end_date__isnull=True)).count()
        # Filter authors with a valid authorship period as of today (used in table and cards)
        total_authors = Member.objects.filter(authorship_start__lte=today).filter(
            Q(authorship_end__isnull=True) | Q(authorship_end__gt=today)
        ).count()

        # Members and authors by country with percentage calculations
        countries_data = []
        for country in Country.objects.order_by('name'):
            # Current members in each country as of today (used in table)
            country_members = Member.objects.filter(
                institute__group__country=country,
                start_date__lte=today,
            ).filter(Q(end_date__isnull=True) | Q(end_date__gt=today)).count()

            # Current authors in each country as of today (used in table)
            country_authors = Member.objects.filter(
                institute__group__country=country,
                authorship_start__lte=today
            ).filter(Q(authorship_end__isnull=True) | Q(authorship_end__gt=today)).count()

            # Calculate percentages as of today (used in table)
            member_percentage = (country_members / total_members * 100) if total_members > 0 else 0
            author_percentage = (country_authors / total_authors * 100) if total_authors > 0 else 0

            # Calculate monthly averages for the last 12 months based on the 15th of each month
            avg_members_12 = calculate_12_months_avg(
                Member.objects.filter(institute__group__country=country),
                'start_date',
                today
            )

            avg_authors_12 = calculate_12_months_avg(
                Member.objects.filter(institute__group__country=country),
                'authorship_start',
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
                institute__group=group,
                start_date__lte=today,
            ).filter(Q(end_date__isnull=True) | Q(end_date__gt=today)).count()

            # Current authors in each group as of today (used in table)
            group_authors = Member.objects.filter(
                institute__group=group,
                authorship_start__lte=today
            ).filter(Q(authorship_end__isnull=True) | Q(authorship_end__gt=today)).count()

            # Calculate percentages as of today (used in table)
            member_percentage = (group_members / total_members * 100) if total_members > 0 else 0
            author_percentage = (group_authors / total_authors * 100) if total_authors > 0 else 0

            # Calculate monthly averages for the last 12 months based on the 15th of each month
            avg_members_12 = calculate_12_months_avg(
                Member.objects.filter(institute__group=group),
                'start_date',
                today
            )

            avg_authors_12 = calculate_12_months_avg(
                Member.objects.filter(institute__group=group),
                'authorship_start',
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

    # Apply filters dynamically
    if country_name and country_name != 'all':
        queryset = queryset.filter(institute__group__country__name=country_name)

    if group_name:
        queryset = queryset.filter(institute__group__name=group_name)

    if institute_name:
        queryset = queryset.filter(institute__name=institute_name)

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
        avg_members = calculate_averages(queryset, "start_date", year, current_year, today.month)

        # Average authors
        avg_authors = calculate_averages(queryset.filter(authorship_start__isnull=False),
                                         "authorship_start", year, current_year, today.month)

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
    year = request.GET.get('year')
    country = request.GET.get('country', None)
    group = request.GET.get('group', None)
    institute = request.GET.get('institute', None)

    # Initialize base queryset
    queryset = Member.objects.all()

    # Apply filters dynamically
    if country and country != 'all':
        queryset = queryset.filter(institute__group__country__name=country)
    if group:
        queryset = queryset.filter(institute__group__name=group)
    if institute:
        queryset = queryset.filter(institute__name=institute)

    # Calculate monthly data
    members = [
        get_active_member_count(queryset, "start_date", int(year), month)
        for month in range(1, 13)
    ]
    authors = [
        get_active_author_count(queryset, int(year), month)
        for month in range(1, 13)
    ]
    logger = logging.getLogger(__name__)
    logger.debug(f"Received filter parameters: Year={year}, Country={country}, Group={group}, Institute={institute}")
    logger.debug(f"members: {members}, authors: {authors}")
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
