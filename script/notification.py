import os

import requests

from petkit_exporter.petkit import PetKit

petkit_username = os.environ["PETKIT_USERNAME"]
petkit_password = os.environ["PETKIT_PASSWORD"]
ifttt_key = os.environ["IFTTT_KEY"]

petkit = PetKit(petkit_username, petkit_password)

devices = petkit.discover_devices()
require_cleans = [
    device.name
    for device in devices
    if petkit.get_device_details(device)['state']['boxFull']]
if len(require_cleans) > 0:
    r = requests.get(
        f"https://maker.ifttt.com/trigger/litter_box_is_full/json/with/key/{ifttt_key}",
        data={"value1": " and ".join(require_cleans)}
    )
    print(r.content)
else:
    print("No need to clean for now!")
