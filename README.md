# slack-dm-to-mattermost
Export Slack Direct Message and Group Direct Messages into the same format as "Corporate Export", this can be then imported into MatterMost via the `slack import` cli function or via Team Import page in the Web Interface.

Original script copied from: https://github.com/zach-snell/slack-export

This script makes use of API token. You can either request a Legacy Token at: https://api.slack.com/custom-integrations/legacy-tokens

Or, you can setup a Bot and create an Oauth token: https://api.slack.com/apps
```
Create New App

App Name -> Direct Message Export
Slack Workspace -> IBM Algo Risk Service

Under Add Features and Functionality, click on Permissions

Go down to Scopes, add the following permissions:
 - users:read
 - users:read.email
 - users.profile:read
 - usergroups:read
 - reactions:read
 - stars:read
 - pins:read
 - mpim:read
 - mpim:history
 - links:read
 - im:read
 - im:history
 - identify
 - groups:read
 - groups:history

Scroll back up, click on the Request to Install Button

After your request is approved by the Team Admin, go back to the App Page, Oauth and Permissions
- click on Install App to WorkSpace
- note your Oauth token
```


To run the script, first create a python environment:
```
python3 -m venv ~/python3
source ~/python3/bin/activate
python3 -m pip install slacker
```

To run the export:
```
./slack_export.py --token <token> --includeGroupDirectMessages --includeDirectMessages
```

This will create `~/slackdmexport/test` directory with users.json, mpims.json, dms.json and the associated directories. You can now run a zip command to package it into a Slack Corporate Export format zip.
```
cd test
zip -r ../slackdms.zip .
```

To import the data into mattermost local install:
- Install docker desktop: https://hub.docker.com/?overlay=onboarding
- Create an account on DockerHub: https://hub.docker.com
- Install mattermost preview: https://github.com/mattermost/mattermost-docker-preview
- Navigate to mattermost local install: http://localhost:8065
  - register using your IBM email
  - create a team
  - goto the admin console and update maximum user count to 500: http://localhost:8065/admin_console/site_config/users_and_teams
- Go back to your local install http://localhost:8065/<team>, from the drop down navigation menu, select Team Settings -> Import
- Upload your zip file created from the previous step and import data
- NOTE: for users that are not part of our workspace (from another team or left the company, their IDs will be in the form of **generated-<ID>**
