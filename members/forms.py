from django import forms
from django.contrib.auth.forms import AuthenticationForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from .models import Member, Institute, Group, Duty, Country, AuthorDetails


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
    start_date = forms.DateField(required=True)
    end_date = forms.DateField(required=False)
    duty = forms.ModelChoiceField(queryset=Duty.objects.all(), initial=0, required=False)

    class Meta:
        model = Member
        fields = ['name', 'surname', 'primary_email', 'start_date', 'end_date', 'role', 'institute', 'group', 'country', 'duty']

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        # Validate that the end date is later than the start date
        if end_date and end_date <= start_date:
            raise forms.ValidationError("End date must be later than the start date.")

        return cleaned_data

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


class AddAuthorDetailsForm(forms.ModelForm):
    """
    Form for managing author details, including optional fields for ORCID, email, and affiliations.
    """
    # Match the "name" attributes in the template
    author_name = forms.CharField(
        required=False,
        max_length=150,
        help_text="Full author name as it appears in publications.",
        label="Full Name"  # Matches the label in the template
    )
    author_name_given = forms.CharField(
        required=False,
        max_length=80,
        help_text="Given name as it appears in publications.",
        label="Given Name"
    )
    author_name_family = forms.CharField(
        required=False,
        max_length=80,
        help_text="Family name as it appears in publications.",
        label="Family Name"
    )
    author_email = forms.EmailField(
        required=False,
        help_text="Email used for publications. Leave blank if not applicable.",
        label="Email"
    )
    orcid = forms.CharField(
        required=False,
        max_length=25,
        help_text="Enter the ORCID (19 characters including hyphens). Leave blank if not applicable.",
        label="ORCID"
    )

    class Meta:
        model = AuthorDetails
        fields = ['author_name', 'author_name_given', 'author_name_family', 'author_email', 'orcid']

    def save(self, commit=True):
        """
        Save the form instance, including any custom logic for related models.
        """
        instance = super().save(commit=False)
        if commit:
            instance.save()
        return instance


class AddInstituteForm(forms.ModelForm):
    country = forms.ModelChoiceField(
        queryset=Country.objects.all(),
        initial=0,
        required=False,
        label="Country",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    group = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        initial=0,
        required=False,
        label="Group",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    name = forms.CharField(
        required=True,
        label="Institute Name",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter institute name'})
    )
    long_name = forms.CharField(
        required=False,
        label="Long Name",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter full institute name'})
    )
    long_description = forms.CharField(
        required=False,
        label="Description",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Enter a detailed description'})
    )
    is_lst = forms.BooleanField(
        required=False,
        label="Is LST?",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = Institute
        fields = ['name', 'long_name', 'long_description', 'is_lst', 'group', 'country']

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
        return instance
