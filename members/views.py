from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from .forms import LoginForm
from django.views.generic import TemplateView
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Member, Institute, Group, Duty, Country, MemberDuty
from .forms import AddMemberForm
from datetime import date
from django.contrib.auth.models import User
from django.http import HttpResponse
import json
import logging
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Q


logger = logging.getLogger(__name__)


def logout_user(request):
    logout(request)
    messages.success(request, "You Have Been Logged Out...")
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
        six_months_ago = timezone.now() - timedelta(days=6 * 30)
        # Count of members who joined within the last six months and have an authorship start date
        members_becoming_authors = Member.objects.filter(start_date__gte=six_months_ago, authorship_start__isnull=False).count()
        # Count of non-members (with an end date in the past) who still have an active authorship period (authorship end date is in the future).
        non_members_with_authorship = Member.objects.filter(end_date__lt=timezone.now(), authorship_end__gt=today).count()
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
            'total_institutes': total_institutes,
            'total_groups': total_groups,
            'total_countries': total_countries,
            'institutes_per_country': institutes_per_country,
            'groups_per_country': groups_per_country,
        })
        return context


class MemberList(LoginRequiredMixin, View):
    def get(self, request):
        # Fetch all members with related data
        members = Member.objects.all().select_related('institute', 'institute__group__country')
        member_list = []
        today = date.today()

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
                'authorship_start': member.authorship_start.strftime('%Y-%m-%d') if member.authorship_start else None,
                'authorship_end': member.authorship_end.strftime('%Y-%m-%d') if member.authorship_end else None,
                'group_name': member.institute.group.name if member.institute and member.institute.group else 'No Group',
                'country_name': member.institute.group.country.name if member.institute and member.institute.group and member.institute.group.country else 'No Country',
                'institute_name': member.institute.name if member.institute else 'No Institute',
            })

        member_json = json.dumps(member_list)

        context = {
            'page_title': 'Member List',
            'members': member_list,
            'member_data': member_json,
            'duties': list(Duty.objects.order_by('name').values('id', 'name')),
            'institutes': list(Institute.objects.order_by('name').values('id', 'name')),
            'groups': list(Group.objects.order_by('name').values('id', 'name')),
            'countries': list(Country.objects.order_by('name').values('id', 'name')),
            'userGroups': list(request.user.groups.values_list('name', flat=True)),
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
                return render(request, 'manage_member.html', context)
            except Member.DoesNotExist:
                messages.error(request, "Member not found.")
                return redirect('member-list')
        else:
            context['member'] = {}
            context['roles'] = Member.ROLE_CHOICES

        context['institute_list'] = Institute.objects.all()
        # Return the context to the template for rendering
        return render(request, 'manage_member.html', context)


class Statistics(TemplateView):
    template_name = 'statistics.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()

        # Year range for the histogram
        start_year = 2018
        end_year = today.year
        years = range(start_year, end_year + 1)

        # Structure to hold monthly member and author counts
        year_data = {year: {'members': [], 'authors': []} for year in years}

        # Monthly member and author counts
        for year in years:
            for month in range(1, 13):
                check_date = datetime(year, month, 15).date()

                # Members active on the 15th of the month
                monthly_member_count = Member.objects.filter(
                    start_date__lte=check_date,
                ).filter(
                    Q(end_date__isnull=True) | Q(end_date__gt=check_date)
                ).count()

                # Authors active on the 15th of the month
                monthly_author_count = Member.objects.filter(
                    authorship_start__lte=check_date,
                ).filter(
                    Q(authorship_end__isnull=True) | Q(authorship_end__gt=check_date)
                ).count()

                print(f"Year: {year}, Month: {month}, Members: {monthly_member_count}, Authors: {monthly_author_count}")
                # Append monthly counts
                year_data[year]['members'].append(monthly_member_count)
                year_data[year]['authors'].append(monthly_author_count)

        # Calculate yearly averages for members and authors
        year_averages = []
        member_averages = []
        author_averages = []
        for year, data in year_data.items():
            avg_members = sum(data['members']) / 12
            avg_authors = sum(data['authors']) / 12
            year_averages.append({
                'year': year,
                'avg_members': avg_members,
                'avg_authors': avg_authors
            })
            member_averages.append(avg_members)
            author_averages.append(avg_authors)
            print(f"Year: {year}, Avg Members: {avg_members}, Avg Authors: {avg_authors}")

        # Lists for years, members and authors (monthly data)
        years_list = list(years)
        members_count_list = [data['members'] for data in year_data.values()]  # Monthly counts for members
        authors_count_list = [data['authors'] for data in year_data.values()]  # Monthly counts for authors

        #####################################################
        # Calculations for total active members and authors
        #####################################################
        # Filter members whose membership is currently active
        total_members = (Member.objects.filter(end_date__gt=today) | Member.objects.filter(end_date__isnull=True)).count()
        # Filter authors with a valid authorship period
        total_authors = Member.objects.filter(authorship_start__lte=today).filter(
            Q(authorship_end__isnull=True) | Q(authorship_end__gt=today)
        ).count()
        print(f"Total Members: {total_members}")
        print(f"Total Authors: {total_authors}")
        # Members and authors by country with percentage calculations
        countries_data = []
        for country in Country.objects.order_by('name'):
            # Current members in each country
            country_members = Member.objects.filter(
                institute__group__country=country,
                start_date__lte=today,
                # end_date__gt=today
            ).filter(Q(end_date__isnull=True) | Q(end_date__gt=today)).count()

            # Current authors in each country
            country_authors = Member.objects.filter(
                institute__group__country=country,
                authorship_start__lte=today
            ).filter(Q(authorship_end__isnull=True) | Q(authorship_end__gt=today)).count()

            # Calculate percentages
            member_percentage = (country_members / total_members * 100) if total_members > 0 else 0
            author_percentage = (country_authors / total_authors * 100) if total_authors > 0 else 0

            countries_data.append({
                'country': country.name,
                'members_count': country_members,
                'authors_count': country_authors,
                'member_percentage': member_percentage,
                'author_percentage': author_percentage,
            })

        # Get lists for filtering options
        country_list = Country.objects.values_list('name', flat=True).order_by('name')
        # Retrieve all countries and their groups
        countries_groups = {
            country.name: list(Group.objects.filter(country=country).values_list('name', flat=True))
            for country in Country.objects.all()
        }

        # Retrieve all groups and their institutes
        groups_institutes = {
            group.name: list(Institute.objects.filter(group=group).values_list('name', flat=True))
            for group in Group.objects.all()
        }


        context.update({
            'total_members': total_members,
            'total_authors': total_authors,
            'countries_data': countries_data,
            'member_averages': member_averages,
            'author_averages': author_averages,
            'year_averages': year_averages,
            'years_list': years_list,
            'members_count_list': members_count_list,  # Monthly counts for members
            'authors_count_list': authors_count_list,  # Monthly counts for authors
            'country_list': country_list,
            'countries_groups': countries_groups,
            'groups_institutes': groups_institutes,
        })
        return context
