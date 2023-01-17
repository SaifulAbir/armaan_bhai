from slugify import slugify
from product.utils import random_string_generator


def unique_order_id_generator_for_order(instance, new_order_id=None):
    if new_order_id is not None:
        order_id = new_order_id
    else:
        order_id_str = "or_"+str(random_string_generator(size=8))
        order_id = slugify(str(order_id_str))
    Klass = instance.__class__
    qs_exists = Klass.objects.filter(order_id=order_id).exists()

    if qs_exists:
        new_order_id = "{order_id}-{randstr}".format(
            order_id=order_id, randstr=random_string_generator(size=8))
        return unique_order_id_generator_for_order(instance, new_order_id=new_order_id)
    return order_id