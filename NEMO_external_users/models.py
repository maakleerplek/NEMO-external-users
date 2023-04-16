from django.db import models
from django.conf import settings
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from NEMO.models import User as NemoUser


class ExternalUserAttributes(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    password = models.CharField(max_length=100)

    def __str__(self):
        return self.user.username


class ExternalUserManager(BaseUserManager):
    def create_user(self, email, first_name, last_name, password=None):
        """
        Creates and saves a User with the given email, date of
        birth and password.
        """
        if not email:
            raise ValueError('Users must have an email address')

        normalized_email = self.normalize_email(email)
        user = self.model(
            email=normalized_email,
            first_name=first_name,
            last_name=last_name,
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, first_name, last_name, password=None):
        """
        Creates and saves a superuser with the given email, date of
        birth and password.
        """
        normalized_email = self.normalize_email(email)

        user = self.create_user(
            email=normalized_email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )

        user.is_admin = True
        user.save(using=self._db)
        return user


class ExternalUser(AbstractBaseUser):
    email = models.EmailField(
        verbose_name='email address',
        max_length=255,
        unique=True,
    )
    first_name = models.CharField(max_length=100, default='')
    last_name = models.CharField(max_length=100, default='')
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    nemo_user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.DO_NOTHING,
        null=True,
    )

    objects = ExternalUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    def __str__(self):
        return self.email

    def has_perm(self, perm, obj=None):
        "Does the user have a specific permission?"
        # Simplest possible answer: Yes, always
        return True

    def has_module_perms(self, app_label):
        "Does the user have permissions to view the app `app_label`?"
        # Simplest possible answer: Yes, always
        return True

    @property
    def is_staff(self):
        "Is the user a member of staff?"
        # Simplest possible answer: All admins are staff
        return self.is_admin


@receiver(post_save, sender=ExternalUser)
def create_related_nemo_user(sender, instance, **kwargs):
    if instance.is_active and instance.nemo_user is None:
        instance.nemo_user = NemoUser.objects.create_user(
            username=instance.email,
            first_name=instance.first_name,
            last_name=instance.last_name,
            email=instance.email,
        )
        instance.nemo_user.is_active = instance.is_active
        instance.save()


@receiver(post_delete, sender=ExternalUser)
def delete_related_nemo_user(sender, instance, **kwargs):
    try:
        nemo_user = instance.nemo_user
    except NemoUser.DoesNotExist:
        nemo_user = None

    if instance.is_active and nemo_user is not None:
        instance.nemo_user.is_active = False
        instance.nemo_user.save()
        instance.nemo_user.delete()


@receiver(post_delete, sender=NemoUser)
def delete_related_external_user(sender, instance, **kwargs):
    try:
        external_user = instance.externaluser
    except ExternalUser.DoesNotExist:
        external_user = None

    if instance.is_active and external_user is not None:
        instance.externaluser.is_active = False
        instance.externaluser.save()
        instance.externaluser.delete()
