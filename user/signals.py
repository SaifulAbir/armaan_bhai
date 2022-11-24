# from django.db.models.signals import post_save
# from .models import *
# from django.dispatch import receiver


# @receiver(post_save,sender=User)
# def create_profile(sender,instance,created, **kwargs):

#     type = ProfileType.objects.get(id=1)
#     plan = Plan.objects.get(id=1)
#     if created:
#         Profile.objects.create(user=instance,profile_types=type,plan_id=plan)



# @receiver(post_save,sender=User)
# def save_profile(sender,instance, **kwargs):
#     instance.profile.save()