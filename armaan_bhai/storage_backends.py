from storages.backends.s3boto3 import S3Boto3Storage


class StaticStorage(S3Boto3Storage):
    """Static Storage for S3 configuration
    Args:
        S3Boto3Storage ([object]): Inherits default S3Boto3Storage object.
    """
    location = 'static'
    default_acl = 'public-read'


class PublicMediaStorage(S3Boto3Storage):
    """Public media Storage for S3 configuration
    Args:
        S3Boto3Storage ([object]): Inherits default S3Boto3Storage object.
    """
    location = 'media'
    default_acl = 'public-read'
    file_overwrite = False