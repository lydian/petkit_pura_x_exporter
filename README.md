# Petkit Pura X Exporter

This is for exporting petkit pura X to external services (currently only support google sheets)

- Exporting to external services so that you can keep the log more than 24 hours
- A dedicated tracking log for each pets if you have multiple pets and their weight are different. (Right now the app only have the combined view)

## How to use the script ?

1. Fork the Repo
2. Create a Google Service Account, and get the key.json
    1. Visit https://console.cloud.google.com/iam-admin/ create new project
    2. Enable Google sheets Library
    3. Create a service account: https://console.cloud.google.com/iam-admin/serviceaccounts

3. Create a new spreadsheet and shared with the service account you just created.
4. Configure the secrets in the repository:
    - `AUTH_JSON`:  The plain json content from downloaded key.json of your service account
    - `SPREADSHEET_ID`: The id of the spreadsheet that you had shared with the service account
    - `PETKIT_USERNAME`: the petkit app login user name
    - `PETKIT_PASSWORD`: the petkit app login password

Once completed. The github action is schedule to run every 15 mins and will update the spreadsheet when there's newer event.
