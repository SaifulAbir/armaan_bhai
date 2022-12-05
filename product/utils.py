import string
import random
from slugify import slugify


def random_string_generator(size=10, chars=string.ascii_lowercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def unique_slug_generator(instance, new_slug=None):
    if new_slug is not None:
        slug = new_slug
    else:
        p_title = str(instance.title)
        l = [s for s in p_title.split()]
        text = '-'.join(l)
        slug = slugify(text)

    new_slug = "{slug}-{randstr}".format(slug=slug,
                                         randstr=random_string_generator(size=8))
    return new_slug
