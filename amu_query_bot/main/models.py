from django.db import models
from django.conf import settings

# Create your models here.

# 2. Feedback Table
class Feedback(models.Model):
    RATING_CHOICES = [(i, i) for i in range(1, 6)]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='feedbacks')
    rating = models.IntegerField(choices=RATING_CHOICES)
    comments = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback {self.id} - {self.user.email} - {self.rating}⭐"

    class Meta:
        verbose_name = "Feedback"
        verbose_name_plural = "Feedbacks"
        ordering = ['-submitted_at']


class Resource(models.Model):

    url = models.URLField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to ='uploads/', blank=True, null=True)

    class Meta:
        verbose_name = "Resource"
        verbose_name_plural = "Resources"
