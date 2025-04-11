from django.urls import path
from . import views


urlpatterns = [
    path('', views.Index.as_view(), name='index'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_user, name='logout'),
    path('member/<int:pk>/', views.MemberRecord.as_view(), name='member-record'),
    path('members/', views.MemberList.as_view(), name='member_list'),
    path('manage_member/', views.ManageMember.as_view(), name='manage-member'),
    path('manage_member/<int:pk>/', views.ManageMember.as_view(), name='manage-member-pk'),
    path('add_member/', views.AddMember.as_view(), name='add-member'),
    path('add_member/<int:pk>', views.AddMember.as_view(), name='add-member-pk'),
    path('statistics/', views.Statistics.as_view(), name='statistics'),
    path('api/members/', views.api_member, name='api_member'),
    path('api/authors/', views.api_author, name='api_author'),
    path('api/institutes/', views.api_institute, name='api_institute'),
    path('api/get_filtered_chart_data/', views.get_filtered_chart_data, name='get_filtered_chart_data'),
    path('api/get-years/', views.get_years, name='get_years'),
    path('api/get-groups/', views.get_groups, name='get_groups'),
    path('api/get-institutes/', views.get_institutes, name='get_institutes'),
    path('api/get-filtered-monthly-data/', views.get_filtered_monthly_data, name='get_filtered_monthly_data'),
    path('api/get-countries/', views.get_countries, name='get_countries'),
    path('authors/', views.AuthorList.as_view(), name='author_list'),
    path('authors/<int:pk>/', views.AuthorRecord.as_view(), name='author-record'),
    path('manage_author/', views.ManageAuthor.as_view(), name='manage-author'),
    path('manage_author/<int:pk>/', views.ManageAuthor.as_view(), name='manage-author-pk'),
    path('add_author/', views.AddAuthor.as_view(), name='add-author'),
    path('add_author/<int:pk>', views.AddAuthor.as_view(), name='add-author-pk'),
    path('export-aa-with-emails/', views.generate_aa_email, name='export_aa_with_emails'),
    path('export-aa/', views.generate_aa, name='export_aa'),
    path('export-apj/', views.generate_apj, name='export_apj'),
    path('export-arxiv/', views.generate_arxiv, name='export_arxiv'),
    path('export-mnras/', views.generate_mnras, name='export_mnras'),
    path('export-pos/', views.generate_pos, name='export_pos'),
    path('export-nature/', views.generate_nature, name='export_nature'),
    path('export-science/', views.generate_science, name='export_science'),
    path('institutes/', views.InstituteList.as_view(), name='institute_list'),
    path('institutes/<int:pk>/', views.InstituteRecord.as_view(), name='institute-record'),
    path('manage_institute/', views.ManageInstitute.as_view(), name='manage-institute'),
    path('manage_institute/<int:pk>/', views.ManageInstitute.as_view(), name='manage-institute-pk'),
    path('add_institute/', views.AddInstitute.as_view(), name='add-institute'),
    path('add_institute/<int:pk>', views.AddInstitute.as_view(), name='add-institute-pk'),
]
