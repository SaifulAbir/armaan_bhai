"""
sms_gateway_url = 'https://api2.onnorokomsms.com/sendsms.asmx?WSDL'
sms_gateway_api_key = '5b03ead3-131d-495b-bce0-12d12a75a6ea'
"""
from twilio.rest import Client
from zeep import Client
import math
from random import randint

from armaan_bhai import settings

otp_number_max_length = 6


class SMSConfig(object):

    def __init__(self):
        self.url = 'https://api2.onnorokomsms.com/sendsms.asmx?WSDL'
        self.client = Client(self.url)
        self.api_key = '5b03ead3-131d-495b-bce0-12d12a75a6ea'
        self.mask_name = ''
        self.campaign_name = ''
        self.low_balance = 10

    def check_sms_balance(self):
        balance = self.client.service.GetCurrentBalance(self.api_key)
        # if balance is under mentioned amount then send a sms to the Admin
        if int(math.ceil(float(balance))) <= self.low_balance:
            return True
        else:
            return False

    def send_sms(self, sms_text, recipient_number, sms_type):
        result = self.client.service.NumberSms(self.api_key, sms_text, recipient_number, sms_type, self.mask_name,
                                               self.campaign_name)
        # print("result of send sms = ", result)
        return result


class OTPManager(object):

    def generate_otp_number(self):
        max_length = otp_number_max_length
        otp_number = self.random_with_N_digits(max_length)
        return otp_number

    def create_otp(self, contact_number):
        # generate unique OTP Number
        otp_number = self.generate_otp_number()
        return otp_number

    def random_with_N_digits(self, max_length):
        range_start = 10 ** (max_length - 1)
        range_end = (10 ** max_length) - 1
        return randint(range_start, range_end)

    def initialize_otp(self, contact_number):

        otp_number = self.create_otp(contact_number)
        return otp_number

    def send_sms_to_user_by_queue(self, smsText, recipientNumber, smsType):
        result = SMSConfig().send_sms(smsText, recipientNumber, smsType)
        return result

    def initialize_otp_and_sms_otp(self, contact_number):
        otp_number = self.initialize_otp(contact_number)
        # self.send_twilio_message(contact_number, "Hello From Saiful")
        #
        # if int(otp_number):
        #
        #     smsText = 'Your verification number is ' + str(otp_number)
        #     self.send_sms_to_user_by_queue(smsText, mobile, 'TEXT')
        #     return str(otp_number)
        # else:
        #     pass
        return str(otp_number)

    def send_twilio_message(self, to_number, body):
        client = Client(
            settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

        return client.messages.create(
            body=body,
            to=to_number,
            from_=settings.TWILIO_PHONE_NUMBER
        )