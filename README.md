## Summary
This plugin extends [Indigo](http://www.indigodomo.com) allowing it to send messages to [Slack](https://slack.com), optionally with attachments and adds a separate file upload notification.  This is a re-write of [Slack-Notify](https://github.com/achterberg/slack-notify) by [achterberg](https://github.com/achterberg) which hasn't seen any activity since February 2015.

Some notable changes:
* Switched to using WebAPI (via [python-slackclient](http://slackapi.github.io/python-slackclient/)) instead of webhooks
* Channel and user lookups are moved to Plugin startup, instead of at each dialog screen. A menu option has been added to refresh this data as needed.
* Added option for conditional channel mentions (@channel) when posting a message.
* Added separate action for file uploads
* Recursive variable substitution (instead of just replacing the first instance)


## Requirements
* [Indigo 7](http://www.indigodomo.com/index.html) or later (pro version only)
* A Slack Team is required. Register for an account at [Slack](https://slack.com) and set up a team
* Optional: Create a Slack channel to be used for Slack Notify (recommended), or use one of the defaults
* Requires [Slack SDK for Python](http://slackapi.github.io/python-slackclient/) 

## Installation
* Install slackclient via pip
```sudo pip install slackclient```

* Download the ZIP file from GitHub (look over there --->)
* Unzip the file if it doesn't automatically unzip
* On the computer running Indigo, double-click the file "Slack.indigoPlugin"
* Follow the Indigo dialog and enable the plugin
* The plugin should be visible in the Plugins drop-down menu as "Slack Notify"
* Trouble?: Indigo help for the [installation process](http://wiki.indigodomo.com/doku.php?id=indigo_7_documentation:getting_started)

## Configuration
###Configure Plugin
In the menu: `Indigo 7/Plugins/Slack Notify/Configure`...
    
####Slack Token
  * Go [here](https://api.slack.com/web)
  * Under Authentication there should be a team Token
  * Enter the above in the Slack Token field
  
####User ID
  * This identifies the user Indigo will use to post messages
  * Go to the following link, replacing the part after = with the slack token above
  * https://slack.com/api/users.list?token=replacewithSlackToken
  * Look for the series of letter/numbers after the line beginning with: "id":
  * Enter the above in the User ID field
  
###Configure Notifications
####Slack Notify Action
  * The action will show under `Type: Notification Actions` under `Actions` as `Slack Notify`.
  * Once added to a TRIGGER, SCHEDULE or ACTION GROUPS, click on Edit Action Settings...
  * Select either a channel or a user to receive a Direct Message
  * Enter the message text in the Text field, following the formatting hints listed below the field. Formatting for Indigo and Slack is outlined.
  * Select whether you want to add a channel mention (@channel) to the posted message.
  * Select whether you want to only add a mention if a variable meets certain conditions.  The `Condition` field can either be a literal string, or a python list/dict object.
  * Optional: Enter a username to be posted as. If blank, the plugin will use your username and post as a bot.
  * Optional: Enter a name of an [emoji](http://www.emoji-cheat-sheet.com) to be posted with the message. Or use [Custom Emoji](https://my.slack.com/customize/emoji). If nothing is entered the default is a Slack emoji.
  * Optional: Enter the URL to a publically sharable URL for an image file that will be displayed inside a message attachment. Slack currently supports the following formats: GIF, JPEG, PNG, and BMP.
  * Optional: Enter the file path to a local file to upload to Slack.
####

## Back-end info
* The plugin will attempt to get your user information from Slack to fill in the channels available in your team and to retrieve your username. Turning on debugging mode will expose your Slack user credentials (including ID, username, user icon, user color, real name, status and email address) in the Indigo log.

## Dependencies
* Indigo plugins (the IOM and SDK) use Python 2.7
* See Requirements

## Plugin ID
To programmatically restart the plugin, the Plugin ID is: `com.rafael-ortiz.indigoplugin.slack-notify`

## Uninstall
Remove “/Library/Application Support/Perceptive Automation/Indigo 7/Plugins/Slack.indigoPlugin” (or check in the Disabled Plugins folder if disabled) and restart the Indigo Server
