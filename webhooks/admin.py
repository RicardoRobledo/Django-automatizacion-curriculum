from django.contrib import admin

from .models import PromptModel, GoogleCredentialsModel


admin.site.register(PromptModel)
admin.site.register(GoogleCredentialsModel)
