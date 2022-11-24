
# def profile_view_count(profile):
#     profile.view_count += 1
#     profile.save()
#
#
# def get_current_host(request):
#     scheme = request.is_secure() and "https" or "http"
#     return f'{scheme}://{request.get_host()}/'
from random import randint

user_id_max_length = 6


class UserIDManager(object):

    def generate_user_id(self):
        max_length = user_id_max_length
        user_id = "AR_" + str(self.random_with_N_digits(max_length))
        return user_id

    def random_with_N_digits(self, max_length):
        range_start = 10 ** (max_length - 1)
        range_end = (10 ** max_length) - 1
        return randint(range_start, range_end)