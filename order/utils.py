from slugify import slugify
import string
import random


def random_id_generator(size=10, chars=string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def unique_order_id_generator_for_order(instance, new_order_id=None):
    if new_order_id is not None:
        order_id = new_order_id
    else:
        order_id_str = instance.delivery_address.district.name[:3] + "-" + str(random_id_generator(size=6))
        order_id = slugify(str(order_id_str))
    Klass = instance.__class__
    qs_exists = Klass.objects.filter(order_id=order_id).exists()

    if qs_exists:
        new_order_id = "{order_id}-{randstr}".format(
            order_id=order_id, randstr=random_id_generator(size=6))
        return unique_order_id_generator_for_order(instance, new_order_id=new_order_id)
    return order_id


def unique_order_id_generator_for_suborder(instance, new_order_id=None):
    if new_order_id is not None:
        order_id = new_order_id
    else:
        order_id_str = instance.delivery_address.district.name[:3] + "-" + str(random_id_generator(size=8))
        order_id = slugify(str(order_id_str))
    Klass = instance.__class__
    qs_exists = Klass.objects.filter(suborder_number=order_id).exists()

    if qs_exists:
        new_order_id = "{order_id}-{randstr}".format(
            order_id=order_id, randstr=random_id_generator(size=8))
        return unique_order_id_generator_for_order(instance, new_order_id=new_order_id)
    return order_id