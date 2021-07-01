import os
import json

from petkit_exporter.googlesheet_exporter import GoogleSheetExporter
from petkit_exporter.petkit import PetKit


google_auth_json = json.loads(os.environ["AUTH_JSON"])
petkit_username = os.environ["PETKIT_USERNAME"]
petkit_password = os.environ["PETKIT_PASSWORD"]
spreadsheet_id = os.environ["SPREADSHEET_ID"]

petkit = PetKit(petkit_username, petkit_password)
google_sheet = GoogleSheetExporter(
    auth_json=google_auth_json,
    spreadsheet_id=spreadsheet_id
)

device_id = petkit.discover_devices()[0]["data"]["id"]
google_sheet.update(petkit.get_device_records(device_id))
