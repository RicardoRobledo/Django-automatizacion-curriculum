import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# The ID and range of a sample spreadsheet.
SPREADSHEET_ID = "1hQl4MWaL4uNW1w5y0k9qcS2EMgvSKI02aM7hfRFHgBA"
RANGE_NAME = "Hoja 1"


def main():
    """Shows basic usage of the Sheets API.
    Prints values from a sample spreadsheet.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            print('Inicio del flujo de autorización')
            from decouple import config

            import json
            client_config_str = config('GOOGLE_CREDENTIALS')

            print(f'Tipo de client_config_str: {type(client_config_str)}')
            print(f'Client Config String: {client_config_str}')

            # Convertir la cadena JSON en un diccionario
            client_config = json.loads(client_config_str)

            print(f'Tipo de client_config: {type(client_config)}')
            print(f'Client Config: {client_config}')

            if not isinstance(client_config, dict):
                raise ValueError(
                    "settings.GOOGLE_CREDENTIALS debe ser un diccionario después de cargarlo de JSON")

            flow = InstalledAppFlow.from_client_config(
                client_config, SCOPES)
            flow.redirect_uri = "http://localhost"

            auth_url, _ = flow.authorization_url(
                access_type='offline', include_granted_scopes='true', prompt='consent')

            print(
                f'Por favor visita este URL para autorizar la aplicación: {auth_url}')
            print(
                'Autoriza la aplicación y luego introduce el código de autorización aquí:')
            auth_code = input('Código de autorización: ')
            flow.fetch_token(code=auth_code)

            creds = flow.credentials

            # Aquí normalmente deberías redirigir al usuario a auth_url para que autorice la aplicación
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service = build("sheets", "v4", credentials=creds)

        # Call the Sheets API
        sheet = service.spreadsheets()
        result = (
            sheet.values()
            .get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME)
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
        ["Nombre", "Teléfono", "Tecnologías", "Años de experiencia", "Aplica"],
        ["John", "23434", "john.doe@example.com", 4, "si"],
    ]

    body = {
        'values': values
    }

    # Insertar datos en la hoja de cálculo
    result = service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME,
        valueInputOption="RAW", insertDataOption="INSERT_ROWS", body=body).execute()
    print('{0} cells updated.'.format(result.get('updatedCells')))


if __name__ == "__main__":
    main()
