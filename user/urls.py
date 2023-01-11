from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .api import *
from .views import *
from django.views.decorators.csrf import csrf_exempt

urlpatterns = [
    # agent and farmer login
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # agent create api
    path('create-user/', csrf_exempt(UserRegApi.as_view())),
    # farmer create api
    path('create/farmer/', csrf_exempt(FarmerCreateApi.as_view())),
    # active/inactive agent
    path('agent/update/<int:pk>/', AgentUpdateAPIView.as_view(), name='update_agent'),
    # create customer
    path('create/customer/', CreateCustomerAPI.as_view(), name='create_customer'),
    # customer login
    path('customer/login/', CustomerLoginAPI.as_view(), name='customer_login'),
    # customer resend otp
    path('customer/resend-otp/', CustomerReSendOTPAPIView.as_view(), name='customer_resend_otp'),
    # verify otp of customer
    path('otp/verify/', OTPVerifyAPIVIEW.as_view(), name='otp_verification'),
    # customer profile
    path('customer/profile/', CustomerRetrieveAPIView.as_view(), name='customer_profile'),
    # customer profile update
    path('customer/edit-profile/', CustomerUpdateAPIView.as_view(), name='customer_edit_profile'),
    # farmer list for agent
    path('admin/farmer/list/', FarmerListAPI.as_view(), name='farmer_list'),
    # agent list for superadmin
    path('admin/agent/list/', AgentListAPI.as_view(), name='agent_list'),
    # division, district and upazilla list api
    path('division/list/', DivisionListAPI.as_view(), name='division_list'),
    path('district/list/<int:division_id>/', DistrictListAPI.as_view(), name='district_list'),
    path('upazilla/list/<int:district_id>/', UpazillaListAPI.as_view(), name='upazilla_list'),
    # path('update-user/', UserUpdateAPIView.as_view()),
    # path('user-detail/', UserUpdateAPIView.as_view()),
    # path('donor-profile/<int:pk>/', DonorProfileAPIView.as_view()),
    # path('donee-ngo-profile/<int:pk>/', DoneeAndNGOProfileAPIView.as_view()),
    # path('create-profile/', DoneeAndNgoProfileCreateAPIView.as_view()),
    # path('update-profile/', DoneeAndNgoProfileUpdateAPIView.as_view()),
    # path('profile-detail/', DoneeAndNgoProfileUpdateAPIView.as_view()),
    # path('country-list/', CountryListAPI.as_view()),
    # # path('verify-invitation/<str:invitation>',VerifyInvitationView.as_view()),
    # path('user-follow/', UserFollowUserAPI.as_view()),
    # path('profile-follow/', UserFollowProfileAPI.as_view()),
    # path('dashboard/donee-count/', inNgoDoneeInfoAPIView.as_view()),
    # path('dashboard/donee-list/', inNgoDoneeListAPIView.as_view()),
    # path('platform/dashboard/donee/', PlatformDashboardDoneeAPIView.as_view()),
    # path('platform/dashboard/ngo/', PlatformDashboardNGOAPIView.as_view()),
    # path('donee-status/', DoneeStatusUpdateAPIView.as_view()),
    # path('send-invitation-link/', SendInvitationLink.as_view()),
    # path('dashboard/app/', DashboardAppAPIView.as_view()),
    # path('platform/dashboard/', PlatformDashboardAPIView.as_view()),
    # path('ngo-endorsed-goals/', EndorsedGoalsInNgoAPIView.as_view()),
    # path('social-signup/', SocialSignupAPIView.as_view()),
    # path('search-user/', UserSearchAPIView.as_view()),
    # path('role-list/',RoleListAPIView.as_view()),
    # path('platform-role-list/',PlatformRoleListAPIView.as_view()),
    # path('ngo-user-create/',NgoUserCreateAPIView.as_view()),
    # path('platform-user-create/', PlatformUserCreateAPIView.as_view()),
    # path('ngo-user-list/',NgoUserListAPIView.as_view()),
    # path('platform-user-list/',PlatformUserListAPIView.as_view()),
    # path('ngo-user-role-update/<int:pk>/',NgoUserRoleUpdateAPIView.as_view()),
    # path('ngo-user-status-update/<int:pk>/', NgoUserUpdateStatusAPIView.as_view()),
    # path('verify-user/<str:verification>', IdActiveAPIView.as_view()),
    # path('dashboard/my-wallet/', DashboardMyWalletAPIView.as_view()),
    # path('platform/dashboard/my-wallet/', PlatformDashboardWalletAPIView.as_view()),
    # path('dashboard/donors/',DashboardDonorsAPIView.as_view()),
    # path('platform/dashboard/donors/',PlatformDashboardDonorAPIView.as_view()),
    # path('country-code/<int:pk>/',CountryCodeAPIView.as_view()),

]

