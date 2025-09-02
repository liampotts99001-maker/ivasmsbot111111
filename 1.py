import requests
from bs4 import BeautifulSoup
import time
import schedule
from telegram import Bot
from telegram.error import TelegramError
import logging
import re
import os
from datetime import datetime, timedelta
import json
import asyncio
import sys
import io

# এনকোডিং সমস্যার সমাধান
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, 'utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, 'utf-8')

# লগিং কনফিগারেশন
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("otp_bot.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# কনফিগারেশন
IVASMS_USERNAME = "t90auupr@nqmo.com"
IVASMS_PASSWORD = "t90auupr@nqmo.com"
TELEGRAM_BOT_TOKEN = "7993238689:AAH8VwOre8jwOPZvMtzSfyeXob84mNxILKU"
TELEGRAM_CHANNEL_ID = -1003026928669
CHECK_INTERVAL = 10

# গ্লোবাল ভেরিয়েবল
csrf_token = ""
processed_message_ids = set()
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Linux; Android 13; Infinix X6525B Build/TP1A.220624.014) AppleWebKit/537.36 (KHTML, like GeetCode) Chrome/139.0.7258.158 Mobile Safari/537.36',
    'X-Requested-With': 'XMLHttpRequest',
    'Accept': 'text/html, */*; q=0.01',
    'Accept-Language': 'en-US,en;q=0.9,bn-BD;q=0.8,bn;q=0.7',
    'Origin': 'https://www.ivasms.com',
    'Referer': 'https://www.ivasms.com/portal/sms/received',
    'sec-ch-ua': '"Not;A=Brand";v="99", "Android WebView";v="139", "Chromium";v="139"',
    'sec-ch-ua-mobile': '?1',
    'sec-ch-ua-platform': '"Android"',
    'sec-fetch-site': 'same-origin',
    'sec-fetch-mode': 'cors',
    'sec-fetch-dest': 'empty'
})

# সাহায্যকারী ফাংশন
def escape_html(text):
    """HTML entities এ কনভার্ট করে"""
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('#', '&#35;')

def get_service_name(message: str) -> str:
    message_lower = message.lower()
    services = {
        'facebook': 'Facebook', 'google': 'Google', 'g-': 'Google', 'gmail': 'Gmail',
        'paypal': 'PayPal', 'bkash': 'bKash', 'nagad': 'Nagad', 'whatsapp': 'WhatsApp',
        'telegram': 'Telegram', 'amazon': 'Amazon', 'uber': 'Uber', 'twitter': 'Twitter',
        'x-com': 'Twitter (X.com)', 'microsoft': 'Microsoft', 'binance': 'Binance',
        'verified': 'Verified', 'instagram': 'Instagram', 'tiktok': 'TikTok',
        'apple': 'Apple', 'discord': 'Discord', 'signal': 'Signal', 'linkedin': 'LinkedIn',
        'riot games': 'Riot Games', 'steam': 'Steam', 'epic games': 'Epic Games',
        'gcash': 'GCash', 'paymaya': 'PayMaya', 'grab': 'Grab', 'shopee': 'Shopee',
        'aliexpress': 'AliExpress', 'alibaba': 'Alibaba', 'snapchat': 'Snapchat',
        'viber': 'Viber', 'wechat': 'WeChat', 'line': 'LINE', 'kakao': 'KakaoTalk',
        'imo': 'IMO', 'alibaba': 'Alibaba', 'tencent': 'Tencent', 'vk': 'VK',
        'okru': 'Odnoklassniki', 'mail.ru': 'Mail.ru', 'yahoo': 'Yahoo', 'outlook': 'Outlook',
        'hotm': 'Hotmail', 'live.com': 'Live.com', 'yandex': 'Yandex', 'netflix': 'Netflix',
        'spotify': 'Spotify', 'pinterest': 'Pinterest', 'reddit': 'Reddit', 'ebay': 'eBay',
        'flipkart': 'Flipkart', 'myntra': 'Myntra', 'zomato': 'Zomato', 'swiggy': 'Swiggy',
        'pubg': 'PUBG Mobile', 'free fire': 'Free Fire', 'call of duty': 'Call of Duty Mobile'
    }
    for keyword, name in services.items():
        if keyword in message_lower: return name
    return 'Unknown Service'

def get_country_info(number: str) -> tuple:
    country_codes = {
        '963': ('Syria', '🇸🇾'), '216': ('Tunisia', '🇹🇳'), '261': ('Madagascar', '🇲🇬'), '58': ('Venezuela', '🇻🇪'),
        '880': ('Bangladesh', '🇧🇩'), '1': ('USA/Canada', '🇺🇸'), '44': ('UK', '🇬🇧'), '91': ('India', '🇮🇳'),
        '86': ('China', '🇨🇳'), '33': ('France', '🇫🇷'), '49': ('Germany', '🇩🇪'), '225': ('Ivory Coast', '🇨🇮'),
        '229': ('Benin', '🇧🇯'), '93': ('Afghanistan', '🇦🇫'), '62': ('Indonesia', '🇮🇩'), '63': ('Philippines', '🇵🇭'),
        '60': ('Malaysia', '🇲🇾'), '66': ('Thailand', '🇹🇭'), '84': ('Vietnam', '🇻🇳'), '65': ('Singapore', '🇸🇬'),
        '852': ('Hong Kong', '🇭🇰'), '853': ('Macau', '🇲🇴'), '855': ('Cambodia', '🇰🇭'), '856': ('Laos', '🇱🇦'),
        '95': ('Myanmar', '🇲🇲'), '971': ('UAE', '🇦🇪'), '966': ('Saudi Arabia', '🇸🇦'), '965': ('Kuwait', '🇰🇼'),
        '974': ('Qatar', '🇶🇦'), '973': ('Bahrain', '🇧🇭'), '968': ('Oman', '🇴🇲'), '962': ('Jordan', '🇯🇴'),
        '20': ('Egypt', '🇪🇬'), '212': ('Morocco', '🇲🇦'), '234': ('Nigeria', '🇳🇬'), '254': ('Kenya', '🇰🇪'),
        '27': ('South Africa', '🇿🇦'), '34': ('Spain', '🇪🇸'), '39': ('Italy', '🇮🇹'), '7': ('Russia', '🇷🇺'),
        '380': ('Ukraine', '🇺🇦'), '52': ('Mexico', '🇲🇽'), '55': ('Brazil', '🇧🇷'), '54': ('Argentina', '🇦🇷'),
        '51': ('Peru', '🇵🇪'), '57': ('Colombia', '🇨🇴'), '56': ('Chile', '🇨🇱'), '61': ('Australia', '🇦🇺'),
        '64': ('New Zealand', '🇳🇿'), '351': ('Portugal', '🇵🇹'), '353': ('Ireland', '🇮🇪'), '357': ('Cyprus', '🇨🇾'),
        '358': ('Finland', '🇫🇮'), '359': ('Bulgaria', '🇧🇬'), '370': ('Lithuania', '🇱🇹'), '371': ('Latvia', '🇱🇻'),
        '372': ('Estonia', '🇪🇪'), '374': ('Armenia', '🇦🇲'), '375': ('Belarus', '🇧🇾'), '381': ('Serbia', '🇷🇸'),
        '385': ('Croatia', '🇭🇷'), '386': ('Slovenia', '🇸🇮'), '387': ('Bosnia & Herzegovina', '🇧🇦'),
        '40': ('Romania', '🇷🇴'), '41': ('Switzerland', '🇨🇭'), '420': ('Czech Republic', '🇨🇿'), '421': ('Slovakia', '🇸🇰'),
        '423': ('Liechtenstein', '🇱🇮'), '43': ('Austria', '🇦🇹'), '45': ('Denmark', '🇩🇰'), '46': ('Sweden', '🇸🇪'),
        '47': ('Norway', '🇳🇴'), '48': ('Poland', '🇵🇱'), '506': ('Costa Rica', '🇨🇷'), '507': ('Panama', '🇵🇦'),
        '509': ('Haiti', '🇭🇹'), '591': ('Bolivia', '🇧🇴'), '593': ('Ecuador', '🇪🇨'), '595': ('Paraguay', '🇵🇾'),
        '598': ('Uruguay', '🇺🇾'), '673': ('Brunei', '🇧🇳'), '674': ('Nauru', '🇳🇷'), '675': ('Papua New Guinea', '🇵🇬'),
        '676': ('Tonga', '🇹🇴'), '677': ('Solomon Islands', '🇸🇧'), '678': ('Vanuatu', '🇻🇺'), '679': ('Fiji', '🇫🇯'),
        '680': ('Palau', '🇵🇼'), '681': ('Wallis & Futuna', '🇼🇫'), '682': ('Cook Islands', '🇨🇰'), '683': ('Niue', '🇳🇺'),
        '685': ('Samoa', '🇼🇸'), '686': ('Kiribati', '🇰🇮'), '687': ('New Caledonia', '🇳🇨'), '688': ('Tuvalu', '🇹🇻'),
        '689': ('French Polynesia', '🇵🇫'), '690': ('Tokelau', '🇹🇰'), '691': ('Micronesia', '🇫🇲'), '692': ('Marshall Islands', '🇲🇭'),
        '850': ('North Korea', '🇰🇵'), '82': ('South Korea', '🇰🇷'), '886': ('Taiwan', '🇹🇼'), '970': ('Palestine', '🇵🇸'), 
        '972': ('Israel', '🇮🇱'), '976': ('Mongolia', '🇲🇳'), '977': ('Nepal', '🇳🇵'), '992': ('Tajikistan', '🇹🇯'),
        '993': ('Turkmenistan', '🇹🇲'), '994': ('Azerbaijan', '🇦🇿'), '995': ('Georgia', '🇬🇪'), '996': ('Kyrgyzstan', '🇰🇬'),
        '998': ('Uzbekistan', '🇺🇿'), '213': ('Algeria', '🇩🇿'), '218': ('Libya', '🇱🇾'), '220': ('Gambia', '🇬🇲'),
        '221': ('Senegal', '🇸🇳'), '222': ('Mauritania', '🇲🇷'), '223': ('Mali', '🇲🇱'), '224': ('Guinea', '🇬🇳'),
        '226': ('Burkina Faso', '🇧🇫'), '227': ('Niger', '🇳🇪'), '228': ('Togo', '🇹🇬'), '230': ('Mauritius', '🇲🇺'),
        '231': ('Liberia', '🇱🇷'), '232': ('Sierra Leone', '🇸🇱'), '233': ('Ghana', '🇬🇭'), '235': ('Chad', '🇹🇩'),
        '236': ('Central African Republic', '🇨🇫'), '237': ('Cameroon', '🇨🇲'), '238': ('Cape Verde', '🇨🇻'),
        '239': ('Sao Tome & Principe', '🇸🇹'), '240': ('Equatorial Guinea', '🇬🇶'), '241': ('Gabon', '🇬🇦'),
        '242': ('Congo (Brazzaville)', '🇨🇬'), '243': ('Congo (Kinshasa)', '🇨🇩'), '244': ('Angola', '🇦🇴'),
        '245': ('Guinea-Bissau', '🇬🇼'), '246': ('Diego Garcia', '🇮🇴'), '247': ('Ascension Island', '🇦🇨'),
        '248': ('Seychelles', '🇸🇨'), '249': ('Sudan', '🇸🇩'), '250': ('Rwanda', '🇷🇼'), '251': ('Ethiopia', '🇪🇹'),
        '252': ('Somalia', '🇸🇴'), '253': ('Djibouti', '🇩🇯'), '255': ('Tanzania', '🇹🇿'), '256': ('Uganda', '🇺🇬'),
        '257': ('Burundi', '🇧🇮'), '258': ('Mozambique', '🇲🇿'), '260': ('Zambia', '🇿🇲'), '262': ('Reunion/Mayotte', '🇷🇪'),
        '263': ('Zimbabwe', '🇿🇼'), '264': ('Namibia', '🇳🇦'), '265': ('Malawi', '🇲🇼'), '266': ('Lesotho', '🇱🇸'),
        '267': ('Botswana', '🇧🇼'), '268': ('Eswatini', '🇸🇿'), '269': ('Comoros', '🇰🇲')
    }
    clean_number = re.sub(r'\D', '', number)
    for code, info in country_codes.items():
        if clean_number.startswith(code): return info
    return ('Unknown', '🏳️')

def save_processed_messages():
    try:
        with open('processed_messages.json', 'w', encoding='utf-8') as f: 
            json.dump(list(processed_message_ids), f, ensure_ascii=False, indent=2)
    except Exception as e: 
        logger.error(f"প্রসেস করা মেসেজ আইডি সেভ করতে সমস্যা: {e}")

def load_processed_messages():
    global processed_message_ids
    try:
        if os.path.exists('processed_messages.json'):
            with open('processed_messages.json', 'r', encoding='utf-8') as f:
                processed_message_ids = set(json.load(f)[-500:])
                logger.info(f"{len(processed_message_ids)}টি পুরনো মেসেজ আইডি লোড করা হয়েছে।")
    except Exception as e: 
        logger.error(f"প্রসেস করা মেসেজ লোড করতে সমস্যা: {e}")

# IVASMS সেশন ম্যানেজমেন্ট
def ivasms_auto_login():
    global csrf_token
    try:
        logger.info("লগইন পেজ থেকে CSRF টোকেন সংগ্রহ করা হচ্ছে...")
        response = session.get('https://www.ivasms.com/login', timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')
        token_input = soup.find('input', {'name': '_token'})
        if not token_input:
            logger.error("লগইন পেজে CSRF টোকেন খুঁজে পাওয়া যায়নি।")
            return False
        csrf_token = token_input.get('value')
        login_data = {'_token': csrf_token, 'email': IVASMS_USERNAME, 'password': IVASMS_PASSWORD}
        logger.info("লগইন করার চেষ্টা করা হচ্ছে...")
        login_response = session.post('https://www.ivasms.com/login', data=login_data, timeout=30, allow_redirects=True)
        if login_response.status_code == 200 and '/portal' in login_response.url:
            logger.info("সফলভাবে লগইন করা হয়েছে।")
            return True
        else:
            logger.error(f"লগইন ব্যর্থ। স্ট্যাটাস: {login_response.status_code}, URL: {login_response.url}")
            return False
    except Exception as e:
        logger.error(f"লগইন প্রক্রিয়ায় ত্রুটি: {e}", exc_info=True)
        return False

# SMS স্ক্র্যাপিং - উন্নত OTP detection সহ
def get_sms_messages():
    global csrf_token
    if 'ivas_sms_session' not in session.cookies:
        if not ivasms_auto_login(): 
            return []
    
    all_new_messages = []
    end_date = datetime.now()
    start_date = end_date - timedelta(days=1)
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    
    try:
        # প্রথমে মূল পেজ লোড করুন CSRF টোকেন এর জন্য
        base_url = 'https://www.ivasms.com/portal/sms/received'
        response = session.get(base_url, timeout=30)
        
        if '/login' in str(response.url):
            logger.warning("সেশন শেষ, পুনরায় লগইন করা হচ্ছে...")
            if not ivasms_auto_login(): 
                return []
            response = session.get(base_url, timeout=30)
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # নতুন CSRF টোকেন সংগ্রহ করুন
        token_input = soup.find('input', {'name': '_token'})
        if not token_input:
            logger.error("CSRF টোকেন পাওয়া যায়নি")
            return []
        
        csrf_token = token_input.get('value')
        logger.info(f"নতুন CSRF টোকেন: {csrf_token}")

        # ধাপ ১: রেঞ্জ/গ্রুপ গুলো সংগ্রহ করুন
        groups_url = 'https://www.ivasms.com/portal/sms/received/getsms'
        groups_payload = {
            'start': start_date_str,
            'end': end_date_str,
            '_token': csrf_token
        }
        
        groups_response = session.post(groups_url, data=groups_payload, timeout=30)
        groups_soup = BeautifulSoup(groups_response.text, 'html.parser')
        
        # রেঞ্জ/গ্রুপ গুলো খুঁজুন
        range_elements = groups_soup.select('div.card-body div.col-sm-4')
        ranges = [div.get_text(strip=True) for div in range_elements if div.get_text(strip=True)]
        
        if not ranges:
            logger.info("কোনো রেঞ্জ/গ্রুপ পাওয়া যায়নি")
            return []
        
        logger.info(f"পাওয়া গেছে {len(ranges)}টি রেঞ্জ: {ranges}")
        
        # ধাপ ২: প্রতিটি রেঞ্জ/গ্রুপ এর জন্য নম্বর গুলো সংগ্রহ করুন
        for range_name in ranges:
            logger.info(f"প্রসেস করছি রেঞ্জ: {range_name}")
            
            # রেঞ্জের নম্বর গুলো সংগ্রহ করুন
            number_list_url = 'https://www.ivasms.com/portal/sms/received/getsms/number'
            number_payload = {
                'start': start_date_str,
                'end': end_date_str,
                '_token': csrf_token,
                'range': range_name
            }
            
            number_list_response = session.post(number_list_url, data=number_payload, timeout=30)
            number_soup = BeautifulSoup(number_list_response.text, 'html.parser')
            
            # নম্বর গুলো খুঁজুন
            number_divs = number_soup.select('div.Number div.card')
            
            if not number_divs:
                logger.info(f"রেঞ্জ {range_name} এ কোনো নম্বর পাওয়া যায়নি")
                continue
            
            logger.info(f"রেঞ্জ {range_name} এ {len(number_divs)}টি নম্বর পাওয়া গেছে")
            
            # ধাপ ৩: প্রতিটি নম্বরের জন্য SMS গুলো সংগ্রহ করুন
            for num_div in number_divs:
                try:
                    # নম্বর খুঁজুন - onclick attribute থেকে নম্বর extract করুন
                    onclick_element = num_div.find('div', {'onclick': True})
                    if not onclick_element:
                        continue
                    
                    # onclick attribute থেকে নম্বর extract করুন
                    onclick_text = onclick_element.get('onclick', '')
                    number_match = re.search(r"getDetialsNumber.*?\(['\"](.*?)['\"]", onclick_text)
                    if not number_match:
                        continue
                    
                    number = number_match.group(1)
                    if not number.isdigit():
                        continue
                    
                    logger.info(f"প্রসেস করছি নম্বর: {number}")
                    
                    # এই নম্বরের SMS গুলো সংগ্রহ করুন
                    sms_url = 'https://www.ivasms.com/portal/sms/received/getsms/number/sms'
                    sms_payload = {
                        'start': start_date_str,
                        'end': end_date_str,
                        '_token': csrf_token,
                        'Range': range_name,
                        'Number': number
                    }
                    
                    sms_response = session.post(sms_url, data=sms_payload, timeout=30)
                    
                    # SMS কার্ড গুলো খুঁজুন
                    sms_soup = BeautifulSoup(sms_response.text, 'html.parser')
                    sms_cards = sms_soup.select('div.card.card-body')
                    
                    for card in sms_cards:
                        try:
                            # মেসেজ টেক্সট খুঁজুন
                            message_element = card.select_one('div.col-9.col-sm-6 p.mb-0.pb-0')
                            if not message_element:
                                continue
                                
                            message_text = message_element.get_text(strip=True)
                            logger.info(f"মেসেজ টেক্সট: {message_text}")
                            
                            otp_code = None
                            
                            # --- উন্নত OTP ডিটেকশন লজিক শুরু ---
                            # লক্ষ্য: 1 থেকে 11 ডিজিটের যেকোনো সংখ্যা যা বিভিন্ন সেপারেটর দ্বারা বিভক্ত হতে পারে।
                            # এবং এমন সংখ্যা যা মেসেজের মধ্যে স্বাধীনভাবে বিদ্যমান।
                            
                            # প্রথমত, মেসেজ থেকে সমস্ত সংখ্যা এবং সম্ভাব্য সেপারেটর সহ স্ট্রিং বের করা।
                            # প্যাটার্ন: এক বা একাধিক সংখ্যা (\d+), তারপরে শূন্য বা এক বা একাধিক স্পেস/হাইফেন/স্ল্যাশ ([\s\-/]*)
                            # এই প্যাটার্নটি বার বার রিপিট হতে পারে।
                            
                            # সব সম্ভাব্য সংখ্যা সিকোয়েন্সগুলো খুঁজে বের করুন (যেমন, 123 456, 123-456, 123/456, 123456789)
                            # আমরা এমন সব সাবস্ট্রিং খুঁজছি যা ডিজিট, স্পেস, হাইফেন বা স্ল্যাশ নিয়ে গঠিত।
                            potential_otps_raw = re.findall(r'(\d+[\s\-/]?)+', message_text)
                            
                            extracted_digits = []
                            for p_otp_raw in potential_otps_raw:
                                # প্রতিটি সম্ভাব্য OTP স্ট্রিং থেকে শুধুমাত্র ডিজিটগুলো বের করে যোগ করুন
                                digits_only = re.sub(r'[\s\-/]', '', p_otp_raw)
                                if 1 <= len(digits_only) <= 11: # 1 থেকে 11 সংখ্যার OTP
                                    extracted_digits.append(digits_only)
                            
                            # সবচেয়ে বড় ডিজিট সিকোয়েন্সটি OTP হিসেবে নির্বাচন করুন, যদি একাধিক থাকে
                            if extracted_digits:
                                otp_code = max(extracted_digits, key=len) # দীর্ঘতম OTP নির্বাচন
                                # যদি একাধিক দীর্ঘতম OTP থাকে, তাহলে প্রথমটি নেওয়া হবে।
                                logger.info(f"উন্নত ডিটেকশন থেকে OTP পাওয়া গেছে: {otp_code}")
                            else:
                                # যদি উপরের পদ্ধতি কাজ না করে, তবে একেবারে সহজভাবে একটানা 1-11 ডিজিট খুঁজুন
                                digit_match = re.search(r'\b(\d{1,11})\b', message_text)
                                if digit_match:
                                    otp_code = digit_match.group(1)
                                    logger.info(f"সাধারণ একটানা ডিজিট থেকে OTP পাওয়া গেছে: {otp_code}")
                            
                            # --- উন্নত OTP ডিটেকশন লজিক শেষ ---
                            
                            if otp_code:
                                message_id = f"{number}-{message_text}-{otp_code}"
                                
                                if message_id not in processed_message_ids:
                                    all_new_messages.append({
                                        'number': number, 
                                        'message': message_text, 
                                        'otp': otp_code
                                    })
                                    processed_message_ids.add(message_id)
                                    logger.info(f"নতুন OTP পাওয়া গেছে: {number} - {otp_code}")
                                else:
                                    logger.info(f"এই OTP '{otp_code}' ইতিমধ্যে প্রসেস করা হয়েছে।")
                            else:
                                # যদি কোনো OTP খুঁজে না পাওয়া যায়, তবে ডিফল্ট হিসেবে "No OTP Found" সেট করুন
                                otp_code = "No OTP Found" 
                                message_id = f"{number}-{message_text}-{otp_code}" # OTP না পেলেও মেসেজ আইডি তৈরি করুন
                                
                                if message_id not in processed_message_ids:
                                    all_new_messages.append({
                                        'number': number, 
                                        'message': message_text, 
                                        'otp': otp_code
                                    })
                                    processed_message_ids.add(message_id)
                                    logger.info(f"কোন OTP পাওয়া যায়নি, ডিফল্ট সেট করা হয়েছে।")
                                else:
                                    logger.info(f"এই মেসেজটি '{message_text}' ইতিমধ্যে প্রসেস করা হয়েছে (OTP ছাড়া)।")
                            
                        except Exception as e:
                            logger.error(f"কার্ড পার্স error: {e}")
                            continue
                
                except Exception as e:
                    logger.error(f"নম্বর প্রসেস error: {e}")
                    continue
        
        if all_new_messages:
            save_processed_messages()
            logger.info(f"মোট {len(all_new_messages)}টি নতুন মেসেজ (OTP সহ বা ছাড়া) পাওয়া গেছে")
        else:
            logger.info("কোনো নতুন মেসেজ পাওয়া যায়নি")
            
        return all_new_messages
        
    except Exception as e:
        logger.error(f"SMS মেসেজ পাওয়ার সময় error: {e}", exc_info=True)
        return []

# টেলিগ্রাম কমিউনিকেশন
async def send_to_telegram_async(bot_token, channel_id, message):
    try:
        bot = Bot(token=bot_token)
        await bot.send_message(chat_id=channel_id, text=message, parse_mode='HTML', disable_web_page_preview=True)
        return True
    except TelegramError as e:
        logger.error(f"টেলিগ্রামে মেসেজ পাঠানোর সময় TelegramError: {e}")
        return False
    except Exception as e:
        logger.error(f"টেলিগ্রামে মেসেজ পাঠানোর সময় একটি অপ্রত্যাশিত ত্রুটি: {e}")
        return False

# মূল কার্যকারিতা
def check_and_forward_otp():
    logger.info("নতুন OTP এর জন্য চেক করা হচ্ছে...")
    
    messages = get_sms_messages()
    
    if not messages:
        logger.info("কোনো নতুন মেসেজ পাওয়া যায়নি।") # পরিবর্তন করা হয়েছে
        return
    
    logger.info(f"{len(messages)}টি নতুন মেসেজ পাওয়া গেছে (OTP সহ বা ছাড়া)।") # পরিবর্তন করা হয়েছে
    
    for msg in messages:
        service_name = get_service_name(msg['message'])
        country_name, country_flag = get_country_info(msg['number'])
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        escaped_message = escape_html(msg['message'])
        
        # OTP না পেলে "No OTP Found" দেখানো হবে
        otp_display = msg['otp'] if msg['otp'] != "No OTP Found" else "<code>No OTP Found</code>"
        
        telegram_message = f"""✨ <b>🔷TechFlowBangla Otp Bot🔷</b> ✨

⏰ <b>Time:</b> {current_time}
📞 <b>Number:</b> <code>{msg['number']}</code>
🌐 <b>Country:</b> {country_flag} {country_name}
🔧 <b>Service:</b> {service_name}

🔑 <b>OTP Code:</b> {otp_display}

<code>{escaped_message}</code>"""

        print("\n--- Sending to Telegram ---")
        print(telegram_message)
        print("---------------------------\n")

        if asyncio.run(send_to_telegram_async(TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID, telegram_message)):
            logger.info(f"মেসেজ (OTP: {msg['otp']}) টেলিগ্রামে সফলভাবে পাঠানো হয়েছে।") # পরিবর্তন করা হয়েছে
        else:
            logger.error(f"মেসেজ (OTP: {msg['otp']}) পাঠানো ব্যর্থ হয়েছে।") # পরিবর্তন করা হয়েছে
        time.sleep(1)

# বট চালনা এবং শিডিউলিং
def main():
    logger.info("=== OTP ফরওয়ার্ডিং বট শুরু হচ্ছে ===")
    load_processed_messages()
    if not ivasms_auto_login():
        logger.critical("IVASMS লগইন ব্যর্থ। বট চালু করা সম্ভব হচ্ছে না।")
        return
    
    asyncio.run(send_to_telegram_async(TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID, "🚀 <b>বট সফলভাবে চালু হয়েছে এবং এখন OTP-এর জন্য পর্যবেক্ষণ করছে!</b>"))
    logger.info(f"বট সফলভাবে শুরু হয়েছে। প্রতি {CHECK_INTERVAL} সেকেন্ডে চেক করা হবে।")
    check_and_forward_otp()
    schedule.every(CHECK_INTERVAL).seconds.do(check_and_forward_otp)
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("বট ব্যবহারকারী দ্বারা বন্ধ করা হয়েছে。")
    except Exception as e:
        logger.critical(f"একটি মারাত্মক ত্রুটির কারণে বট ক্র্যাশ করেছে: {e}", exc_info=True)
    finally:
        save_processed_messages()
        logger.info("প্রসেস করা মেসেজ আইডিগুলো সফলভাবে সেভ করা হয়েছে। বট বন্ধ হচ্ছে。")
        asyncio.run(send_to_telegram_async(TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID, "🔴 <b>বট বন্ধ হয়ে গেছে!</b>"))

if __name__ == '__main__':
    main()