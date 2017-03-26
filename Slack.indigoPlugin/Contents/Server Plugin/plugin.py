#! /usr/bin/env python2.5
# -*- coding: utf-8 -*-
import ast
import indigo
import simplejson
import urlparse, httplib
import hashlib
from datetime import date
import os
import sys
import platform
import MultipartPostHandler
import urllib
import urllib2

# Globals
plugin_id = "com.bot.indigoplugin.slack"

class Plugin(indigo.PluginBase):
    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
        self.debug = pluginPrefs.get("showDebugInfo", False)
        self.channels = {}
        self.config = {}

    def __del__(self):
        indigo.PluginBase.__del__(self)

    def startup(self):
        self.debugLog(u"startup called")
        self.debugLog(u"Indigo log path: %s" % self.returnlogpath ()[0:-1] )

        self.config['auth'] = {
            'url_token': self.pluginPrefs.get('urltoken','').strip(),
            'slack_token': self.pluginPrefs.get('slacktoken','').strip(),
            'user_id':  self.pluginPrefs.get('userid','').strip()
        }

        self.config['api'] = {
            'channel_list': 'https://slack.com/api/channels.list',
            'file_upload': 'https://slack.com/api/files.upload',
            'user_info': 'https://slack.com/api/users.info',
            'service_url': "https://hooks.slack.com/services/%s" % (self.config['auth']['url_token'])
        }

        ## Get the slack user details once on startup, instead of before every message
        self.refresh_slack_data()
        self.debugLog(u"startup complete")


    def shutdown(self):
        self.debugLog(u"shutdown called")

    def returnlogpath(self):
        baseDir = r"/Library/Application Support/Perceptive Automation/Indigo %s/" % (int(indigo.server.version[0]) )
        fileDate = str(date.today())
        logPath = os.path.join(baseDir + 'Logs', fileDate + ' Events.txt ')
        return logPath

    def shorten(self, url):
        # http://taoofmac.com/space/blog/2009/08/10/2205
        # BITLY_TOKEN = 'addtoken'
        services = {
        # 'api-ssl.bitly': '/v3/shorten?access_token=%s&longUrl=' % BITLY_TOKEN,
        # 'api.tr.im':   '/api/trim_simple?url=',
        'tinyurl.com': '/api-create.php?url=',
        'is.gd':       '/api.php?longurl='
        }
        for shortener in services.keys():
            c = httplib.HTTPConnection(shortener)
            c.request("GET", services[shortener] + urllib.quote(url))
            r = c.getresponse()
            shorturl = r.read().strip()
            if ("DOCTYPE" not in shorturl) and ("http://" + urlparse.urlparse(shortener)[1] in shorturl):
                return shorturl
            else:
                continue
            # raise IOError

    def refresh_slack_data(self):
        self.config['user'] = self._get_user_info()
        self.channels = self._get_channels()


    def _get_channels(self):
        channels = {}

        self.debugLog("Loading Slack channels")

        params = {
            'token': self.config['auth']['slack_token'],
            'pretty': 1
        }

        url = self.config['api']['channel_list']

        result = self._do_slack_request_get(url,params)

        if result is None:
            self.errorLog("Failed to get Slack channel names")
            return channels

        cl = simplejson.loads(result)

        for chan in cl['channels']:
            channel = {}

            if not chan.get('is_channel',False):
                continue

            if chan.get('is_archived',False):
                continue

            if chan['name'] in channels.keys():
                continue

            channels[chan['name']] = {
                'id': chan['id']
            }

        self.debugLog("Slack Channels: %s" % (channels))

        return channels



    def getChannelNames(self):
        slackToken = self.pluginPrefs['slacktoken'].strip()
        params = urllib.urlencode({'token': slackToken, 'pretty': 1})
        url = urllib.urlopen("https://slack.com/api/channels.list?%s" % params)
        url = url.geturl()

        self.debugLog(u"Channels URL: %s" % url)

        jc = urllib2.urlopen(url)
        channelString = jc.read()
        jcl = simplejson.loads(channelString)

        cList = []
        for i in jcl['channels']:
            x = i['name']
            if x not in cList:
                cList.append(x)

        oList = list(cList)

        deck = []
        for i in range(len(cList)):
            while True:
                card = (oList[i],cList[i])
                deck.append(card)
                break

        self.debugLog(deck)
        return deck

    def channelListGenerator(self, filter="", valuesDict=None, typeId="", targetId=0):
        chanlist = []
        for name,chan in self.channels.iteritems():
            cl = (name,name)
            chanlist.append(cl)

        return chanlist


    # def channelListGenerator(self, filter="", valuesDict=None, typeId="", targetId=0):
    #     return self.getChannelNames()

    def validatePrefsConfigUi(self, valuesDict):
        self.debugLog(u"validatePrefsConfigUi() method called")
        errorsDict = indigo.Dict()
        errorsFound = False

        if len(valuesDict[u'urltoken']) == 0:
            errorsDict[u'urltoken'] = u'The plugin requires a Slack webhook token.'
            errorsFound = True
        if " " in (valuesDict[u'urltoken']):
            errorsDict[u'urltoken'] = u'The Slack webhook token can not contain spaces.'
            errorsFound = True

        if len(valuesDict[u'slacktoken']) == 0:
            errorsDict[u'slacktoken'] = u'The plugin requires a Slack token.'
            errorsFound = True
        if " " in (valuesDict[u'slacktoken']):
            errorsDict[u'slacktoken'] = u'The Slack token can not contain spaces.'
            errorsFound = True

        if len(valuesDict[u'userid']) == 0:
            errorsDict[u'userid'] = u'The plugin requires a Slack user ID.'
            errorsFound = True
        if " " in (valuesDict[u'userid']):
            errorsDict[u'userid'] = u'The Slack user ID can not contain spaces.'
            errorsFound = True

        if errorsFound:
            return (False, valuesDict, errorsDict)
        else:
            return (True, valuesDict)

    def closedPrefsConfigUi (self, valuesDict, userCancelled):
        self.debugLog(u"closedPrefsConfigUi() method called")

        if userCancelled is True:
            self.debugLog(u"User cancelled updating preferences")

        if userCancelled is False:
            indigo.server.log (u"Slack Notify preferences were updated.")
            self.debug = valuesDict.get('showDebugInfo', False)

        if self.debug is True:
            self.debugLog(u"Debugging on")
            self.debugLog(unicode(u"Debugging set to: %s" % self.pluginPrefs[u"showDebugInfo"]))


    def upload(self, pluginAction):
        uploadParams = {
            'file': None,
            'title': '',
            'comment': '',
            'channels': None,
            'token': self.config['auth']['slack_token']
        }

        filePath = pluginAction.props['filename'].strip()

        if filePath is not None:
            while "%%v:" in filePath:
                filePath = self.substituteVariable(filePath)

        self.debugLog(u"Preparing to upload file from %s" % (filePath))

        try:
            uploadParams['file'] = open(filePath,'rb')
        except IOError, e:
            self.errorLog("Failed to open file for upload: %s" % (e))
            return None

        uploadParams['filename'] = filePath

        if len(pluginAction.props['filetitle']):
            uploadParams['title'] = pluginAction.props['filetitle']

        if len(pluginAction.props['filecomment']):
            uploadParams['comment'] = pluginAction.props['filecomment']

        channel = pluginAction.props['channel']
        dm = pluginAction.props['directMessage'].strip()

        if channel and dm:
            channel = dm
        elif not channel:
            if not dm:
                self.errorLog(u"Enter either a channel or DM to post to")
                return None
            else:
                channel = dm

        uploadParams['channels'] = channel

        res = self._do_slack_request(url=self.config['api']['file_upload'], data=uploadParams,method="POST")
        self.debugLog(u"File upload response: %s" % res)
        
        fres = simplejson.loads(res)

        if fres is None:
            self.errorLog(u"Upload request failed")
            return None

        if not fres.get('ok',False):
            self.errorLog(u"File upload Failed: %s" % fres['error'])
            return None

        slack_file = fres.get('file',None)

        if slack_file is not None:
            indigo.server.log(u"File uploaded.")

        return fres.get('file',None)

    def _pick_channel(self, channel=None,dm=None):
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

    def _get_user_info(self):
        self.debugLog(u"Retreiving Slack user variables")

        user = {}
        
        params = {
            'token': self.config['auth']['slack_token'],
            'user': self.config['auth']['user_id'],
            'pretty': 1
        }

        result = self._do_slack_request_get(url=self.config['api']['user_info'], data=params)

        if result is None:
            self.errorLog(u"Unable to load Slack user variables")
            return {}

        js = simplejson.loads(result)

        if js.get('ok', False) in [False]:
            self.errorLog(u"Failed to get user variables: %s" % js.get('error'))
            return {}

        if 'user' in js:
            user = js['user']

        self.debugLog(u"Slack User: %s" % (user))

        return user

    def _get_gravatar_url(self, email=None):
        default = "http://www.gravatar.com/avatar/c4ac5c1a595fe25bad7ddb2eb2d7c2f4?d=identicon"
        size = 16

        if email is None:
            return default

        email_digest = hashlib.md5(email.lower()).hexdigest()
        gravatar_url = "http://www.gravatar.com/avatar/" + email_digest + "?"
        gravatar_url += urllib.urlencode({'d':default, 's':str(size)})

        return gravatar_url

    def notify(self, pluginAction):
        msgTxt = pluginAction.props['text'].strip()

        if msgTxt is not None:
            while "%%v:" in msgTxt:
                msgTxt = self.substituteVariable(msgTxt)
        else:
            self.errorLog(u"No message text provided for Slack Notify.")
            return None

        self.debugLog(u"Message Text: %s" % (msgTxt))

        msgChan = pluginAction.props['channel'].strip()
        dm = pluginAction.props['directMessage'].strip()

        isChannel = False
        channel = self._pick_channel(msgChan, dm)

        if channel is None:
            self.errorLog(u"Enter either a channel OR a DM to post to.")
            return None

        if channel[0] == '#':
            isChannel = True


        ## Decide if we need to add a mention

        enableMention = pluginAction.props.get('enableMention',False)
        conditionalMention = pluginAction.props.get('conditionalMention',False)
        mentionConditionVar = pluginAction.props.get('mentionConditionVar','').strip()
        mentionConditionVal = pluginAction.props.get('mentionConditionVal','').strip()

        if enableMention and isChannel:
            mention = "<!channel>\n"            

            if not conditionalMention:
                msgTxt = mention + msgTxt
            else:
                varTestVal = self.substituteVariable("%%v:" + mentionConditionVar + "%%")
                self.debugLog("mentionConditionVar: %s = %s " % (mentionConditionVar,varTestVal))
                self.debugLog("mentionConditionVal: %s" % mentionConditionVal)

                
                ## Try converting the conditional value to a python object
                ## if that fails, just do a direct string comparison
                try:
                    conditions = ast.literal_eval(mentionConditionVal)
                except ValueError, e :
                    conditions = mentionConditionVal

                if isinstance(conditions,basestring):
                    self.debugLog("Evaluating condition as string")
                    if conditions.lower() in ['true','false']:
                        self.debugLog("Evaluating condition as true/false")
                        conditions = conditions.lower()

                    if varTestVal == conditions:
                        msgTxt = mention + msgTxt
                else:
                    self.debugLog("Evaluating condition as iterable")
                    if varTestVal in conditions:
                        msgTxt = mention + msgTxt


        self.debugLog(u"Message Text: %s" % (msgTxt))

        imgURL = pluginAction.props['imageurl'].strip()

        msgUsername = pluginAction.props['username'].strip()
        msgIcon = pluginAction.props['icon'].strip()
        ##############################################################################################

        # get Slack user variables
        # user = self._get_user_info()
        user = self.config['user']

        userName = user.get('name','')
        self.debugLog(u"Username set to %s (bot)" % userName)

        userIconURL = None
        userEmail = None
        if 'profile' in user:
            userIconURL = user['profile'].get('image_24',None)
            userEmail = user['profile'].get('email',None)

        if userIconURL is None:
            userIconURL = self._get_gravatar_url(userEmail)

        self.debugLog(u"User icon url set to: %s" % userIconURL)
        ##############################################################################################

        # construct and attempt to send payload to Slack #############################################
        if not msgUsername:
            msgUsername = userName

        surl = self.config['api']['service_url']
        self.debugLog(u"Slack payload url: %s" % surl)

        payload = {'link_names': '1'}
        payload['text'] = "%s" % (msgTxt)
        payload['channel'] = channel
        payload['username'] = msgUsername
        if msgIcon:
            payload['icon_emoji'] = ":" + msgIcon + ":"

        if imgURL:
            attachment = {
                'fallback': "Image is attached",
                'image_url': imgURL
            }
            payload['attachments'] = []
            payload['attachments'].append(attachment)

        data = "payload=%s" % (simplejson.dumps(payload))

        ## Decode the escaped string created by the dict->str conversion
        data= data.decode('string_escape')

        result = self._do_slack_request(surl,data,method="POST")

        if result is None:
            indigo.server.log(u"Failed to send message to slack")
            return None

        indigo.server.log(u"Message sent.")
        ##############################################################################################

    def _do_slack_request(self,url,data=None,method="GET"):
        if method == "GET":
            return self._do_slack_request_get(url,data)
        elif method == "POST":
            return self._do_slack_request_post(url,data)
        else:
            self.debugLog(u"Invalid request method for %s" % (url))
            return None

    def _do_slack_request_post(self,url,data):

        result = None
        opener = urllib2.build_opener(MultipartPostHandler.MultipartPostHandler)

        self.debugLog("Starting POST request for %s" % (url))
        self.debugLog("POST Data: %s" % (data))

        try:
            result = opener.open(url, data).read()
            self.debugLog(u"POST Response: %s" % str(result))
        except urllib2.HTTPError, e:
            self.errorLog(u"Failed to get URL. HTTPError - %s" % unicode(e))
        except urllib2.URLError, e:
            self.errorLog(u"Failed to get URL. URLError - %s" % unicode(e))
        except Exception, e:
            if "invalid literal for int() with base 16: ''" in e:
                self.errorLog(u"Exception: invalid literal for int() with base 16")
            else:
                self.errorLog(u"Exception - %s" % unicode(e))

        return result

    def _do_slack_request_get(self,url,data=None):
        ## Need to convert this to use requests
        if data is not None:
            try:
                params = urllib.urlencode(data)
            except TypeError:
                params = data

            url = url + "?" + params

        self.debugLog("Starting GET request for %s" % (url))
        urlobj = urllib.urlopen(url)
        realurl = urlobj.geturl()

        response = None

        try:
            res = urllib2.urlopen(url)
            response = res.read()
        except urllib2.HTTPError, e:
            self.errorLog(u"HTTPError - %s" % unicode(e))
        except urllib2.URLError, e:
            self.errorLog(u"URLError - %s" % unicode(e))
        except Exception, e:
            if "invalid literal for int() with base 16: ''" in e:
                self.errorLog(u"Obscure bug in Python 2.5.")
            else:
                self.errorLog(u"Exception - %s" % unicode(e))

        return response
