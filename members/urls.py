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
    path('api/get_filtered_chart_data/', views.get_filtered_chart_data, name='get_filtered_chart_data'),
    path('api/get-years/', views.get_years, name='get_years'),
    path('api/get-groups/', views.get_groups, name='get_groups'),
    path('api/get-institutes/', views.get_institutes, name='get_institutes'),
    path('api/get-filtered-monthly-data/', views.get_filtered_monthly_data, name='get_filtered_monthly_data'),
    path('api/get-countries/', views.get_countries, name='get_countries'),
    path('authors/', views.AuthorList.as_view(), name='author_list'),
    path('authors/<int:pk>/', views.AuthorRecord.as_view(), name='author-record'),
]
