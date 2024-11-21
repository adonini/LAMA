from django import forms
from django.contrib.auth.forms import AuthenticationForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from .models import Member, Institute, Group, Duty, Country


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super(LoginForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('login', 'Login'))


class AddMemberForm(forms.ModelForm):
    institute = forms.ModelChoiceField(queryset=Institute.objects.all(), initial=0, required=True)
    group = forms.ModelChoiceField(queryset=Group.objects.all(), initial=0, required=False)
    country = forms.ModelChoiceField(queryset=Country.objects.all(), initial=0, required=False)
    role = forms.ChoiceField(choices=Member.ROLE_CHOICES, required=True)
    name = forms.CharField(required=True)
    surname = forms.CharField(required=True)
    primary_email = forms.EmailField(required=True)
    secondary_email = forms.EmailField(required=False)
    start_date = forms.DateField(required=True)
    end_date = forms.DateField(required=False)
    duty = forms.ModelChoiceField(queryset=Duty.objects.all(), initial=0, required=False)

    class Meta:
        model = Member
        fields = ['name', 'surname', 'primary_email', 'secondary_email', 'start_date', 'end_date', 'role', 'institute', 'group', 'country', 'duty']

    def clean_role(self):
        role_input = self.cleaned_data['role']
        if role_input:
            return role_input
        return None

    def clean_duty(self):
        duty_input = self.cleaned_data['duty']
        if duty_input:
            return duty_input
        return None

    def save(self, commit=True):
        instance = super(AddMemberForm, self).save(commit=False)
        if commit:
            instance.save()
        return instance
