# main.py
import os
import requests
import hashlib
import time
import copy
import logging
import random
from requests.exceptions import RequestException
from json.decoder import JSONDecodeError

# --- 日志和颜色设置 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Color:
    RED, GREEN, YELLOW, BLUE, END = '\033[91m', '\033[92m', '\033[93m', '\033[94m', '\033[0m'

# --- 全局常量 ---
LIKIE_URL = "http://c.tieba.baidu.com/c/f/forum/like"
TBS_URL = "http://tieba.baidu.com/dc/common/tbs"
SIGN_URL = "http://c.tieba.baidu.com/c/c/forum/sign"
SIGN_KEY = 'tiebaclient!!!'
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36'
session = requests.Session()
session.headers.update({'User-Agent': USER_AGENT})

# --- 核心函数 ---

def send_telegram_message(message: str, token: str, chat_id: str):
    if not token or not chat_id:
        return
    api_url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {'chat_id': chat_id, 'text': message, 'parse_mode': 'MarkdownV2'}
    try:
        response = requests.post(api_url, json=payload, timeout=15)
        if response.status_code == 200:
            logger.info("Telegram 总结报告发送成功。")
        else:
            logger.error(f"发送 Telegram 消息失败: {response.status_code} - {response.text}")
    except RequestException as e:
        logger.error(f"发送 Telegram 消息时网络异常: {e}")

def escape_markdown(text: str) -> str:
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return ''.join(f'\\{char}' if char in escape_chars else char for char in str(text))

def encode_data(data: dict) -> dict:
    sorted_items = sorted(data.items())
    s = "".join(f"{k}={v}" for k, v in sorted_items)
    signed_str = s + SIGN_KEY
    data['sign'] = hashlib.md5(signed_str.encode("utf-8")).hexdigest().upper()
    return data

def get_tbs(bduss: str) -> str:
    logger.info("正在获取 tbs...")
    response = session.get(TBS_URL, headers={'Cookie': f'BDUSS={bduss}'}, timeout=10)
    response.raise_for_status()
    tbs_data = response.json()
    if tbs_data.get('is_login') == 0: raise ValueError("BDUSS 已失效，请重新获取。")
    tbs = tbs_data.get('tbs')
    if not tbs: raise ValueError("未能从响应中获取 tbs。")
    logger.info("获取 tbs 成功。")
    return tbs

def get_favorite_forums(bduss: str) -> list:
    logger.info("正在获取关注的贴吧列表...")
    collected_forums = []
    page = 1
    while True:
        params = {
            'BDUSS': bduss, '_client_type': '2', '_client_id': 'wappc_1534235498291_488',
            '_client_version': '9.7.8.0', '_phone_imei': '000000000000000', 'from': '1008621y',
            'page_no': str(page), 'page_size': '200', 'model': 'MI+5', 'net_type': '1',
            'timestamp': str(int(time.time())), 'vcode_tag': '11',
        }
        signed_params = encode_data(copy.deepcopy(params))
        try:
            response = session.post(LIKIE_URL, data=signed_params, timeout=10)
            data = response.json()
            forum_list = data.get('forum_list', {})
            if forum_list:
                if 'gconforum' in forum_list: collected_forums.extend(forum_list['gconforum'])
                if 'non_gconforum' in forum_list: collected_forums.extend(forum_list['non-gconforum'])
            if data.get('has_more') != '1': break
            page += 1
            time.sleep(random.uniform(0.5, 1.0))
        except (RequestException, JSONDecodeError) as e:
            logger.error(f"获取第 {page} 页贴吧时出错: {e}")
            break
            
    unique_forums = list({f['id']: f for f in collected_forums}.values())
    logger.info(f"获取贴吧列表完成，共 {len(unique_forums)} 个。")
    return unique_forums

def client_sign(bduss: str, tbs: str, forum: dict) -> dict:
    data = {
        'BDUSS': bduss, 'fid': forum.get("id"), 'kw': forum.get("name"), 'tbs': tbs,
        '_client_type': '2', '_client_version': '9.7.8.0', '_phone_imei': '000000000000000',
        'model': 'MI+5', 'net_type': "1", 'timestamp': str(int(time.time())),
    }
    signed_data = encode_data(copy.deepcopy(data))
    try:
        res = session.post(SIGN_URL, data=signed_data, timeout=15).json()
        if res.get("error_code") == "0":
            info = res.get("user_info", {})
            return {"status": "success", "message": f"经验+{info.get('sign_bonus_point', 'N/A')}，第{info.get('user_sign_rank', 'N/A')}个"}
        elif res.get("error_code") == "160002":
            return {"status": "already_signed", "message": "今天已经签到过了"}
        return {"status": "failed", "message": f"Code:{res.get('error_code')}, Msg:{res.get('error_msg', '未知')}"}
    except (RequestException, JSONDecodeError) as e:
        return {"status": "failed", "message": f"请求或解析异常: {e}"}

def main():
    # 从环境变量中安全地读取机密信息
    bduss_string = os.environ.get("BDUSS_SECRET")
    tg_token = os.environ.get("TG_TOKEN")
    tg_chat_id = os.environ.get("TG_CHAT_ID")
    
    if not bduss_string:
        logger.error("未在 GitHub Secrets 中配置 BDUSS_SECRET。")
        raise ValueError("BDUSS_SECRET is not set")
        
    valid_bduss_list = [b.strip() for b in bduss_string.split('#') if b.strip()]
    logger.info(f"检测到 {len(valid_bduss_list)} 个账户，签到任务开始...")

    for i, bduss in enumerate(valid_bduss_list):
        masked_bduss = bduss[:6] + '****' + bduss[-6:]
        summary = {"success": 0, "already_signed": 0, "failed": 0, "failed_list": [], "total": 0}
        
        try:
            tbs = get_tbs(bduss)
            forums = get_favorite_forums(bduss)
            summary['total'] = len(forums)

            for idx, forum in enumerate(forums):
                res = client_sign(bduss, tbs, forum)
                summary[res['status']] += 1
                logger.info(f"[{idx+1}/{summary['total']}] 【{forum.get('name')}】: {res['message']}")
                if res['status'] == 'failed': summary['failed_list'].append(f"{forum.get('name')} ({res['message']})")
                time.sleep(random.uniform(1.0, 2.5))
        except Exception as e:
            logger.error(f"账户 {masked_bduss} 处理时发生严重错误: {e}")
            send_telegram_message(f"*账户签到异常: {escape_markdown(masked_bduss)}*\n*错误信息*: `{escape_markdown(str(e))}`", tg_token, tg_chat_id)
            continue

        # 准备并发送总结报告
        tg_msg = (f"*账户签到总结: {escape_markdown(masked_bduss)}*\n\n"
                  f"总计贴吧: `{summary['total']}`\n✅ *成功*: `{summary['success']}`\n"
                  f"🟡 *已签*: `{summary['already_signed']}`\n🔴 *失败*: `{summary['failed']}`\n")
        if summary['failed_list']:
            tg_msg += "\n*失败列表详情*:\n" + "\n".join(f"\\- `{escape_markdown(item)}`" for item in summary['failed_list'])
        send_telegram_message(tg_msg, tg_token, tg_chat_id)

    logger.info("所有账户签到任务已完成！")
    send_telegram_message("✅ 所有账户签到任务已完成\\.", tg_token, tg_chat_id)

if __name__ == '__main__':
    main()