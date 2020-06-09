# coding: utf-8

import os
import sys
import requests
import urllib.request, urllib.parse, urllib.error
import json
import psycopg2

from linebot.models import (
    CarouselTemplate, CarouselColumn, URITemplateAction, TemplateSendMessage, TextSendMessage
)

class RestaurantInfo():
    def __init__(self):
        self.name = "No Title"
        self.shop_img = ""
        self.shop_url = ""
        self.text_pr = "No information"
        self.opentime = "Open :  - Close : "
        self.holiday = "-"
    
    def show(self):
        print("Name   : {0}".format(self.name))
        print("PR     : {0}".format(self.text_pr))
        print("Open   : {0}".format(self.opentime))
        print("Holiday: {0}".format(self.holiday))
        print("URL    : {0}".format(self.shop_url))

class Gurunavi(object):
    """
    ぐるなびAPIからフリーワード検索で店舗情報を返すクラス
    """
    ROOT_URL = "https://api.gnavi.co.jp/RestSearchAPI/v3/"
    GURUNAVI_APIKEY = os.getenv('GURUNAVI_APIKEY', None)
    DBURL = os.getenv("DATABASE_URL", None)
    MAX_SHOW = 5
    MAX_TEXT = 60

    def __init__(self):
        pass

    def _build_URL_freeword_search(self, freeword):
        # URLに続けて入れるパラメータを組立
        query = {
            "keyid": Gurunavi.GURUNAVI_APIKEY,
            "freeword": freeword
        }
        # URL生成
        url = Gurunavi.ROOT_URL
        url += "?{0}".format(urllib.parse.urlencode(query))
        return url
    
    def _get_json_data(self, url):
        # API実行
        try:
            result = urllib.request.urlopen(url).read()
        except ValueError:
            self._sendText("APIアクセスに失敗しました。")
            return None

        # 取得したJson文字列をDictionary化
        data = json.loads(result)

        # エラーの場合
        if "error" in data:
            if "message" in data:
                self._sendText("エラーメッセージがあります。")
            else:
                self._sendText("データ取得に失敗しました。")
            return None
        return data

    def _parse_restaurant_data(self, data):
        # ヒット件数取得
        total_hit_count = None
        if "total_hit_count" in data:
            total_hit_count = data["total_hit_count"]
        
        # レストランデータがなかったら終了
        if not "rest" in data:
            print("レストランデータが見つからなかったため終了します。")
            sys.exit()
        
        # レストランデータ取得
        num_of_shop = 0
        rest_info_list = []
        for rest in data["rest"]:
            rest_info = RestaurantInfo()
            

            # 店舗名の取得
            if "name" in rest and self._is_str(rest["name"]):
                rest_info.name = rest["name"]
            
            # 画像アドレスの取得(カルーセル取得用)
            if "image_url" in rest:
                image_url = rest["image_url"]
                if "shop_image1" in image_url and self._is_str(image_url["shop_image1"]):
                    rest_info.shop_img = image_url["shop_image1"]

            # 店舗のURL
            if "url" in rest and self._is_str(rest["url"]):
                rest_info.shop_url = rest["url"]
            
            # PR文章
            if "pr" in rest: 
                pr = rest["pr"]
                if "pr_short" in pr and self._is_str(pr["pr_short"]):
                    if pr["pr_short"] != "":
                        text_pr = pr["pr_short"]
                        if len(pr["pr_short"]) > Gurunavi.MAX_TEXT:
                            text_pr = text_pr[0:Gurunavi.MAX_TEXT]
                    else:
                        text_pr = "No Information"
                rest_info.text_pr = text_pr
            
            if "opentime" in rest:
                rest_info.opentime = rest["opentime"]
            
            if "holiday" in rest:
                rest_info.holiday = rest["holiday"]

            rest_info_list.append(rest_info)

            num_of_shop += 1
            if(num_of_shop >= Gurunavi.MAX_SHOW):
                break
        
        return rest_info_list

    
    def _is_str(self, data=None):
        if isinstance(data, str):
            return True
        else:
            return False

    def is_serving(self, userid):
        url = os.getenv("DATABASE_URL")
        connection = psycopg2.connect(url)
        cur = connection.cursor()
        sql = "SELECT serving FROM LinebotState WHERE uid = (%s)"
        data = (userid, )
        cur.execute(sql, data)
        service = cur.fetchall()[0][0]
        cur.close()
        connection.close()
        if service == "Gurunavi":
            return True
        else:
            return False
    
    def _update_service(self, userid, sql):
        # pycopg2はformatでSQL文を生成できないため、
        # sql文は引数として受け付けて暫定的に対処
        url = os.getenv("DATABASE_URL")
        connection = psycopg2.connect(url)
        cur = connection.cursor()
        data = (userid, )
        cur.execute(sql, data)
        connection.commit()
        cur.close()
        connection.close()

    def start_service(self, userid):
        # DatabaseのServingをDefaultに戻す
        sql = "UPDATE LineBotState SET serving='Gurunavi' WHERE uid = (%s)"
        self._update_service(userid, sql)

    def finish_service(self, userid):
        # DatabaseのServingをDefaultに戻す
        sql = "UPDATE LineBotState SET serving='Default' WHERE uid = (%s)"
        self._update_service(userid, sql)

    def reply_shop_list(self, bot, event):
        input_text = event.message.text
        carousel_message = self._create_carousel_template(input_text)
        send_messages = [carousel_message]
        bot.reply_message(
            event.reply_token,
            send_messages
        )

    def reply_start_message(self, bot, event):
        text_message = TextSendMessage(text="どう検索しますか?")
        send_messages = [text_message]        
        bot.reply_message(
            event.reply_token,
            send_messages
        )

    def _create_carousel_template(self, freeword):
        url = self._build_URL_freeword_search(freeword)
        data = self._get_json_data(url)
        rest_info_list = self._parse_restaurant_data(data)

        columns = []
        for rest_info in rest_info_list:
            carousel = CarouselColumn(
                thumbnail_image_url=rest_info.shop_img,
                title=rest_info.name,
                # title = "aa",
                text=rest_info.text_pr,
                # text="bb",
                actions=[
                        URITemplateAction(
                            label='URL',
                            uri=rest_info.shop_url
                        )
                ]
                )
            columns.append(carousel)

        carousel_template_message = TemplateSendMessage(
            alt_text='ぐるなび検索結果',
            template=CarouselTemplate(columns=columns)
        )
        return carousel_template_message