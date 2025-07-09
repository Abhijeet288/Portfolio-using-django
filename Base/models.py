from django.db import models

# Create your models here.
class Contact(models.Model):
    name=models.CharField(max_length=50)
    email=models.EmailField(max_length=50)
    number=models.CharField(max_length=30)
    content=models.TextField(max_length=500)

