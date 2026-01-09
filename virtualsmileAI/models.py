from django.db import models

class SmileDesignLead(models.Model):
    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=20, blank=True)
    city = models.CharField(max_length=80, blank=True)
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    before_image = models.CharField(max_length=255, blank=True)
    after_image = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.name} ({self.phone})"



