from operator import imod
import os
from unittest import mock

import pytest

from petkit_exporter.petkit import CleanEvent, PetEvent, PetKit, Device


@pytest.mark.skipif(
    os.getenv("PETKIT_USERNAME") and os.getenv("PETKIT_PASSWORD"),
    reason="requires `PETKIT_USERNAME` and `PETKIT_PASSWORD` to be configured")
@pytest.fixture(scope="module")
def petkit():
    username = os.environ["PETKIT_USERNAME"]
    password = os.environ["PETKIT_PASSWORD"]
    return PetKit(username, password)


def test_get_user_details(petkit):
    petkit.get_user_details()
    assert petkit.user is not None


def test_discover_devices(petkit):
    devices = petkit.discover_devices()
    assert len(devices) > 0
    assert all(
        isinstance(device, Device)
        for device in devices
    )


def test_get_device_records(petkit):
    for device in petkit.discover_devices():
        records = petkit.get_device_records(device)
        assert len(records) > 0


@pytest.fixture
def mock_find_pet(petkit):
    with mock.patch.object(
        petkit, "find_most_possible_pet",
        return_value={"name": "test-pet", "weight": 1000}
    ):
        yield


@pytest.mark.parametrize("record,expected_type", [
    (
        {
            "eventType": 10,
            "timestamp": 1,
            "content": {
                "timeIn": 1,
                "timeOut": 2,
                "petWeight": 10
            }

        },
        PetEvent
    ),
    (
        {
            "eventType": 5,
            "timestamp": 1,
            "content": {
                "startTime": 1,
                "startReason": 0,
                "litterPercent": 50,
                "boxFull": False
            }
        },
        CleanEvent
    ),
    (
        {
            "eventType": 8,
            "timestamp": 1,
            "content": {
                "startTime": 1,
                "startReason": 0,
                "liquid": 10,
                "liquidLack": False
            }
        },
        CleanEvent
    ),
    (
        {
            "eventType": 7,
            "timestamp": 1,
            "content": {
                "startTime": 1,
                "startReason": 0,
            }
        },
        CleanEvent
    )
])
def test_parse_rcord(petkit, mock_find_pet, record, expected_type):
    device = Device(1, "test-device", "t3")
    _, parsed = petkit.parse_record(device, record)
    assert isinstance(parsed, expected_type)


@pytest.fixture
def mock_pets(petkit):
    with mock.patch.object(petkit, "get_user_details"):
        petkit.user = {
            "dogs": [
                {"name": "test1", "weight": 1},
                {"name": "test2", "weight": 3},
            ]
        }
        yield


@ pytest.mark.parametrize("weight,expected", [
    (900, "test1"),
    (2700, "test2"),
    (4000, None),
])
def test_find_most_possible_pet(petkit, mock_pets, weight, expected):
    if expected is not None:
        assert petkit.find_most_possible_pet(weight)["name"] == expected
    else:
        assert petkit.find_most_possible_pet(weight) is None
