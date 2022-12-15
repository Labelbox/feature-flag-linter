import os
import requests
from datetime import date
from dotenv import load_dotenv

# Load environmental variables from a .env file
load_dotenv()

def get_feature_flag_data():
  """
  Makes a GET request to the LaunchDarkly API to retrieve data
  about the flags in a project.
  """
  # Set the project key
  project_key = "default"
  # Set the URL for the request
  url = "https://app.launchdarkly.com/api/v2/flags/" + project_key
  # Get the LaunchDarkly secret from the environment
  ld_secret = os.environ.get('LAUNCH_DARKLY_KEY')
  # Set the headers for the request
  headers = {"Authorization": ld_secret}
  # Make the request and return the JSON response
  response = requests.get(url, headers=headers)
  return response.json()

# Initialize a string to store the message for Slack
content = "Hello! :wave: The following feature flags are out of compliance :point_down:\n"
# Initialize counters for flags in compliance, out of compliance, and skipped
good_count = 0
bad_count = 0
skipped = 0
# Set the required prefixes for tags
required_prefix = ["group_", "department_", "team_", "life_", "jira_"]

def get_slack_id(email):
  """
  Makes a POST request to the Slack API to look up a user's Slack ID
  based on their email address.
  """
  # Set the URL for the request
  url = "https://slack.com/api/users.lookupByEmail"
  # Get the Slack bot secret from the environment
  slack_bot_secret = os.environ.get('SLACK_BOT_KEY')
  # Set the data for the request
  data = [
    ('token', slack_bot_secret),
    ('email', email)
  ] 
  # Make the request and return the JSON response
  response = requests.post(url, data) 
  if response.json()['ok']:
    return response.json()['user']['id']
  else:
    return None

# Get the data about the flags
data = get_feature_flag_data()

# Print the date of the compliance check
print("******************")
print("Date:", date.today())

# Iterate over the flags
for item in data["items"]:
  # All older flags do not adhere to the FF policy.
  if item["creationDate"] < 1668455118397:
    # Increment the skipped counter
    skipped += 1 
    continue
  # Initialize an array to store missing tags
  is_missing = []
  # Iterate over the required prefixes
  for rp in required_prefix:
    # Set a flag to indicate if the tag is present
    has_tag = False
    # Iterate over the item's tags
    for tag in item["tags"]:
      # If a tag starts with the required prefix, set the flag to True
      if tag.startswith(rp):
        has_tag = True
    # If the flag is still False, add the prefix to the list
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
    content += ":warning: The following tags are missing>:\n %s \n" % is_missing 
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
