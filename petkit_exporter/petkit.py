import datetime
import hashlib
from collections import namedtuple
from typing import Dict, List, Optional

import requests


PETKIT_API = "http://api.petkt.com"

EVENT_TYPES = {
    5: "cleaning",
    7: "reset",
    10: "pet in the litter box",
    8: "deorder"
}

START_REASON = {
    0: "auto",
    1: "periodic",
    2: "manual"
}

PetEvent = namedtuple(
    "PetEvent", [
        "time_start",
        "time_end",
        "duration",
        "name",
        "weight",
    ],
    defaults=(None,) * 5
)

CleanEvent = namedtuple(
    "CleanEvent", [
        "time_start",
        "time_end",
        "duration",
        "event_name",
        "trigger_reason",
        "litter_percent",
        "need_clean",
        "deoder_percent",
        "refill_deoder",
    ],
    defaults=(None,) * 9
)


class PetkitURL:
    LOGIN = "/latest/user/login"
    USER_DETAILS = "/latest/user/details2"
    DISCOVERY = "/latest/discovery/device_roster"
    PURAX_DETAILS = "/latest/t3/device_detail"
    PURAX_RECORDS = "/latest/t3/getDeviceRecord"


class PetKit:

    def __init__(self, user_name: str, password: str) -> None:
        self.user_name = user_name
        self.password = hashlib.md5(password.encode("utf-8")).hexdigest()
        self.access_token: Optional[str] = None
        self.access_token_expiration: Optional[datetime.datetime] = None
        self.user: Optional[Dict] = None

    def maybe_login(self) -> None:
        if (
            self.access_token is not None
            and self.access_token_expiration > datetime.datetime.utcnow()
        ):
            return
        r = requests.post(
            f"{PETKIT_API}{PetkitURL.LOGIN}",
            data={
                "username": self.user_name,
                "password": self.password,
                "encrypt": 1
            }
        )
        r.raise_for_status()
        session = r.json()["result"]["session"]
        self.access_token = session["id"]
        self.access_token_expiration = datetime.datetime.strptime(
            session["createdAt"], "%Y-%m-%dT%H:%M:%S.%fZ"
        ) + datetime.timedelta(seconds=session["expiresIn"])

    def _query(self, path: str) -> Dict:
        self.maybe_login()
        r = requests.post(
            f"{PETKIT_API}{path}", headers={"X-Session": self.access_token}
        )
        r.raise_for_status()
        response = r.json()
        if response.get("error") is not None:
            raise ValueError(response["error"]["msg"])
        return response

    def _format_time(self, ts: int) -> str:
        return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")

    def get_user_details(self) -> None:
        r = self._query(PetkitURL.USER_DETAILS)
        self.user = r["result"]["user"]

    def discover_devices(self) -> List[Dict]:
        r = self._query(PetkitURL.DISCOVERY)
        return r["result"]["devices"]

    def get_device_details(self, device_id: int) -> Dict:
        r = self._query(f"{PetkitURL.PURAX_DETAILS}?id={device_id}")
        return r["result"]

    def get_device_records(self, device_id: int) -> List[Dict]:
        r = self._query(f"{PetkitURL.PURAX_RECORDS}?deviceId={device_id}")
        return [self.parse_record(row) for row in r["result"]]

    def parse_record(self, record):
        if record["eventType"] == 10:
            # Pet in Litter box
            pet = self.find_most_possible_pet(record["content"]["petWeight"])
            return (
                record["timestamp"],
                PetEvent(
                    self._format_time(record["content"]["timeIn"]),
                    self._format_time(record["content"]["timeOut"]),
                    record["content"]["timeOut"] - record["content"]["timeIn"],
                    (pet or {}).get("name"),
                    record["content"]["petWeight"]
                )
            )

        if record["eventType"] == 5:
            # cleaning
            return(
                record["timestamp"],
                CleanEvent(
                    self._format_time(record["content"]["startTime"]),
                    self._format_time(record["timestamp"]),
                    record["timestamp"] - record["content"]["startTime"],
                    "clean",
                    START_REASON.get(
                        record["content"]["startReason"]) or record["content"]["startReason"],
                    litter_percent=record["content"]["litterPercent"],
                    need_clean=record["content"]["boxFull"]
                )
            )
        if record["eventType"] == 8:
            # deorder
            return (
                record["timestamp"],
                CleanEvent(
                    self._format_time(record["content"]["startTime"]),
                    self._format_time(record["timestamp"]),
                    record["timestamp"] - record["content"]["startTime"],
                    "deorder",
                    START_REASON[record["content"]["startReason"]],
                    deoder_percent=record["content"]["liquid"],
                    refill_deoder=record["content"]["liquidLack"]
                )
            )
        if record["eventType"] == 7:
            # reset
            return (
                record["timestamp"],
                CleanEvent(
                    self._format_time(record["content"]["startTime"]),
                    self._format_time(record["timestamp"]),
                    record["timestamp"] - record["content"]["startTime"],
                    "reset",
                    START_REASON.get(
                        record["content"]["startReason"]) or record["content"]["startReason"],
                )
            )
        return record["timestamp"], record

    def find_most_possible_pet(self, weight):
        if self.user is None:
            self.get_user_details()
        pet = sorted(
            self.user["dogs"],
            key=lambda p: abs(p["weight"] * 1000 - weight)
        )[0]
        if pet["weight"] > 600:
            return None
        return pet

    def get_pet_names(self):
        if self.user is None:
            self.get_user_details()
        return [p["name"] for p in self.user["dogs"]]
