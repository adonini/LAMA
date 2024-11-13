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
]
