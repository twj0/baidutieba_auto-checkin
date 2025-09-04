# -*- coding:utf-8 -*-
import requests
import hashlib
import time
import copy
import logging
import random
from requests.exceptions import ReadTimeout, ConnectTimeout, RequestException
from json.decoder import JSONDecodeError
import json

# --- 配置区 ---

# 1. 请将你的百度 cookies (JSON格式) 填入下方列表，支持多个账户
#    - 你可以通过浏览器开发者工具获取 cookies
#    - 将整个 JSON 数组粘贴到 ACCOUNTS_JSON 变量中
ACCOUNTS_JSON = """
[
    [
        {
            "name": "BDUSS",
            "value": "在这里填入你的第一个账户的BDUSS"
        }
    ]
]
"""

# 2. Telegram Bot 配置 (可选, 如不使用则留空)
#    - Bot Token: 在 Telegram 搜索 @BotFather, 创建机器人获取
#    - Chat ID:  在 Telegram 搜索 @userinfobot, 获取你的用户ID
TELEGRAM_BOT_TOKEN = "7859768666:AAHvLnDfiOPnoHSeK_eXUjiS4dlprJzZqVo"  # 在这里填入你的 Telegram Bot Token
TELEGRAM_CHAT_ID = "6312417795"   # 在这里填入你的 Telegram Chat ID

# --- 全局常量 ---
LIKIE_URL = "http://c.tieba.baidu.com/c/f/forum/like"
TBS_URL = "http://tieba.baidu.com/dc/common/tbs"
SIGN_URL = "http://c.tieba.baidu.com/c/c/forum/sign"
SIGN_KEY = 'tiebaclient!!!'
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36'

# --- 终端颜色 ---
class Color:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

# --- 日志和会话设置 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
session = requests.Session()
session.headers.update({'User-Agent': USER_AGENT})


def escape_markdown(text: str) -> str:
    """转义 Telegram MarkdownV2 所需的特殊字符。"""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return ''.join(f'\\{char}' if char in escape_chars else char for char in str(text))

def send_telegram_message(message: str):
    """通过 Telegram Bot 发送格式化消息。"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return  # 如果未配置，则静默返回

    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'MarkdownV2'
    }
    try:
        response = requests.post(api_url, json=payload, timeout=15)
        if response.status_code == 200:
            logger.info("Telegram 总结报告发送成功。")
        else:
            logger.error(f"发送 Telegram 消息失败: {response.status_code} - {response.text}")
    except RequestException as e:
        logger.error(f"发送 Telegram 消息时网络异常: {e}")

def encode_data(data: dict) -> dict:
    """计算贴吧客户端API请求的签名。"""
    sorted_items = sorted(data.items())
    s = "".join(f"{k}={v}" for k, v in sorted_items)
    signed_str = s + SIGN_KEY
    sign = hashlib.md5(signed_str.encode("utf-8")).hexdigest().upper()
    data['sign'] = sign
    return data

def get_tbs(cookie_str: str) -> str:
    """获取 tbs (一个用于验证请求的令牌)。"""
    logger.info("正在获取 tbs...")
    headers = {'Cookie': cookie_str}
    try:
        response = session.get(TBS_URL, headers=headers, timeout=10)
        response.raise_for_status()
        tbs_data = response.json()
        if tbs_data.get('is_login') == 0:
            raise ValueError("Cookies 已失效，请重新获取。")
        tbs = tbs_data.get('tbs')
        if not tbs:
            raise ValueError("未能从响应中获取 tbs。")
        logger.info(f"获取 tbs 成功: {tbs}")
        return tbs
    except (RequestException, JSONDecodeError, ValueError) as e:
        logger.error(f"获取 tbs 失败: {e}")
        raise

def get_favorite_forums(bduss: str) -> list:
    """获取所有关注的贴吧列表。"""
    logger.info("正在获取关注的贴吧列表...")
    all_forums = []
    page_no = 1
    while True:
        data = {'BDUSS': bduss, '_client_type': '2', '_client_version': '9.7.8.0', 'page_no': str(page_no), 'page_size': '100'}
        signed_data = encode_data(copy.deepcopy(data))
        try:
            response = session.post(LIKIE_URL, data=signed_data, timeout=10)
            response.raise_for_status()
            res_json = response.json()
            forum_list_data = res_json.get('forum_list', {})
            if forum_list_data:
                if 'gconforum' in forum_list_data: all_forums.extend(forum_list_data['gconforum'])
                if 'non-gconforum' in forum_list_data: all_forums.extend(forum_list_data['non-gconforum'])
            if res_json.get('has_more') == '1':
                logger.info(f"已获取第 {page_no} 页，继续...")
                page_no += 1
                time.sleep(random.uniform(0.5, 1.5))
            else:
                break
        except (RequestException, JSONDecodeError) as e:
            logger.error(f"获取第 {page_no} 页贴吧列表时出错: {e}")
            break
    unique_forums = list({f['id']: f for f in all_forums}.values())
    logger.info(f"获取贴吧列表完成，共 {len(unique_forums)} 个。")
    return unique_forums

def client_sign(bduss: str, tbs: str, forum: dict) -> dict:
    """对单个贴吧进行签到。"""
    forum_name = forum.get("name", "未知")
    data = {'BDUSS': bduss, 'fid': forum.get("id"), 'kw': forum_name, 'tbs': tbs, '_client_type': '2', '_client_version': '12.28.1.0', '_phone_imei': '000000000000000', 'net_type': "1"}
    signed_data = encode_data(copy.deepcopy(data))
    try:
        response = session.post(SIGN_URL, data=signed_data, timeout=15)
        response.raise_for_status()
        res_json = response.json()
        error_code = res_json.get("error_code")
        if error_code == "0":
            user_info = res_json.get("user_info", {})
            return {"status": "success", "message": f"经验+{user_info.get('sign_bonus_point', 'N/A')}，第{user_info.get('user_sign_rank', 'N/A')}个签到"}
        elif error_code == "160002":
            return {"status": "already_signed", "message": "今天已经签到过了"}
        else:
            return {"status": "failed", "message": f"Code:{error_code}, Msg:{res_json.get('error_msg', '未知')}"}
    except (ReadTimeout, ConnectTimeout):
        return {"status": "failed", "message": "请求超时"}
    except (RequestException, JSONDecodeError) as e:
        return {"status": "failed", "message": f"请求或解析异常: {e}"}

def main():
    """主执行函数。"""
    try:
        accounts = json.loads(ACCOUNTS_JSON)
        if not isinstance(accounts, list):
            raise json.JSONDecodeError("JSON is not a list", ACCOUNTS_JSON, 0)
    except json.JSONDecodeError:
        print(f"{Color.RED}错误: ACCOUNTS_JSON 格式无效，请确保它是一个有效的 JSON 数组。{Color.END}")
        return

    if not accounts or ("在这里填入" in ACCOUNTS_JSON and len(accounts[0]) <= 1):
        print(f"{Color.RED}错误: 未在 ACCOUNTS_JSON 中配置有效的账户信息。{Color.END}")
        return

    print(f"{Color.BLUE}检测到 {len(accounts)} 个账户，签到任务开始...{Color.END}\n" + "="*60)

    for i, cookies in enumerate(accounts):
        if not isinstance(cookies, list):
            print(f"{Color.YELLOW}警告: 账户 {i+1} 的数据不是一个列表，跳过。{Color.END}")
            continue

        bduss_cookie = next((c for c in cookies if isinstance(c, dict) and c.get('name') == 'BDUSS'), None)
        if not bduss_cookie or 'value' not in bduss_cookie or "在这里填入" in bduss_cookie['value']:
            print(f"{Color.RED}错误: 账户 {i+1} 未找到有效的 BDUSS cookie，跳过。{Color.END}")
            continue
        
        bduss = bduss_cookie['value']
        cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies if isinstance(c, dict) and 'name' in c and 'value' in c])
        masked_bduss = bduss[:6] + '****' + bduss[-6:]
        
        print(f"\n{Color.BLUE}---> 开始为第 {i+1} 个账户 ({masked_bduss}) 进行签到 <---{Color.END}")
        summary = {"success": 0, "already_signed": 0, "failed": 0, "failed_list": [], "total": 0}
        
        try:
            tbs = get_tbs(cookie_str)
            favorite_forums = get_favorite_forums(bduss)
            total_forums = len(favorite_forums)
            summary['total'] = total_forums
            
            if not favorite_forums:
                print(f"{Color.YELLOW}该账户没有关注任何贴吧，跳过。{Color.END}")
                continue

            print(f"{Color.BLUE}开始签到 {total_forums} 个贴吧...{Color.END}")
            for index, forum in enumerate(favorite_forums):
                forum_name = forum.get("name", "未知")
                result = client_sign(bduss, tbs, forum)
                status, message = result["status"], result["message"]
                
                if status == "success":
                    summary["success"] += 1
                    print(f"[{index+1}/{total_forums}] {Color.GREEN}【{forum_name}】成功: {message}{Color.END}")
                elif status == "already_signed":
                    summary["already_signed"] += 1
                    print(f"[{index+1}/{total_forums}] {Color.YELLOW}【{forum_name}】已签: {message}{Color.END}")
                else:
                    summary["failed"] += 1
                    summary["failed_list"].append(f"{forum_name} ({message})")
                    print(f"[{index+1}/{total_forums}] {Color.RED}【{forum_name}】失败: {message}{Color.END}")
                
                time.sleep(random.uniform(1.0, 2.5))

        except Exception as e:
            print(f"{Color.RED}账户 {masked_bduss} 处理时发生严重错误: {e}{Color.END}")
            send_telegram_message(f"账户 *{escape_markdown(masked_bduss)}* 运行异常\n*错误信息*: `{escape_markdown(str(e))}`")

        # 打印并发送单个账户的总结
        print(f"\n{Color.BLUE}--- 账户 {masked_bduss} 签到总结 ---{Color.END}")
        print(f"  总计贴吧: {summary['total']}")
        print(f"  {Color.GREEN}签到成功: {summary['success']}{Color.END}")
        print(f"  {Color.YELLOW}早已签到: {summary['already_signed']}{Color.END}")
        print(f"  {Color.RED}签到失败: {summary['failed']}{Color.END}")
        
        tg_summary_msg = (
            f"*账户签到总结: {escape_markdown(masked_bduss)}*\n\n"
            f"总计贴吧: `{summary['total']}`\n"
            f"✅ *成功*: `{summary['success']}`\n"
            f"🟡 *已签*: `{summary['already_signed']}`\n"
            f"🔴 *失败*: `{summary['failed']}`\n"
        )
        if summary["failed_list"]:
            print(f"  {Color.RED}失败列表:{Color.END}")
            tg_summary_msg += "\n*失败列表详情*:\n"
            for item in summary["failed_list"]:
                print(f"    - {item}")
                tg_summary_msg += f"\\- `{escape_markdown(item)}`\n"
        print("-" * 45)
        send_telegram_message(tg_summary_msg)

    final_notice = "✅ 所有账户签到任务已完成\\."
    print(f"\n{Color.BLUE}--- 签到任务完成 ---{Color.END}")
    print(f"{final_notice}\n")
    print("="*60)

    send_telegram_message(final_notice)

if __name__ == '__main__':
    main()