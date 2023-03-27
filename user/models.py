from django.contrib.auth.models import PermissionsMixin, AbstractUser
from django.core.validators import RegexValidator
from django.db import models
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from armaan_bhai.models import AbstractTimeStamp
from django.utils.translation import gettext as _


class Division(AbstractTimeStamp):
    name = models.CharField(max_length=255)

    class Meta:
        db_table = 'divisions'

    def __str__(self):
        return self.name


class District(AbstractTimeStamp):
    division = models.ForeignKey(Division, on_delete=models.PROTECT, null=True, related_name='division_district')
    name = models.CharField(max_length=255)
    english_name = models.CharField(max_length=255)

    class Meta:
        db_table = 'districts'

    def __str__(self):
        return self.name


class Upazilla(AbstractTimeStamp):
    division = models.ForeignKey(Division, on_delete=models.PROTECT, null=True)
    district = models.ForeignKey(District, on_delete=models.PROTECT, null=True)
    name = models.CharField(max_length=255)

    class Meta:
        db_table = 'upazillas'

    def __str__(self):
        return self.name


phone_regex = RegexValidator(regex='^[+]*[(]{0,1}[0-9]{1,4}[)]{0,1}[-\s\./0-9]*$',message='invalid phone number')
class User(AbstractUser):
    GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
    )
    USER_CHOICES = (
        ('FARMER', 'Farmer'),
        ('AGENT', 'Agent'),
        ('CUSTOMER', 'Customer'),
        ('ADMIN', 'Admin'),
    )
    full_name = models.CharField(max_length=255, null=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, null=True)
    organization_name = models.CharField(max_length=255, null=True, blank=True)
    address = models.TextField(null=True)
    division = models.ForeignKey(Division, on_delete=models.PROTECT, null=True, related_name='division_user')
    district = models.ForeignKey(District, on_delete=models.PROTECT, null=True)
    upazilla = models.ForeignKey(Upazilla, on_delete=models.PROTECT, null=True)
    village = models.CharField(max_length=255, null=True, blank=True)
    postcode = models.IntegerField(null=True, blank=True)
    phone_number = models.CharField(max_length=255, validators=[phone_regex], unique=True)
    terms_and_conditions = models.BooleanField(default=False)
    image = models.ImageField(upload_to='images/user', null=True, blank=True)
    user_type = models.CharField(max_length=50, choices=USER_CHOICES, null=True, blank=True)
    is_admin = models.BooleanField(default=False)
    agent_user_id = models.CharField(max_length=50, null=True, blank=True)
    nid_front = models.ImageField(upload_to='images/user', null=True, blank=True)
    nid_back = models.ImageField(upload_to='images/user', null=True, blank=True)
    first_name = None
    last_name = None

    USERNAME_FIELD = 'phone_number'

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        db_table = 'users'

    def __str__(self):
        return self.username + "-" + str(self.id) + "-" + (self.agent_user_id if self.agent_user_id else "No Agent") + "-" + str(self.phone_number)


class AgentFarmer(AbstractTimeStamp):
    farmer = models.ForeignKey(User, on_delete=models.PROTECT, related_name="farmer_agent")
    agent = models.ForeignKey(User, on_delete=models.PROTECT, related_name="agent_farmer")

    class Meta:
        verbose_name = 'Agent Farmer'
        verbose_name_plural = 'Agent Farmers'
        db_table = 'agent_farmers'

    def __str__(self):
        return self.agent.full_name


class OTPModel(AbstractTimeStamp):
    """OTPModel to save otp value
    Args:
        contact_number: CharField
        otp_number: IntegerField
        expired_time: DateTimeField

    """
    contact_number = models.CharField(_('Contact Number'), max_length=20, null=False, blank=False)
    otp_number = models.IntegerField(_('OTP Number'), null=False, blank=False)
    verified_phone = models.BooleanField(default=False)
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="user_otp")
    expired_time = models.DateTimeField(_('Expired Time'), null=False, blank=False)

    def __str__(self):
        return self.user.full_name

    class Meta:
        verbose_name = "OTPModel"
        verbose_name_plural = "OTPModels"
        db_table = 'otp_models'

