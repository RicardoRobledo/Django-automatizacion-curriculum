import googleapiclient.discovery
import google_auth_oauthlib.flow
import google.oauth2.credentials
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from google.auth.transport.requests import Request
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
import json
import io
import requests

from asgiref.sync import sync_to_async

from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.http import HttpResponse

from openai import AsyncOpenAI

from PyPDF2 import PdfReader

from .models import PromptModel, GoogleCredentialsModel


client = AsyncOpenAI(
    api_key=settings.OPENAI_API_KEY
)


CLIENT_SECRETS_FILE = settings.GOOGLE_CREDENTIALS
API_SERVICE_NAME = 'drive'
API_VERSION = 'v3'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
          'https://www.googleapis.com/auth/drive']


@method_decorator(csrf_exempt, name='dispatch')
class EmailWebookView(View):
    """
    This view is used to receive emails from a webhook and process them
    """

    async def post(self, request, *args, **kwargs):

        # No usar sesiones

        queryset = await sync_to_async(GoogleCredentialsModel.objects.all)()

        credentials = google.oauth2.credentials.Credentials(
            queryset.first().credentials)

        # Check if credentials are valid
        if not credentials.valid:
            if credentials.expired and credentials.refresh_token:
                try:
                    credentials.refresh(Request())
                except Exception as e:
                    print("Error refreshing credentials:", e)
                    return HttpResponse("Error refreshing credentials", status=500)

                # Save the refreshed credentials back to the session
                await sync_to_async(queryset.update)(credentials=credentials_to_dict(credentials))
            else:
                return redirect('authorize')

        body = json.loads(request.body)
        url = body['attachments'][0]['url']
        response = requests.get(url)

        if response.status_code == 200:
            pdf_file = io.BytesIO(response.content)
            reader = PdfReader(pdf_file)

            all_text = ""
            for page_num in range(len(reader.pages)):
                page = reader.pages[page_num]
                all_text += page.extract_text()

        content = await sync_to_async(PromptModel.objects.first)()

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": f"Esta es una vacante\n-----------\n{content}\n-----------\nDebes de analizar el curriculum de un aspirante y verificar si cumple con los requisitos de la vacante. aspirtante: {all_text}"}],
            tool_choice="required",
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "curriculum_analyzer",
                        "description": "Analyze a curriculum",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "nombre": {
                                    "type": "string",
                                    "description": "Nombres y apellidos de la persona",
                                    "default": "empty"
                                },
                                "telefono": {
                                    "type": "string",
                                    "description": "Número de teléfono de la persona",
                                    "default": "empty"
                                },
                                "tecnologias": {
                                    "type": "string",
                                    "description": "Lenguajes de programación, bases de datos, frameworks de programación y otras tecnologías y herramientas de programación que maneje",
                                    "default": "empty"
                                },
                                "años_experiencia": {
                                    "type": "integer",
                                    "description": "Los años de experiencia que tiene la persona",
                                    "default": 12
                                },
                                "aplica": {
                                    "type": "string",
                                    "description": "Si aplica o no a la oferta de trabajo con en base a lo que se busca",
                                    "enum": ["si", "no"],
                                    "default": "no"
                                }
                            },
                            "required": ["nombre", "telefono", "tecnologías", "años_experiencia", "aplica"]
                        }
                    }
                }
            ]
        )

        json_content = json.loads(
            response.choices[0].message.tool_calls[0].function.arguments)

        print('Vamos')

        try:
            service = build("sheets", "v4", credentials=credentials)

            # Call the Sheets API
            sheet = service.spreadsheets()
            result = (
                sheet.values()
                .get(spreadsheetId=settings.SPREADSHEET_ID, range="Hoja 1")
                .execute()
            )
            values = result.get("values", [])

            if not values:
                print("No data found.")
                return

            for row in values:
                print(row)
        except HttpError as err:
            print(err)

        values = [
            [json_content['nombre'],
             json_content['telefono'],
             json_content['tecnologias'],
             json_content['años_experiencia'],
             json_content['aplica'],],
        ]

        body = {
            'values': values
        }

        # Insertar datos en la hoja de cálculo
        result = service.spreadsheets().values().append(
            spreadsheetId=settings.SPREADSHEET_ID, range='Hoja 1',
            valueInputOption="RAW", insertDataOption="INSERT_ROWS", body=body).execute()

        return HttpResponse(status=200)


@method_decorator(csrf_exempt, name='dispatch')
class TestView(View):

    async def get(self, request):

        queryset = GoogleCredentialsModel.objects.all()

        credentials_exist = await sync_to_async(queryset.exists)()

        if not credentials_exist:
            return redirect('authorize')

        # Load credentials from the session
        credentials = google.oauth2.credentials.Credentials(
            (await sync_to_async(queryset.first)()).credentials)

        # Check if credentials are valid
        if not credentials.valid:
            if credentials.expired and credentials.refresh_token:
                try:
                    credentials.refresh(Request())
                except Exception as e:
                    print("Error refreshing credentials:", e)
                    return HttpResponse("Error refreshing credentials", status=500)

                # Save the refreshed credentials back to the session
                await sync_to_async(queryset.update)(credentials=credentials_to_dict(credentials))
            else:
                return redirect('authorize')

        return HttpResponse('Credentials are valid')


@method_decorator(csrf_exempt, name='dispatch')
class AuthorizeView(View):

    async def get(self, request):

        flow = google_auth_oauthlib.flow.Flow.from_client_config(
            json.loads(CLIENT_SECRETS_FILE), scopes=SCOPES)

        flow.redirect_uri = request.build_absolute_uri(
            '/webhooks/oauth2callback/')

        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent')

        await sync_to_async(GoogleCredentialsModel.objects.create)(state=state)

        return redirect(authorization_url)


@method_decorator(csrf_exempt, name='dispatch')
class OAuth2CallbackView(View):

    async def get(self, request):

        queryset = GoogleCredentialsModel.objects.all()

        state = (await sync_to_async(queryset.first)()).state

        flow = google_auth_oauthlib.flow.Flow.from_client_config(
            json.loads(CLIENT_SECRETS_FILE), scopes=SCOPES, state=state)

        flow.redirect_uri = request.build_absolute_uri(
            '/webhooks/oauth2callback/')

        authorization_response = request.build_absolute_uri()
        flow.fetch_token(authorization_response=authorization_response)

        credentials = flow.credentials

        print(await sync_to_async(queryset.update)(credentials=credentials_to_dict(credentials)))

        return redirect('test_api_request')


@method_decorator(csrf_exempt, name='dispatch')
class RevokeView(View):

    async def get(self, request):

        google_credentials_obj = await sync_to_async(GoogleCredentialsModel.objects.first)()

        if google_credentials_obj is None:
            return HttpResponse('You need to <a href="/authorize">authorize</a> before testing the code to revoke credentials.')

        credentials = google.oauth2.credentials.Credentials(
            google_credentials_obj.credentials)

        revoke = requests.post('https://oauth2.googleapis.com/revoke',
                               params={'token': credentials.token},
                               headers={'content-type': 'application/x-www-form-urlencoded'})

        status_code = getattr(revoke, 'status_code')
        if status_code == 200:
            return HttpResponse('Credentials successfully revoked.')
        else:
            return HttpResponse('An error occurred.')


@method_decorator(csrf_exempt, name='dispatch')
class ClearCredentialsView(View):

    async def get(self, request):

        google_credentials_obj = await sync_to_async(GoogleCredentialsModel.objects.first)()

        if google_credentials_obj:
            google_credentials_obj.delete()

        return HttpResponse('Credentials have been cleared.')


def credentials_to_dict(credentials):

    return {'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes}
