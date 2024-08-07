from django.db import models


class PromptModel(models.Model):

    prompt_vacant = models.TextField()

    def __str__(self):
        return 'Prompt'

    def __repr__(self) -> str:
        return self.prompt_vacant


class GoogleCredentialsModel(models.Model):

    credentials = models.TextField()
    state = models.TextField()

    def __str__(self):
        return 'Google credentials'

    def __repr__(self):
        return self.credentials
