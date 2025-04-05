from pyclbr import Class
from django.db import models
import datetime
from django.utils import timezone
# Create your models here.
class Browse(models.Model):
    title = models.CharField(max_length=200)
    pub_date = models.DateTimeField('date published')
    image = models.ImageField(upload_to='images/')
    def __str__(self):
        return self.title
    def was_published_recently(self):
        return self.pub_date >= timezone.now() - datetime.timedelta(days=1)
class Blast(models.Model):
    title = models.CharField(max_length=200)
    pub_date = models.DateTimeField('date published')
    image = models.ImageField(upload_to='images/')

class Download(models.Model):
    title = models.CharField(max_length=200)
    pub_date = models.DateTimeField('date published')
    image = models.ImageField(upload_to='images/')
    def __str__(self):
        return self.title
    def was_published_recently(self):
        return self.pub_date >= timezone.now() - datetime.timedelta(days=1) 
class About(models.Model):
    title = models.CharField(max_length=200)
    pub_date = models.DateTimeField('date published')
    image = models.ImageField(upload_to='images/')
    def __str__(self):
        return self.title
    def was_published_recently(self):        return self.pub_date >= timezone.now() - datetime.timedelta(days=1)
class Contact(models.Model):
    title = models.CharField(max_length=200)
    pub_date = models.DateTimeField('date published')
    image = models.ImageField(upload_to='images/')
    def __str__(self):
        return self.title
    def was_published_recently(self):        return self.pub_date >= timezone.now() - datetime.timedelta(days=1)
class Help(models.Model):
    title = models.CharField(max_length=200)
    pub_date = models.DateTimeField('date published')
    image = models.ImageField(upload_to='images/')
    def __str__(self):
        return self.title
    def was_published_recently(self):        return self.pub_date >= timezone.now() - datetime.timedelta(days=1)