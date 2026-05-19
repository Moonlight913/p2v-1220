# -*- coding:utf-8 -*-

import websocket
import hashlib
import base64
import hmac
import json
from urllib.parse import urlencode
import ssl
from wsgiref.handlers import format_date_time
from datetime import datetime
from time import mktime
import _thread as thread
import os
import glob
import time

from config import (
    XUNFEI_APP_ID,
    XUNFEI_API_KEY,
    XUNFEI_API_SECRET,
    SCRIPT_DIR,
    VOICE_DIR
)


# =========================
# 官方 Ws_Param（不要改结构）
# =========================
class Ws_Param(object):

    def __init__(self, APPID, APIKey, APISecret, Text):

        self.APPID = APPID
        self.APIKey = APIKey
        self.APISecret = APISecret
        self.Text = Text

        # 公共参数
        self.CommonArgs = {
            "app_id": self.APPID,
            "status": 2
        }

        # 业务参数
        self.BusinessArgs = {
            "tts": {

                "vcn": "x6_lingyuyan_pro",

                "volume": 50,

                "rhy": 0,

                "speed": 50,

                "pitch": 50,

                "bgs": 0,

                "reg": 0,

                "rdn": 0,

                "audio": {

                    "encoding": "lame",

                    "sample_rate": 24000,

                    "channels": 1,

                    "bit_depth": 16,

                    "frame_size": 0
                }
            }
        }

        # 文本数据
        self.Data = {
            "text": {

                "encoding": "utf8",

                "compress": "raw",

                "format": "plain",

                "status": 2,

                "seq": 0,

                "text": str(
                    base64.b64encode(
                        self.Text.encode('utf-8')
                    ),
                    "UTF8"
                )
            }
        }


class AssembleHeaderException(Exception):

    def __init__(self, msg):

        self.message = msg


class Url:

    def __init__(self, host, path, schema):

        self.host = host
        self.path = path
        self.schema = schema


def parse_url(request_url):

    stidx = request_url.index("://")

    host = request_url[stidx + 3:]

    schema = request_url[:stidx + 3]

    edidx = host.index("/")

    if edidx <= 0:

        raise AssembleHeaderException(
            "invalid request url:" + request_url
        )

    path = host[edidx:]

    host = host[:edidx]

    return Url(host, path, schema)


def assemble_ws_auth_url(
        request_url,
        method="GET",
        api_key="",
        api_secret=""
):

    u = parse_url(request_url)

    host = u.host

    path = u.path

    now = datetime.now()

    date = format_date_time(
        mktime(now.timetuple())
    )

    signature_origin = (
        f"host: {host}\n"
        f"date: {date}\n"
        f"{method} {path} HTTP/1.1"
    )

    signature_sha = hmac.new(
        api_secret.encode('utf-8'),
        signature_origin.encode('utf-8'),
        digestmod=hashlib.sha256
    ).digest()

    signature_sha = base64.b64encode(
        signature_sha
    ).decode(encoding='utf-8')

    authorization_origin = (
        f'api_key="{api_key}", '
        f'algorithm="hmac-sha256", '
        f'headers="host date request-line", '
        f'signature="{signature_sha}"'
    )

    authorization = base64.b64encode(
        authorization_origin.encode('utf-8')
    ).decode(encoding='utf-8')

    values = {
        "host": host,
        "date": date,
        "authorization": authorization
    }

    return request_url + "?" + urlencode(values)


class XunfeiTTSSynthesizer:
    """讯飞TTS合成器"""

    def __init__(
            self,
            app_id,
            api_key,
            api_secret,
            output_dir
    ):

        self.app_id = app_id

        self.api_key = api_key

        self.api_secret = api_secret

        self.output_dir = output_dir

        # 使用你的官方私有接口
        self.ws_url = (
            'wss://cbm01.cn-huabei-1.xf-yun.com/'
            'v1/private/mcd9m97e6'
        )

        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)

    def _on_message(self, ws, message, audio_data, is_success):
        """WebSocket消息回调"""
        try:
            # JSON字符串 -> Python字典
            message = json.loads(message)

            # 获取返回码
            code = message["header"]["code"]

            # 收到音频数据
            if "payload" in message and "audio" in message["payload"]:

                # 获取base64音频
                audio_base64 = message["payload"]["audio"]["audio"]

                # base64解码
                audio_chunk = base64.b64decode(audio_base64)

                # 保存音频片段
                audio_data.append(audio_chunk)

                # 获取状态
                status = message["payload"]["audio"]["status"]

                # status=2 表示最后一帧
                if status == 2:
                    ws.close()

            # 错误处理
            if code != 0:
                error_msg = message["header"].get("message", "未知错误")
                print(f"错误代码: {code}, 消息: {error_msg}")
                is_success[0] = False
            else:
                is_success[0] = True

        except Exception as e:
            print(f"解析消息异常: {e}")
            is_success[0] = False

    def _on_error(self, ws, error):

        print("WebSocket错误:")

        print(error)

    def _on_close(
            self,
            ws,
            close_status_code,
            close_msg
    ):

        pass

    def _on_open(self, ws, request_data):

        def run(*args):

            ws.send(request_data)

        # 官方demo写法
        thread.start_new_thread(run, ())

    def synthesize_text(
            self,
            text,
            output_filename,
            voice="x6_lingyuyan_pro"
    ):

        # 使用官方 Ws_Param
        ws_param = Ws_Param(

            APPID=self.app_id,

            APIKey=self.api_key,

            APISecret=self.api_secret,

            Text=text
        )

        # 官方结构
        request_data = json.dumps({

            "header": ws_param.CommonArgs,

            "parameter": ws_param.BusinessArgs,

            "payload": ws_param.Data
        })

        # 生成鉴权URL
        auth_url = assemble_ws_auth_url(

            self.ws_url,

            "GET",

            self.api_key,

            self.api_secret
        )

        # 音频缓存
        audio_data = []

        # 是否成功
        is_success = [False]

        # 创建连接
        ws = websocket.WebSocketApp(

            auth_url,

            on_message=lambda ws, msg:
            self._on_message(
                ws,
                msg,
                audio_data,
                is_success
            ),

            on_error=self._on_error,

            on_close=self._on_close
        )

        ws.on_open = lambda ws: self._on_open(
            ws,
            request_data
        )

        # 启动 websocket
        websocket.enableTrace(False)

        ws.run_forever(
            sslopt={"cert_reqs": ssl.CERT_NONE}
        )

        # 保存音频
        if audio_data and is_success[0]:

            output_path = os.path.join(
                self.output_dir,
                output_filename
            )

            with open(output_path, 'wb') as f:

                for chunk in audio_data:

                    f.write(chunk)

            print(f"音频文件已保存: {output_path}")

            return True

        else:

            print(f"合成失败: {output_filename}")

            return False


def synthesize_voices(
        voice="x6_lingyuyan_pro"
):

    """
    合成 SCRIPT_DIR 下所有txt文件
    """

    try:

        synthesizer = XunfeiTTSSynthesizer(

            app_id=XUNFEI_APP_ID,

            api_key=XUNFEI_API_KEY,

            api_secret=XUNFEI_API_SECRET,

            output_dir=VOICE_DIR
        )

        # 检查目录
        if not os.path.exists(SCRIPT_DIR):

            print(
                f"错误: 脚本目录不存在 "
                f"- {SCRIPT_DIR}"
            )

            return False

        # 查找txt文件
        txt_files = sorted(

            glob.glob(
                os.path.join(
                    SCRIPT_DIR,
                    "page_*.txt"
                )
            ),

            key=lambda x:
            int(
                os.path.basename(x)
                .split('_')[1]
                .split('.')[0]
            )
        )

        if not txt_files:

            print(
                f"警告: 在 "
                f"{SCRIPT_DIR} "
                f"目录下未找到 "
                f"page_*.txt 文件"
            )

            return False

        print(f"找到 {len(txt_files)} 个文本文件")

        all_success = True

        # 逐个合成
        for txt_file in txt_files:

            try:

                with open(
                        txt_file,
                        'r',
                        encoding='utf-8'
                ) as f:

                    text_content = f.read().strip()

            except Exception as e:

                print(
                    f"读取文件失败 "
                    f"{txt_file}: {e}"
                )

                all_success = False

                continue

            if not text_content:

                print(
                    f"警告: "
                    f"{txt_file} "
                    f"内容为空，跳过"
                )

                continue

            base_name = (
                os.path.basename(txt_file)
                .replace('.txt', '.mp3')
            )

            print(
                f"正在合成: "
                f"{base_name} "
                f"(长度:"
                f"{len(text_content)} 字符)"
            )

            # 开始合成
            success = synthesizer.synthesize_text(

                text=text_content,

                output_filename=base_name,

                voice=voice
            )

            if not success:

                all_success = False

                print(f"合成失败: {base_name}")

            else:

                print(f"合成成功: {base_name}")

            # 防止请求过快
            time.sleep(1)

        return all_success

    except Exception as e:

        print(f"合成过程中发生异常: {e}")

        return False