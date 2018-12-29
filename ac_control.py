# coding: utf-8

import textwrap
import datetime
import urllib.request, urllib.parse, urllib.error

# linebot用
from linebot.models import (
    TextSendMessage, TemplateSendMessage, ConfirmTemplate, PostbackTemplateAction
)

import thingspeak

class ACState(object):
    NO_ACTION = 0
    TOBE_TURN_ON = 1
    TOBE_TURN_OFF = 2

class ACControl(object):
    ac_state_file = "ac_state.json"

    def __init__(self, line_bot_api, my_line_user_id):
        self.line_bot_api = line_bot_api
        self.my_line_user_id = my_line_user_id
        self.ac_state = {"state": ACState.NO_ACTION}
    
    def push_turn_on_confirm(self):
        welcome_back_message = TextSendMessage("もうすぐ家ですね。おかえりなさい。")
        environment_information = self.get_environment()
        information_message = TextSendMessage(environment_information)
        confirm_template_message = TemplateSendMessage(
            alt_text='エアコンつけておきますか?',
            template=ConfirmTemplate(
                text='エアコンつけておきますか?',
                actions=[
                    PostbackTemplateAction(
                        label='承認',
                        text='承認',
                        data='ac_on_approval'
                    ), 
                    PostbackTemplateAction(
                        label='否認',
                        text='否認',
                        data='ac_on_disapproval'
                    )
                ]
            )
        )
        send_messages = [welcome_back_message, information_message, confirm_template_message]
        self.line_bot_api.push_message(self.my_line_user_id, send_messages)
        return True

    def push_turn_off_confirm(self):
        see_you_message = TextSendMessage("でかけるのですか?行ってらっしゃいませ。")
        environment_information = self.get_environment()
        information_message = TextSendMessage(environment_information)
        confirm_template_message = TemplateSendMessage(
            alt_text='エアコン消しておきますか?',
            template=ConfirmTemplate(
                text='エアコン消しておきますか?',
                actions=[
                    PostbackTemplateAction(
                        label='承認',
                        text='承認',
                        data='ac_off_approval'
                    ), 
                    PostbackTemplateAction(
                        label='否認',
                        text='否認',
                        data='ac_off_disapproval'
                    )
                ]
            )
        )
        send_messages = [see_you_message, information_message, confirm_template_message]
        self.line_bot_api.push_message(self.my_line_user_id, send_messages)
        return True
    
    def set_no_action_flg(self):
        self.ac_state["state"] = ACState.NO_ACTION
        thingspeak.write_current_state(self.ac_state.get("state"))

    def set_turn_on_flg(self):
        self.ac_state["state"] = ACState.TOBE_TURN_ON
        thingspeak.write_current_state(self.ac_state.get("state"))

    def set_turn_off_flg(self):
        self.ac_state["state"] = ACState.TOBE_TURN_OFF
        thingspeak.write_current_state(self.ac_state.get("state"))

    def get_environment(self):
        sensor_output_text = """\
        温度: {temperature:.2f}度
        湿度: {humidity:.2f}%
        気圧: {pressure:.2f}hPa
        ({time}時点での情報)
        """
        fields = thingspeak.get_environment_field()
        time_obj = datetime.datetime.strptime(fields.get("time")[:-6], "%Y-%m-%dT%H:%M:%S")
        time_outtext = "{year}/{month}/{date} {hour}:{minute}:{second}".format(
            year=time_obj.year,
            month=time_obj.month,
            date=time_obj.day,
            hour=time_obj.hour,
            minute=time_obj.minute,
            second=time_obj.second
        )
        sensor_output_text = sensor_output_text.format(
            temperature=float(fields.get("temperature")),
            humidity=float(fields.get("humidity")),
            pressure=float(fields.get("pressure")),
            time=time_outtext
            )
        sensor_output_text = textwrap.dedent(sensor_output_text)
        return sensor_output_text
