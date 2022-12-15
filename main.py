import os
import requests
from datetime import date
from dotenv import load_dotenv
load_dotenv()

def get_feature_flag_data():
  project_key = "default"
  url = "https://app.launchdarkly.com/api/v2/flags/" + project_key
  ld_secret = os.environ.get('LAUNCH_DARKLY_KEY')
  headers = {"Authorization": ld_secret}
  response = requests.get(url, headers=headers)
  return response.json()

content = "Hello! :wave: The following feature flags are out of compliance :point_down:\n"
good_count = 0
bad_count = 0
skipped = 0
required_prefix = ["group_", "department_", "team_", "life_", "jira_"]

def get_slack_id(email):
  url = "https://slack.com/api/users.lookupByEmail"
  slack_bot_secret = os.environ.get('SLACK_BOT_KEY')
  data = [
    ('token', slack_bot_secret),
    ('email', email)
  ] 
  response = requests.post(url, data) 
  if response.json()['ok']:
    return response.json()['user']['id']
  else:
    return None

data = get_feature_flag_data()
print("******************")
print("Date:", date.today())
for item in data["items"]:
  # All older flags do not adhere to the FF policy.
  if item["creationDate"] < 1668455118397:
    skipped += 1 
    continue
  is_missing = []
  for rp in required_prefix:
    has_tag = False
    for tag in item["tags"]:
      if tag.startswith(rp):
        has_tag = True
    if not has_tag:
      is_missing.append(rp)
  if not is_missing and item["description"]:
    good_count += 1
    continue
  print("========")
  print("Name: %s" % item["name"])
  print("Creation Date %s" % item["creationDate"])
  print("Tags: %s" % item["tags"])
  print("Description: %s" % item["description"])
  slack_id = ""
  if "_maintainer" in item:
    print("Maintainer: %s" % item["_maintainer"]["email"])
    slack_id = get_slack_id(item["_maintainer"]["email"])
  if is_missing:
    print("Missing tags: %s" % is_missing)
  if not item["description"]:
    print("Description is missing")
  bad_count += 1

  # Build the message for slack.
  content += "---------------------------\n"
  content += "*Name*: %s\n" % item["name"]
  if "_maintainer" in item:
    content += "*Maintainer*: %s\n" % item["_maintainer"]["email"]
    if slack_id:
      content += "<@%s>\n" % slack_id
  content += "*Tags*: %s\n" % item["tags"]
  if is_missing:
    content += ":warning: <https://labelbox.atlassian.net/wiki/spaces/ENG/pages/1901199406/Feature+Flags+Engineering+Policy#Tags|The following tags are missing>:\n %s \n" % is_missing 
  if not item["description"]:
    content += ":warning: Description is missing! Please add it.\n"

print("")
print("========Summary========")
print("Flags in compliance: %s" % good_count)
print("Flags out of compliance: %s" % bad_count)
print("Flags skipped: %s" % skipped)
print("Total number of flag: %s" % len(data["items"]))
if bad_count > 0:
  url = os.environ.get('SLACK_CHANNEL_URL')
  headers = {"Content-type": "application/json"}
  response = requests.post(url, data='{"text":"' + content + '"}', headers=headers)
  print("Slack response: ", response.text)
