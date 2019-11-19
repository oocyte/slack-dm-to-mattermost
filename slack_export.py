#!/bin/env python3.6
# MIT License

# Copyright (c) 2016 Chandler Abraham

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from slacker import Slacker
import json
import argparse
import os
import time
import sys
import re

# This script finds all channels, private channels and direct messages
# that your user participates in, downloads the complete history for
# those converations and writes each conversation out to seperate json files.
#
# This user centric history gathering is nice because the official slack data exporter
# only exports public channels.
#
# PS, this only works if your slack team has a paid account which allows for unlimited history.
#
# PPS, this use of the API is blessed by Slack.
# https://get.slack.help/hc/en-us/articles/204897248
# " If you want to export the contents of your own private groups and direct messages
# please see our API documentation."
#
# get your slack user token at the bottom of this page
# https://api.slack.com/web
#
# dependencies: 
#  pip install slacker # https://github.com/os/slacker
#
# usage examples
#  python slack_history.py --token='123token'
#  python slack_history.py --token='123token' --dryRun=True
#  python slack_history.py --token='123token' --skipDirectMessages
#  python slack_history.py --token='123token' --skipDirectMessages --skipPrivateChannels

# Gloabl Variables
#outputDir = str(int(time.time()))
outputDir = "test"
userList = []
teamId = "T0G6PUBAT"

# fetches the complete message history for a channel/group/im
#
# pageableObject could be:
# slack.channel
# slack.groups
# slack.im
# 
# channelId is the id of the channel/group/im you want to download history for.

def getHistory(pageableObject, channelId, pageSize = 100):
  messages = []
  lastTimestamp = None

  while(True):
    response = pageableObject.history(
      channel = channelId,
      latest  = lastTimestamp,
      oldest  = 0,
      count   = pageSize
    ).body

    messages.extend(response['messages'])

    if (response['has_more'] == True):
      lastTimestamp = messages[-1]['ts'] # -1 means last element in a list
    else:
      break
  return messages

def mkdir(directory):
  if not os.path.exists(directory):
    os.makedirs(directory)

# fetch and write history for all direct message conversations
# also known as IMs in the slack API.
def getDirectMessages(slack, ownerId, userIdNameMap, dryRun):
  dms = slack.im.list().body['ims']
  
  print("\nfound direct messages (1:1) with the following users:")
  for dm in dms:
    print(userIdNameMap.get(dm['user'], dm['user'] + " (name unknown)"))
  
  dmManifest = []
  if not dryRun:
    mkdir(outputDir)
    for dm in dms:
      dmid = dm['id']
      name = userIdNameMap.get(dm['user'], dm['user'] + " (name unknown)")
      if dm['user'] not in userList: userList.append(dm['user'])
      print("getting history for direct messages with {0}".format(name))
      dmOutputDir = "%s/%s" % (outputDir, dmid)
      mkdir(dmOutputDir)
      fileName = "%s/%s.json" % (dmOutputDir, dmid)
      messages = getHistory(slack.im, dm['id'])
      # Xin - Prevent Rate Limiting
      time.sleep(15)
      dmManifest.append({'id': dm['id'], 'created': dm['created'], 'members': [ownerId, dm['user']]})
      with open(fileName, 'w') as outFile:
        print("writing {0} records to {1}".format(len(messages), fileName))
        json.dump(messages, outFile, ensure_ascii=False, indent=4)
    dmManifestFileName = "%s/dms.json" % (outputDir)
    with open(dmManifestFileName, 'w') as outFile:
      print("writing direct message manifest for {0} channels to {1}".format(len(dmManifest), dmManifestFileName))
      json.dump(dmManifest, outFile, ensure_ascii=False, indent=4)

# fetch and write history for all private channels
# also known as groups in the slack API.
def getGroupDirectMessages(slack, ownerId, userIdNameMap, dryRun):
  groups = slack.groups.list().body['groups']
  
  print("\nfound group direct messages:")
  for group in groups:
    if re.match("^mpdm-", group['name']):
      print("{0}: ({1} members)".format(group['name'], len(group['members'])))

  mpdmManifest = []
  if not dryRun:
    mkdir(outputDir)
    for group in groups:
      if not re.match("^mpdm-", group['name']): continue

      mpdmid = group['id']
      mpdmname = group['name']
      for member in group['members']:
        if member not in userList: userList.append(member)
      print("getting history for group direct messages for {0}".format(mpdmname))
      mpdmOutputDir = "%s/%s" % (outputDir, mpdmname)
      mkdir(mpdmOutputDir)
      fileName = "%s/%s.json" % (mpdmOutputDir, mpdmname)
      messages = getHistory(slack.groups, mpdmid)
      # Xin - Prevent Rate Limiting
      time.sleep(15)
      mpdmManifest.append(group)
      with open(fileName, 'w') as outFile:
        print("writing {0} records to {1}".format(len(messages), fileName))
        json.dump(messages, outFile, ensure_ascii=False, indent=4)
    mpdmManifestFileName = "%s/mpims.json" % (outputDir)
    with open(mpdmManifestFileName, 'w') as outFile:
      print("writing group direct message manifest for {0} channels to {1}".format(len(mpdmManifest), mpdmManifestFileName))
      json.dump(mpdmManifest, outFile, ensure_ascii=False, indent=4)

# fetch all associated users encountered during our DM and Group DM export
def getUserList(slack):
  encounteredUsers = []
  users = slack.users.list().body['members']
  for user in users:
    if user['id'] in userList:
      encounteredUsers.append(user)
      userList.remove(user['id'])
  for missingUser in userList:
    userStruct = {'id' : missingUser, 'team_id': teamId, 'name' : 'generated-%s' % missingUser, 'profile' : { 'first_name': "Generated", 'last_name': missingUser, 'email' : '%s@dummy.com' % missingUser } }
    encounteredUsers.append(userStruct)
  userListFileName = "%s/users.json" % (outputDir)
  with open(userListFileName, 'w') as outFile:
    print("writing encountered user list {0}".format(userListFileName))
    json.dump(encounteredUsers, outFile, ensure_ascii=False, indent=4)

# fetch all users for the channel and return a map userId -> userName
def getUserMap(slack):
  #get all users in the slack organization
  users = slack.users.list().body['members']
  userIdNameMap = {}
  for user in users:
    userIdNameMap[user['id']] = user['name']
  print("found {0} users ".format(len(users)))
  return userIdNameMap

# get basic info about the slack channel to ensure the authentication token works
def doTestAuth(slack):
  testAuth = slack.auth.test().body
  teamName = testAuth['team']
  currentUser = testAuth['user']
  print("Successfully authenticated for team {0} and user {1} ".format(teamName, currentUser))
  return testAuth

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description='download slack history')

  parser.add_argument('--token', help="an api token for a slack user")

  parser.add_argument(
    '--dryRun',
    action='store_true',
    default=False,
    help="if dryRun is true, don't fetch/write history only get channel names")

  parser.add_argument(
    '--includeGroupDirectMessages',
    action='store_true',
    default=False,
    help="Fetch History for GroupDirectMessages")

  parser.add_argument(
    '--includeDirectMessages',
    action='store_true',
    default=False,
    help="Fetch History for DirectMessages")

  args = parser.parse_args()

  slack = Slacker(args.token)

  testAuth = doTestAuth(slack)

  userIdNameMap = getUserMap(slack)

  dryRun = args.dryRun

  userList.append(testAuth['user_id'])

  if args.includeDirectMessages:
    getDirectMessages(slack, testAuth['user_id'], userIdNameMap, dryRun)

  if args.includeGroupDirectMessages:
    getGroupDirectMessages(slack, testAuth['user_id'], userIdNameMap, dryRun)

  getUserList(slack)
