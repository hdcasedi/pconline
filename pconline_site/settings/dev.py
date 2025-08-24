from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-q!_kfj%ryutpw02&6!%04m#+&do=yha4hu@v!e!i9e9%v$^olf"

# SECURITY WARNING: define the correct hosts in production!


ALLOWED_HOSTS = ['physiquechimie.online', 'www.physiquechimie.online', 'localhost', '127.0.0.1']
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"


try:
    from .local import *
except ImportError:
    pass
