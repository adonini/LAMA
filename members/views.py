from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from .forms import LoginForm
from django.views.generic import TemplateView
from django.shortcuts import render
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Member, Institute, Group, Duty, Country
from django.http import JsonResponse
from .forms import AddMemberForm
from datetime import date
from django.contrib.auth.models import User
from django.http import HttpResponse
import json
import logging

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
        return context


class MemberList(LoginRequiredMixin, View):
    def get(self, request):
        members = Member.objects.all().select_related('institute')
        member_list = list(members.values(
            'name',
            'surname',
            'primary_email',
            'start_date',
            'end_date',
            'role',
            'institute_id',
        ))

        # fetch related group and country for each member
        for member in member_list:
            institute = Institute.objects.filter(id=member['institute_id']).select_related('group__country').first()
            if institute:
                # Add group and country data to each member
                member['institute_name'] = institute.name
                member['group_name'] = institute.group.name if institute.group else None
                member['country_name'] = institute.group.country.name if institute.group and institute.group.country else None
            else:
                # If no institute found, assign default values
                member['institute_name'] = 'N/A'
                member['group_name'] = 'N/A'
                member['country_name'] = 'N/A'

        # Format dates
        for member in member_list:
            member['start_date'] = str(member['start_date'])
            member['end_date'] = str(member['end_date']) if member['end_date'] else 'N/A'

        member_json = json.dumps(member_list)

        context = {
            'page_title': 'Member List',
            'members': members,
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
            duties = Duty.objects.filter(member=member)
            role = member.role if member.role else 'No role assigned'
            # Get the institutes and their related group information
            institute = member.institute if member.institute else 'No institute assigned'
            group = institute.group if institute else 'No group assigned'
            country = group.country if group else 'No country assigned'
            # Get the member's historical duties if any
            historical_duties = []
            if member.duty:
                historical_duties = Duty.objects.filter(member=member).order_by('start_date')

            context['member'] = member
            context['duties'] = duties
            context['role'] = role
            context['institute'] = institute
            context['group'] = group
            context['country'] = country
            context['historical_duties'] = historical_duties
            return render(request, 'member_record.html', context)


class AddMember(LoginRequiredMixin, View):
    def post(self, request):
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
            try:
                member = Member.objects.get(id=pk)
                context['member'] = member
                context['duties'] = Duty.objects.filter(member=member)
            except Member.DoesNotExist:
                messages.error(request, "Member not found.")
                return redirect('member-list')
        else:
            context['member'] = {}
            context['roles'] = Member.ROLE_CHOICES

        context['institutes'] = Institute.objects.all()
        # Return the context to the template for rendering
        return render(request, 'manage_member.html', context)
