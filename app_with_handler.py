# -*- coding: utf-8 -*-

#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

import os
import sys
from argparse import ArgumentParser

from flask import Flask, request, abort
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, StickerMessage,
    StickerSendMessage, PostbackEvent, PostbackTemplateAction, Postback
)

from ac_control import ACControl

app = Flask(__name__)

# get channel_secret and channel_access_token from your environment variable
my_user_id = os.getenv('MY_USER_ID', None)
channel_secret = os.getenv('LINE_CHANNEL_SECRET', None)
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)
if my_user_id is None:
    print('Specify MY_USER_ID as environment variable.')
    sys.exit(1)
if channel_secret is None:
    print('Specify LINE_CHANNEL_SECRET as environment variable.')
    sys.exit(1)
if channel_access_token is None:
    print('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
    sys.exit(1)

line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)

@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@app.route("/ifttt", methods=['POST'])
def callback_ifttt():
    body = request.get_data(as_text=True)
    app.logger.info("IFTTT test")
    app.logger.info("Request body: " + body)
    ac_cont = ACControl(line_bot_api, my_user_id)
    if(body=="IFTTT_AC_ON"):
        ac_cont.push_turn_on_confirm()
    elif(body=="IFTTT_AC_OFF"):
        ac_cont.push_turn_off_confirm()
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def message_text(event):
    if(event.type != "message"):
        # return
        pass

    # 入力されたテキストを取り出す
    input_text = event.message.text
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=event.message.text+"ですね。")
    )

@handler.add(MessageEvent, message=StickerMessage)
def message_sticker(event):
    name = line_bot_api.get_profile(event.source.user_id).display_name
    line_bot_api.reply_message(
        event.reply_token,
        [TextSendMessage(text="なるほど、スタンプですか。考えましたね、"+name+"さん。"),StickerSendMessage(package_id=4,sticker_id=296)]
    )

@handler.add(PostbackEvent)
def reply_to_postback(event):
    messages = []
    ac_cont = ACControl()    
    if event.postback.data == "ac_on_approval":
        messages.append(TextSendMessage(text="承知いたしました。つけておきます。"))
        ac_cont.set_turn_on_flg()
    elif event.postback.data == "ac_on_disapproval":
        messages.append(TextSendMessage(text="そうですか。そのままにしておきます。"))
        ac_cont.set_no_action_flg()

    if event.postback.data == "ac_off_approval":
        messages.append(TextSendMessage(text="承知いたしました。消しておきます。"))
        ac_cont.set_turn_off_flg()
    elif event.postback.data == "ac_off_disapproval":
        messages.append(TextSendMessage(text="そうですか。そのままつけておきます。"))
        ac_cont.set_no_action_flg()
    line_bot_api.reply_message(event.reply_token, messages)


if __name__ == "__main__":
    arg_parser = ArgumentParser(
        usage='Usage: python ' + __file__ + ' [--port <port>] [--help]'
    )
    arg_parser.add_argument('-p', '--port', default=8000, help='port')
    arg_parser.add_argument('-d', '--debug', default=False, help='debug')
    options = arg_parser.parse_args()

    # app.run(debug=options.debug, port=options.port)
    app.run(debug=True, port=options.port)