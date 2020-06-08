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
import datetime
import psycopg2
import logging

from flask import Flask, request, abort
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, StickerMessage,
    StickerSendMessage, PostbackEvent, PostbackTemplateAction, Postback,
    FollowEvent
)
from ac_control import ACControl


app = Flask(__name__)

# https://teratail.com/questions/159332
# ログを標準出力に出力する
app.logger.addHandler(logging.StreamHandler(sys.stdout))
# （レベル設定は適宜行ってください）
# app.logger.setLevel(logging.ERROR)
app.logger.setLevel(logging.INFO)

# get channel_secret and channel_access_token from your environment variable
my_user_id = os.getenv('LINE_USER_ID', None)
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
    """
    IFTTTからのWebHookを受け取り、bodyの中身に応じて確認メッセージを投稿する
    """
    body = request.get_data(as_text=True)
    app.logger.info("callback_ifttt() called.")
    app.logger.info("Request body: " + body)
    ac_cont = ACControl(line_bot_api, my_user_id)
    if body == "IFTTT_AC_ON":
        ac_cont.push_turn_on_confirm()
    elif body == "IFTTT_AC_OFF":
        ac_cont.push_turn_off_confirm()
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def message_text(event):
    """
    ユーザーからのテキストメッセージを受け取り、加工して返答する
    """
    if(event.type != "message"):
        return
    # gurunavi = Gurunavi()

    # if gurunavi.is_serving(userid=event.source.user_id):
    #     gurunavi.reply(searchword=event.message.text)

    # # 入力されたテキストを取り出す
    # input_text = event.message.text
    # if input_text == "食事":
    #     gurunavi.start_service()
    # else:
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=event.message.text+"ですね。")
    )
        

@handler.add(MessageEvent, message=StickerMessage)
def message_sticker(event):
    """
    ユーザーからのスタンプメッセージを受け取り、返答する
    """
    name = line_bot_api.get_profile(event.source.user_id).display_name
    line_bot_api.reply_message(
        event.reply_token,
        [TextSendMessage(text="なるほど、スタンプですか。考えましたね、"+name+"さん。"),StickerSendMessage(package_id=4, sticker_id=296)]
    )

@handler.add(PostbackEvent)
def reply_to_postback(event):
    """
    ユーザーからのボタン押下によるPostbackに対して、返答する
    """
    messages = []
    ac_cont = ACControl(line_bot_api, my_user_id)
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

@handler.add(FollowEvent)
def check_user_information(event):
    app.logger.info("New user followed Yoshina.")
    uid = event.source.user_id
    uname = line_bot_api.get_profile(uid).display_name
    timestamp_ms = event.timestamp
    timestamp = convert_timestamp(timestamp_ms)

    connection = get_database_connection()
    if not user_exists(connection, uid):
        append_new_user_to_database(connection, uid, uname, timestamp)
        app.logger.info("New user was appended.")
    connection.close()

def convert_timestamp(milliseconds):
    seconds = milliseconds / 1000.0
    return datetime.datetime.fromtimestamp(seconds).strftime('%Y-%m-%d %H:%M:%S')

def get_database_connection():
    url = os.getenv("DATABASE_URL")
    return psycopg2.connect(url)

def append_new_user_to_database(connection, userid, username, timestamp):
    cur = connection.cursor()
    sql = "INSERT INTO LineBotState (uid, uname, serving, last_message_time) VALUES(%s, %s, %s, %s)"
    data = (userid, username, "Default", timestamp)
    cur.execute(sql, data)
    cur.commit()
    cur.close()


def user_exists(connection, userid):
    cur = connection.cursor()
    cur.execute("SELECT * FROM LinebotState WHERE uid = (%s)", (userid,))
    user_info = cur.fetchall()
    cur.close()
    if len(user_info):
        return True
    else:
        return False

if __name__ == "__main__":
    arg_parser = ArgumentParser(
        usage='Usage: python ' + __file__ + ' [--port <port>] [--help]'
    )
    arg_parser.add_argument('-p', '--port', default=8000, help='port')
    arg_parser.add_argument('-d', '--debug', default=False, help='debug')
    options = arg_parser.parse_args()

    # app.run(debug=options.debug, port=options.port)
    app.run(debug=True, port=options.port)