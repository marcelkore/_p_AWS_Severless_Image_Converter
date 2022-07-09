import os
import slack_notifications as slack

slack.ACCESS_TOKEN =

channel_name = "aws-da-image-converter"
username = 's3Bot'
text = "Image converted to thumbnail"

slack.send_notify(channel_name, username, text)
