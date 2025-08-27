from django.db.models.signals import pre_delete
from django.dispatch import receiver
from .models import Dentist, DentistRedirect

@receiver(pre_delete, sender=Dentist)
def store_redirect(sender, instance, **kwargs):
    DentistRedirect.objects.get_or_create(
        old_slug=instance.slug,
        city=instance.city
    )