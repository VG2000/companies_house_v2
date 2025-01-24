from django.contrib import admin
from .models import Company, CompanyFiles

# Register your models here.
admin.site.register(Company)
admin.site.register(CompanyFiles)