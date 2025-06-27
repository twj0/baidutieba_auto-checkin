import requests
import hashlib
import time
import copy
import logging
import random
import os
from requests.exceptions import ReadTimeout, ConnectTimeout, RequestException
from json.decoder import JSONDecodeError

# --- Configuration from Environment Variables ---
BDUSS_LIST = os.environ.get("BDUSS_LIST", "").split()
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# --- Global Constants ---
LIKIE_URL = "http://c.tieba.baidu.com/c/f/forum/like"
TBS_URL = "http://tieba.baidu.com/dc/common/tbs"
SIGN_URL = "http://c.tieba.baidu.com/c/c/forum/sign"
SIGN_KEY = 'tiebaclient!!!'
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36'

# --- Terminal Colors ---
class Color:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

# --- Logging and Session Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
session = requests.Session()
session.headers.update({'User-Agent': USER_AGENT})


def escape_markdown(text: str) -> str:
    """Escapes special characters for Telegram MarkdownV2."""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return ''.join(f'\\{char}' if char in escape_chars else char for char in str(text))

def send_telegram_message(message: str):
    """Sends a formatted message via Telegram Bot."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return

    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'MarkdownV2'
    }
    try:
        response = requests.post(api_url, json=payload, timeout=15)
        if response.status_code == 200:
            logger.info("Telegram summary report sent successfully.")
        else:
            logger.error(f"Failed to send Telegram message: {response.status_code} - {response.text}")
    except RequestException as e:
        logger.error(f"Network error while sending Telegram message: {e}")

def encode_data(data: dict) -> dict:
    """Calculates the signature for Tieba client API requests."""
    sorted_items = sorted(data.items())
    s = "".join(f"{k}={v}" for k, v in sorted_items)
    signed_str = s + SIGN_KEY
    sign = hashlib.md5(signed_str.encode("utf-8")).hexdigest().upper()
    data['sign'] = sign
    return data

def get_tbs(bduss: str) -> str:
    """Gets the tbs token for request verification."""
    logger.info("Getting tbs...")
    headers = {'Cookie': f'BDUSS={bduss}'}
    try:
        response = session.get(TBS_URL, headers=headers, timeout=10)
        response.raise_for_status()
        tbs_data = response.json()
        if tbs_data.get('is_login') == 0:
            raise ValueError("BDUSS is invalid. Please update it.")
        tbs = tbs_data.get('tbs')
        if not tbs:
            raise ValueError("Failed to get tbs from the response.")
        logger.info(f"Successfully got tbs: {tbs}")
        return tbs
    except (RequestException, JSONDecodeError, ValueError) as e:
        logger.error(f"Failed to get tbs: {e}")
        raise

def get_favorite_forums(bduss: str) -> list:
    """Gets the list of all followed forums."""
    logger.info("Getting the list of followed forums...")
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
                logger.info(f"Got page {page_no}, continuing...")
                page_no += 1
                time.sleep(random.uniform(0.5, 1.5))
            else:
                break
        except (RequestException, JSONDecodeError) as e:
            logger.error(f"Error getting page {page_no} of the forum list: {e}")
            break
    unique_forums = list({f['id']: f for f in all_forums}.values())
    logger.info(f"Finished getting the forum list, a total of {len(unique_forums)} forums.")
    return unique_forums

def client_sign(bduss: str, tbs: str, forum: dict) -> dict:
    """Signs in to a single forum."""
    forum_name = forum.get("name", "Unknown")
    data = {'BDUSS': bduss, 'fid': forum.get("id"), 'kw': forum_name, 'tbs': tbs, '_client_type': '2', '_client_version': '12.28.1.0', '_phone_imei': '000000000000000', 'net_type': "1"}
    signed_data = encode_data(copy.deepcopy(data))
    try:
        response = session.post(SIGN_URL, data=signed_data, timeout=15)
        response.raise_for_status()
        res_json = response.json()
        error_code = res_json.get("error_code")
        if error_code == "0":
            user_info = res_json.get("user_info", {})
            return {"status": "success", "message": f"Experience +{user_info.get('sign_bonus_point', 'N/A')}, signed in as number {user_info.get('user_sign_rank', 'N/A')}"}
        elif error_code == "160002":
            return {"status": "already_signed", "message": "Already signed in today"}
        else:
            return {"status": "failed", "message": f"Code:{error_code}, Msg:{res_json.get('error_msg', 'Unknown')}"}
    except (ReadTimeout, ConnectTimeout):
        return {"status": "failed", "message": "Request timed out"}
    except (RequestException, JSONDecodeError) as e:
        return {"status": "failed", "message": f"Request or parsing exception: {e}"}

def main():
    """Main execution function."""
    if not BDUSS_LIST:
        print(f"{Color.RED}Error: No valid BDUSS configured in the BDUSS_LIST secret.{Color.END}")
        return

    print(f"{Color.BLUE}Detected {len(BDUSS_LIST)} accounts, starting sign-in task...{Color.END}\n" + "="*60)

    for i, bduss in enumerate(BDUSS_LIST):
        masked_bduss = bduss[:6] + '****' + bduss[-6:]
        print(f"\n{Color.BLUE}---> Starting sign-in for account {i+1} ({masked_bduss}) <---{Color.END}")
        summary = {"success": 0, "already_signed": 0, "failed": 0, "failed_list": [], "total": 0}
        
        try:
            tbs = get_tbs(bduss)
            favorite_forums = get_favorite_forums(bduss)
            total_forums = len(favorite_forums)
            summary['total'] = total_forums
            
            if not favorite_forums:
                print(f"{Color.YELLOW}This account does not follow any forums, skipping.{Color.END}")
                continue

            print(f"{Color.BLUE}Starting to sign in to {total_forums} forums...{Color.END}")
            for index, forum in enumerate(favorite_forums):
                forum_name = forum.get("name", "Unknown")
                result = client_sign(bduss, tbs, forum)
                status, message = result["status"], result["message"]
                
                if status == "success":
                    summary["success"] += 1
                    print(f"[{index+1}/{total_forums}] {Color.GREEN}【{forum_name}】Success: {message}{Color.END}")
                elif status == "already_signed":
                    summary["already_signed"] += 1
                    print(f"[{index+1}/{total_forums}] {Color.YELLOW}【{forum_name}】Already signed in: {message}{Color.END}")
                else:
                    summary["failed"] += 1
                    summary["failed_list"].append(f"{forum_name} ({message})")
                    print(f"[{index+1}/{total_forums}] {Color.RED}【{forum_name}】Failed: {message}{Color.END}")
                
                time.sleep(random.uniform(1.0, 2.5))

        except Exception as e:
            print(f"{Color.RED}A serious error occurred while processing account {masked_bduss}: {e}{Color.END}")
            send_telegram_message(f"Account *{escape_markdown(masked_bduss)}* encountered an exception\n*Error message*: `{escape_markdown(str(e))}`")

        # Print and send a summary for the individual account
        print(f"\n{Color.BLUE}--- Account {masked_bduss} Sign-in Summary ---{Color.END}")
        print(f"  Total forums: {summary['total']}")
        print(f"  {Color.GREEN}Successful sign-ins: {summary['success']}{Color.END}")
        print(f"  {Color.YELLOW}Already signed in: {summary['already_signed']}{Color.END}")
        print(f"  {Color.RED}Failed sign-ins: {summary['failed']}{Color.END}")
        
        # Prepare the Telegram message
        tg_summary_msg = (
            f"*Account Sign-in Summary: {escape_markdown(masked_bduss)}*\n\n"
            f"Total forums: `{summary['total']}`\n"
            f"✅ *Success*: `{summary['success']}`\n"
            f"🟡 *Already signed in*: `{summary['already_signed']}`\n"
            f"🔴 *Failed*: `{summary['failed']}`\n"
        )
        if summary["failed_list"]:
            print(f"  {Color.RED}List of failures:{Color.END}")
            tg_summary_msg += "\n*Details of failures*:\n"
            for item in summary["failed_list"]:
                print(f"    - {item}")
                tg_summary_msg += f"\\- `{escape_markdown(item)}`\n"
        print("-" * 45)
        send_telegram_message(tg_summary_msg)

    final_notice = "✅ All account sign-in tasks have been completed\\."
    print(f"\n{Color.BLUE}--- Sign-in Task Completed ---{Color.END}")
    print(f"{final_notice}\n")
    print("="*60)

    # Send the final notification
    send_telegram_message(final_notice)

if __name__ == '__main__':
    main()