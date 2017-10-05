#! /usr/bin/env python2.7

import os
import json
from datetime import date

import ast
import indigo
from slackclient import SlackClient

# Globals
plugin_id = "com.rafael-ortiz.indigoplugin.slack-notify"

class Plugin(indigo.PluginBase):
    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        indigo.PluginBase.__init__(
            self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs
        )

        self.debug = pluginPrefs.get("showDebugInfo", False)
        self.channels = {}
        self.config = {}
        self.team_members = {}
        self.slack_client = None

    def __del__(self):
        indigo.PluginBase.__del__(self)

    def _debugLog(self, msg):
        self.debugLog(unicode(msg))

    def _errorLog(self, msg):
        self.errorLog(unicode(msg))

    def _log(self, msg):
        indigo.server.log(unicode(msg))

    def _getChannels(self):
        channels = {}

        self._debugLog("_get_channels: Loading Slack channels")

        result = self.slack_client.api_call(
            "channels.list",
            exclude_archived=1
        )

        if not result.get('ok', False):
            err = result.get('error', "unknown error")
            self._errorLog("Failed to get Slack channel names: {}".format(err))
            return channels

        for chan in result['channels']:
            if not chan.get('is_channel', False):
                self._debugLog("_get_channels: Not a channel: {}".format(chan))
                continue

            if chan['name'] in channels.keys():
                continue

            channels[chan['name']] = {
                'id': chan['id']
            }

        self._debugLog("_get_channels: Slack Channels: {}".format(channels))
        return channels

    def _pickChannel(self, channel=None, dm=None):
        if channel and dm:
            channel = "@" + dm
        elif not channel:
            if not dm:
                return None
            else:
                channel = "@" + dm
        else:
            channel = "#" + channel

        return channel

    def _getTeamMembers(self):
        team_members = {}

        result = self.slack_client.api_call('users.list')

        if not result.get('ok', False):
            err = result.get("error", "unknown error")
            self._errorLog("Failed to get team member info: {}".format(err))
            return team_members

        for member in result['members']:
            if member['deleted']:
                continue

            team_members[member['id']] = {
                'name': member['name'],
                'profile': member['profile']
            }

        return team_members

    def _evalCondition(self, testValue, conditional):
        """
            Evaluate a value against a conditional string by converting
            the string to a python object. If that fails, we just do a
            direct string comparison
        """
        try:
            conditions = ast.literal_eval(conditional)
        except ValueError:
            conditions = conditional

        if isinstance(conditions, basestring):
            self._debugLog("_eval_condition: Evaluating condition as string")
            if conditions.lower() in ['true', 'false']:
                self._debugLog("_eval_condition: Evaluating condition as true/false")
                conditions = conditions.lower()

            if testValue == conditions:
                return True
        else:
            self._debugLog("_eval_condition: Evaluating condition as iterable")
            if testValue in conditions:
                return True

        return False

    def _returnLogPath(self):
        ver = int(indigo.server.version[0])
        baseDir = r"/Library/Application Support/Perceptive Automation/Indigo {}/".format(ver)
        fileDate = str(date.today())
        logPath = os.path.join(baseDir + 'Logs', fileDate + ' Events.txt ')
        return logPath

    def startup(self):
        self._debugLog("startup called")
        self._debugLog("Indigo log path: {}".format(self._returnLogPath()[0:-1]))

        self.config['auth'] = {
            'url_token': self.pluginPrefs.get('urltoken', '').strip(),
            'slack_token': self.pluginPrefs.get('slacktoken', '').strip(),
            'user_id':  self.pluginPrefs.get('userid', '').strip()
        }

        self.config['api'] = {
            'channel_list': 'https://slack.com/api/channels.list',
            'file_upload': 'https://slack.com/api/files.upload',
            'user_info': 'https://slack.com/api/users.info'
        }

        self.slack_client = SlackClient(self.config['auth']['slack_token'])

        # Get the slack user details once on startup,
        # instead of before every message
        self.refreshSlackData()
        self._debugLog("startup complete")


    def shutdown(self):
        self._debugLog("shutdown called")

    def refreshSlackData(self):
        self.team_members = self._getTeamMembers()
        self._debugLog("refresh_slack_data: Loaded {} team members".format(len(self.team_members)))

        user_id = self.config['auth']['user_id']
        self.config['user'] = self.team_members.get(user_id, None)
        self.channels = self._getChannels()

    def channelListGenerator(
            self, filter="", valuesDict=None, typeId="", targetId=0):
        chanlist = []

        for name, chan in self.channels.iteritems():
            cl = (name, name)
            chanlist.append(cl)

        return chanlist

    def validatePrefsConfigUi(self, valuesDict):
        self._debugLog("validatePrefsConfigUi() method called")
        errorsDict = indigo.Dict()
        errorsFound = False


        if not valuesDict[u'slacktoken']:
            errorsDict[u'slacktoken'] = u'The plugin requires a Slack token.'
            errorsFound = True

        if " " in valuesDict[u'slacktoken']:
            errorsDict[u'slacktoken'] = u'The Slack token can not contain spaces.'
            errorsFound = True

        if valuesDict[u'userid']:
            if not valuesDict[u'userid'].startswith('U'):
                errorsDict[u'userid'] = u"User id should start with 'U'"
                errorsFound = True

            if " " in valuesDict[u'userid']:
                errorsDict[u'userid'] = u'The Slack user ID can not contain spaces.'
                errorsFound = True

        if errorsFound:
            return (False, valuesDict, errorsDict)

        return (True, valuesDict)

    def closedPrefsConfigUi(self, valuesDict, userCancelled):
        self._debugLog("closedPrefsConfigUi() method called")

        if userCancelled is True:
            self._debugLog("User cancelled updating preferences")

        if userCancelled is False:
            self._log("Slack Notify preferences were updated.")
            self.debug = valuesDict.get('showDebugInfo', False)

        if self.debug is True:
            self._debugLog("Debugging on")
            self._debugLog("Debugging set to: {}".format(self.pluginPrefs["showDebugInfo"]))

    def upload(self, pluginAction):
        uploadParams = {
            'file': None,
            'title': '',
            'comment': '',
            'channels': None
        }

        filePath = pluginAction.props['filename'].strip()

        if filePath is not None:
            for i in range(0, 3):
                if "%%v:" in filePath:
                    filePath = self.substituteVariable(filePath)

        self._debugLog("upload: Preparing to upload file from {}".format(filePath))

        try:
            uploadParams['file'] = open(filePath, 'rb')
        except IOError as e:
            self._errorLog("Failed to open file for upload: {}".format(e))
            return None

        uploadParams['filename'] = filePath

        if pluginAction.props['filetitle']:
            uploadParams['title'] = pluginAction.props['filetitle']

        if pluginAction.props['filecomment']:
            uploadParams['comment'] = pluginAction.props['filecomment']

        channel = pluginAction.props['channel']
        dm = pluginAction.props['directMessage'].strip()

        channel = self._pickChannel(channel, dm)

        if channel is None:
            self._errorLog("Missing channel or DM to upload file")
            return None

        uploadParams['channels'] = channel

        result = self.slack_client.api_call("files.upload", **uploadParams)
        self._debugLog("upload: files.upload response: {}".format(result))

        if not result.get('ok', False):
            err = result.get('error', "unknown error")
            self._errorLog("File upload Failed: {}".format(err))
            return None

        slack_file = result.get('file', None)

        if slack_file is not None:
            self._log("File uploaded")

        return slack_file

    def notify(self, pluginAction):
        msgTxt = pluginAction.props['text'].strip()
        msgUsername = pluginAction.props['username'].strip()
        msgIcon = pluginAction.props['icon'].strip()
        msgChan = pluginAction.props['channel'].strip()
        dm = pluginAction.props['directMessage'].strip()
        imgURL = pluginAction.props['imageurl'].strip()

        enableMention = pluginAction.props.get('enableMention', False)
        conditionalMention = pluginAction.props.get('conditionalMention', False)
        mentionConditionVar = pluginAction.props.get('mentionConditionVar', '').strip()
        mentionConditionVal = pluginAction.props.get('mentionConditionVal', '').strip()


        if msgTxt is not None:
            ## Substitute indigo variable strings
            ## (range to avoid getting stuck in the loop)
            for i in range(0, 3):
                if "%%v:" in msgTxt:
                    msgTxt = self.substituteVariable(msgTxt)
        else:
            self._errorLog("No message text provided for Slack Notify.")
            return None

        self._debugLog("notify: Message Text: {}".format(msgTxt))

        isChannel = False
        channel = self._pickChannel(msgChan, dm)

        if channel is None:
            self._errorLog("Missing channel OR a DM to post message.")
            return None

        if channel.startswith("#"):
            isChannel = True

        ## Determine if we need to add an '@channel' mention
        if enableMention and isChannel:
            mention = "\n<!channel>"

            if not conditionalMention:
                msgTxt += mention
            else:
                testValue = self.substituteVariable("%%v:" + mentionConditionVar + "%%")
                self._debugLog("notify: mentionConditionVar: {} = {} ".format(mentionConditionVar, testValue))
                self._debugLog("notify: mentionConditionVal: {}".format(mentionConditionVal))

                if self._evalCondition(testValue, mentionConditionVal):
                    msgTxt += mention

        self._debugLog("notify: Final Message Text: {}".format(msgTxt))

        userName = "indigo"
        userIconURL = None

        user = self.config['user']

        if user is not None:
            userName = user.get('name', '')

            if 'profile' in user:
                userIconURL = user['profile'].get('image_24', None)

            if not msgUsername:
                msgUsername = userName


        self._debugLog("notify: msgUsername set to {} (bot)".format(msgUsername))
        self._debugLog("User icon url set to: {}".format(userIconURL))

        payload = {'link_names': '1'}
        payload['text'] = msgTxt
        payload['channel'] = channel
        payload['username'] = msgUsername

        if msgIcon:
            payload['icon_emoji'] = ":" + msgIcon + ":"

        if imgURL:
            attachment = [{
                'fallback': "Image is attached",
                'image_url': imgURL
            }]
            payload['attachments'] = json.dumps(attachment)

        result = self.slack_client.api_call("chat.postMessage", **payload)
        if not result.get('ok', False):
            err = result.get('error', "unknown error")
            self._errorLog("Failed to post message: {}".format(err))
            return None

        self._log("Message sent")
        return True
