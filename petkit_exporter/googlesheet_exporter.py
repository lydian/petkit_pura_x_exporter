from collections import defaultdict
import string

from google.oauth2 import service_account
from googleapiclient.discovery import build

from petkit_exporter.petkit import CleanEvent
from petkit_exporter.petkit import PetEvent


class GoogleSheetExporter:

    def __init__(self, spreadsheet_id=None, auth_json=None):
        self.creds = service_account.Credentials.from_service_account_info(auth_json)
        self.sheets_service = build("sheets", "v4", credentials=self.creds).spreadsheets()
        self.spreadsheet_id = spreadsheet_id

    def create_sheet_and_share(self, file_name, share_email, pet_names):
        spread_sheet = self.sheets_service.create(
            body={"properties": {"title": file_name}},
            fields="spreadsheetId,spreadsheetUrl"
        ).execute()
        drive_service = build("drive", "v3", credentials=self.creds)
        drive_service.permissions().create(
            fileId=spread_sheet["spreadsheetId"],
            body={
                "type": "user",
                "role": "writer",
                "emailAddress": share_email
            }
        ).execute()
        self.spreadsheet_id = spread_sheet["spreadsheetId"]
        self.spreadsheet_url = spread_sheet["spreadsheetUrl"]
        # create sheets
        sheets_names = pet_names + ["unknown", "other"]
        self.sheets_service.batchUpdate(
            spreadsheetId=spread_sheet["spreadsheetId"],
            body={
                "requests": [
                    {
                        "addSheet": {"properties": {"title": name}}
                    }
                    for name in sheets_names
                ]
            }
        ).execute()
        return spread_sheet

    def create_pet_info_sheet(self, pet_name):
        self.sheets_service.batchUpdate(
            spreadsheetId=self.spreadsheet_id,
            body={
                "requests": [{"addSheet": {"properties": {"title": pet_name}}}]
            }
        ).execute()
        range = f"{pet_name}!A1:" + string.ascii_uppercase[len(PetEvent._fields) -1] + "1"
        self.sheets_service.values().update(
            spreadsheetId=self.spreadsheet_id,
            range=range,
            valueInputOption="RAW",
            body={"values": [PetEvent._fields]}
        ).execute()

    def create_clean_info_sheet(self):
        self.sheets_service.batchUpdate(
            spreadsheetId=self.spreadsheet_id,
            body={
                "requests": [{"addSheet": {"properties": {"title": "other"}}}]
            }
        ).execute()
        self.sheets_service.values().update(
            spreadsheetId=self.spreadsheet_id,
            range="other!A1",
            valueInputOption="RAW",
            body={"values": [["last_modified"]]}
        ).execute()
        self.sheets_service.values().update(
            spreadsheetId=self.spreadsheet_id,
            range="other!A2:" + string.ascii_uppercase[len(CleanEvent._fields) - 1] + "2",
            valueInputOption="RAW",
            body={"values": [CleanEvent._fields]}
        ).execute()

    def get_latest_updated_timestamp(self):
        val = self.sheets_service.values().get(
            spreadsheetId=self.spreadsheet_id,
            range="other!B1"
        ).execute().get("values")
        if val is None:
            return None
        return int(val[0][0])

    def set_latest_updated_timestamp(self, value):
        self.sheets_service.values().update(
            spreadsheetId=self.spreadsheet_id,
            range="other!B1",
            valueInputOption="RAW",
            body={"values": [[value]]}
        ).execute()

    def is_sheet_exists(self, sheet_name):
        return sheet_name in [
            s["properties"]["title"]
            for s in self.sheets_service.get(
                spreadsheetId=self.spreadsheet_id
            ).execute()["sheets"]
        ]

    def update(self, records):
        if not self.is_sheet_exists("other"):
            self.create_clean_info_sheet()

        last_timestamp = self.get_latest_updated_timestamp()
        sheets = defaultdict(list)
        new_ts = None
        for ts, event in records:
            if new_ts is None or ts > new_ts:
                new_ts = ts
            if last_timestamp is not None and ts <= last_timestamp:
                # we've already had this logged
                continue
            if isinstance(event, PetEvent):
                pet_name = event.name or "unknown"
                sheets[pet_name].append(list(event))
            if isinstance(event, CleanEvent):
                sheets["other"].append(list(event))

        for sheet_name, rows in sheets.items():
            if not self.is_sheet_exists(sheet_name):
                self.create_pet_info_sheet(sheet_name)
            range = 'A:' + string.ascii_uppercase[
                len(rows[0]) - 1]
            self.sheets_service.values().append(
                spreadsheetId=self.spreadsheet_id,
                valueInputOption="RAW",
                range=f"{sheet_name}!{range}",
                body={
                    "majorDimension": "ROWS",
                    "values": rows
                }
            ).execute()
        self.set_latest_updated_timestamp(new_ts)
        print(new_ts)
