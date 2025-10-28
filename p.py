import os
import time
import json
import random
import requests
from datetime import datetime
from itertools import cycle
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Bersihkan terminal
os.system('cls' if os.name == 'nt' else 'clear')

# Tampilan hacker style
terminal_width = os.get_terminal_size().columns
banner = f"""
{'+' + '-' * (terminal_width - 2) + '+'}
|{'WELCOME TO HACKER BOT SYSTEM'.center(terminal_width - 2)}|
|{'=' * (terminal_width - 2)}|
|{'DISCORD AUTO-REPLY BOT - NEON MODE V2'.center(terminal_width - 2)}|
{'+' + '-' * (terminal_width - 2) + '+'}
"""

print(f"\033[91m{banner}\033[0m")

# Session dengan retry strategy
def create_session():
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "POST", "DELETE"]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

session = create_session()

def load_tokens(file_path):
    try:
        with open(file_path, 'r') as file:
            tokens = [
                line.strip() for line in file
                if line.strip() and not line.strip().startswith(('#', '//'))
            ]
            if not tokens:
                raise ValueError("File kosong atau hanya berisi komentar.")
            return tokens
    except FileNotFoundError:
        print(f"âš ï¸ File {file_path} tidak ditemukan.")
        return []

discord_tokens = load_tokens('token.txt')
google_api_keys = load_tokens('api.txt')

if not discord_tokens:
    print("âŒ Tidak ada token Discord yang valid!")
    exit(1)

discord_token_cycle = cycle(discord_tokens)
google_api_key_cycle = cycle(google_api_keys) if google_api_keys else None

last_message_id = None
bot_user_id = None
last_ai_response = None
rate_limit_reset = {}

def log_message(message):
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}")

def get_random_message():
    try:
        with open('pesan.txt', 'r', encoding='utf-8') as file:
            lines = [line.strip() for line in file.readlines() if line.strip()]
            return random.choice(lines) if lines else "Tidak ada pesan yang tersedia."
    except FileNotFoundError:
        return "File pesan.txt tidak ditemukan."

def generate_reply(prompt, use_google_ai=True, use_file_reply=False, language="id"):
    global last_ai_response

    if use_file_reply:
        return {"candidates": [{"content": {"parts": [{"text": get_random_message()}]}}]}

    if use_google_ai and google_api_key_cycle:
        google_api_key = next(google_api_key_cycle)

        ai_prompt = (
            f"{prompt}\n\nRespond with only one sentence in casual urban English, like a natural conversation, and do not use symbols."
            if language == "en"
            else f"{prompt}\n\nBerikan 1 kalimat saja dalam bahasa gaul daerah Jakarta seperti obrolan dan jangan gunakan simbol apapun."
        )

        url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={google_api_key}'
        headers = {'Content-Type': 'application/json'}
        data = {'contents': [{'parts': [{'text': ai_prompt}]}]}

        for attempt in range(3):
            try:
                response = session.post(url, headers=headers, json=data, timeout=10)
                response.raise_for_status()
                ai_response = response.json()
                response_text = ai_response['candidates'][0]['content']['parts'][0]['text'].strip()

                if response_text == last_ai_response:
                    log_message("âš ï¸ AI memberikan balasan yang sama, mencoba ulang...")
                    time.sleep(1)
                    continue

                last_ai_response = response_text
                return ai_response

            except Exception as e:
                log_message(f"âš ï¸ Google AI error (attempt {attempt + 1}): {e}")
                if attempt < 2:
                    time.sleep(2)

        return {"candidates": [{"content": {"parts": [{"text": last_ai_response or get_random_message()}]}}]}
    else:
        return {"candidates": [{"content": {"parts": [{"text": get_random_message()}]}}]}

def check_rate_limit(token):
    """Check if token is rate limited"""
    if token in rate_limit_reset:
        if time.time() < rate_limit_reset[token]:
            wait_time = rate_limit_reset[token] - time.time()
            log_message(f"â³ Token rate limited, menunggu {wait_time:.1f} detik...")
            return False
    return True

def handle_rate_limit(token, response):
    """Handle rate limit response"""
    if response.status_code == 429:
        retry_after = response.headers.get('Retry-After')
        if retry_after:
            wait_time = float(retry_after)
            rate_limit_reset[token] = time.time() + wait_time
            log_message(f"âš ï¸ Rate limited! Menunggu {wait_time} detik...")
            time.sleep(wait_time)
            return True
    return False

def validate_token(token):
    """Validate Discord token"""
    headers = {'Authorization': f'{token}'}
    try:
        response = session.get('https://discord.com/api/v9/users/@me', headers=headers, timeout=5)
        if response.status_code == 200:
            return True, response.json().get('id')
        else:
            log_message(f"âš ï¸ Token tidak valid: {response.status_code}")
            return False, None
    except Exception as e:
        log_message(f"âš ï¸ Error validasi token: {e}")
        return False, None

def send_message(channel_id, message_text, token, reply_to=None, reply_mode=True, delete_after_send=False):
    if not check_rate_limit(token):
        return False

    # Validasi input
    if not message_text or len(message_text) > 2000:
        log_message("âš ï¸ Pesan kosong atau terlalu panjang (max 2000 karakter)")
        return False

    headers = {
        'Authorization': token,
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    payload = {'content': message_text}
    
    if reply_mode and reply_to:
        payload['message_reference'] = {
            'message_id': reply_to,
            'channel_id': channel_id
        }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = session.post(
                f"https://discord.com/api/v9/channels/{channel_id}/messages",
                json=payload,
                headers=headers,
                timeout=10
            )

            # Handle rate limiting
            if handle_rate_limit(token, response):
                continue

            if response.status_code in [200, 201]:
                data = response.json()
                message_id = data.get('id')
                log_message(f"âœ… Pesan terkirim: {message_text[:50]}...")

                # Hapus pesan jika diperlukan
                if delete_after_send and message_id:
                    time.sleep(0.5)  # Delay sebelum hapus
                    delete_url = f"https://discord.com/api/v9/channels/{channel_id}/messages/{message_id}"
                    try:
                        del_resp = session.delete(delete_url, headers=headers, timeout=5)
                        if del_resp.status_code == 204:
                            log_message("ðŸ—‘ï¸ Pesan berhasil dihapus.")
                        else:
                            log_message(f"âš ï¸ Gagal menghapus pesan: {del_resp.status_code}")
                    except Exception as e:
                        log_message(f"âš ï¸ Error saat menghapus: {e}")
                
                return True
            
            elif response.status_code == 403:
                log_message("âŒ Akses ditolak (403) - Periksa permission bot!")
                return False
            
            elif response.status_code == 404:
                log_message("âŒ Channel tidak ditemukan (404)")
                return False
            
            else:
                log_message(f"âš ï¸ Gagal mengirim (attempt {attempt + 1}): {response.status_code}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                
        except requests.exceptions.Timeout:
            log_message(f"âš ï¸ Timeout (attempt {attempt + 1})")
            if attempt < max_retries - 1:
                time.sleep(2)
        
        except Exception as e:
            log_message(f"âš ï¸ Error (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2)

    return False

def auto_reply(channel_id, read_delay, reply_delay, use_google_ai, use_file_reply, language, reply_mode, delete_after_send):
    global last_message_id, bot_user_id

    # Validasi token pertama kali
    current_token = next(discord_token_cycle)
    is_valid, bot_id = validate_token(current_token)
    
    if not is_valid:
        log_message("âŒ Tidak ada token yang valid!")
        return
    
    bot_user_id = bot_id
    log_message(f"âœ… Bot siap! ID: {bot_user_id}")

    consecutive_errors = 0
    max_consecutive_errors = 5

    while True:
        token = next(discord_token_cycle)
        
        if not check_rate_limit(token):
            time.sleep(5)
            continue

        headers = {
            'Authorization': token,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        try:
            response = session.get(
                f'https://discord.com/api/v9/channels/{channel_id}/messages?limit=1',
                headers=headers,
                timeout=10
            )

            if handle_rate_limit(token, response):
                continue

            if response.status_code == 200:
                consecutive_errors = 0
                messages = response.json()
                
                if messages and isinstance(messages, list):
                    msg = messages[0]
                    msg_id = msg.get('id')
                    author_id = msg.get('author', {}).get('id')
                    message_type = msg.get('type', 0)

                    # Periksa apakah pesan baru dan bukan dari bot
                    if (last_message_id is None or int(msg_id) > int(last_message_id)) and author_id != bot_user_id and message_type != 8:
                        user_message = msg.get('content', '')
                        
                        if user_message:  # Hanya balas jika ada konten
                            log_message(f"ðŸ’¬ Pesan diterima: {user_message[:50]}...")

                            result = generate_reply(user_message, use_google_ai, use_file_reply, language)
                            response_text = result['candidates'][0]['content']['parts'][0]['text'] if result else get_random_message()

                            time.sleep(reply_delay)
                            
                            success = send_message(
                                channel_id,
                                response_text,
                                token,
                                reply_to=msg_id if reply_mode else None,
                                reply_mode=reply_mode,
                                delete_after_send=delete_after_send
                            )
                            
                            if success:
                                last_message_id = msg_id
            
            elif response.status_code == 403:
                log_message("âŒ Akses ditolak! Periksa permission channel.")
                consecutive_errors += 1
            
            elif response.status_code == 404:
                log_message("âŒ Channel tidak ditemukan!")
                return
            
            else:
                log_message(f"âš ï¸ Error response: {response.status_code}")
                consecutive_errors += 1

            time.sleep(read_delay)

        except requests.exceptions.Timeout:
            log_message("âš ï¸ Timeout saat membaca pesan")
            consecutive_errors += 1
            time.sleep(read_delay)
        
        except Exception as e:
            log_message(f"âš ï¸ Error: {e}")
            consecutive_errors += 1
            time.sleep(read_delay)

        # Stop jika terlalu banyak error berturut-turut
        if consecutive_errors >= max_consecutive_errors:
            log_message("âŒ Terlalu banyak error! Bot dihentikan.")
            return

if __name__ == "__main__":
    try:
        use_reply = input("Ingin menggunakan fitur auto-reply? (y/n): ").lower() == 'y'
        channel_id = input("Masukkan ID channel: ").strip()
        
        if not channel_id.isdigit():
            print("âŒ ID channel harus berupa angka!")
            exit(1)
        
        delete_after_send = input("Hapus pesan setelah dikirim? (y/n): ").lower() == 'y'

        if use_reply:
            use_google_ai = input("Gunakan Google Gemini AI untuk balasan? (y/n): ").lower() == 'y'
            use_file_reply = input("Gunakan pesan dari file pesan.txt? (y/n): ").lower() == 'y'
            reply_mode = input("Ingin membalas pesan (reply) atau hanya mengirim pesan? (reply/send): ").lower() == 'reply'
            language_choice = input("Pilih bahasa untuk balasan (id/en): ").lower()
            
            if language_choice not in ["id", "en"]:
                language_choice = "id"

            read_delay = int(input("Set Delay Membaca Pesan Terbaru (detik, min 3): ") or 3)
            reply_delay = int(input("Set Delay Balas Pesan (detik, min 2): ") or 2)
            
            read_delay = max(3, read_delay)
            reply_delay = max(2, reply_delay)

            log_message("ðŸš€ Bot dimulai...")
            auto_reply(channel_id, read_delay, reply_delay, use_google_ai, use_file_reply, language_choice, reply_mode, delete_after_send)
        
        else:
            send_interval = int(input("Set Interval Pengiriman Pesan (detik, min 5): ") or 5)
            send_interval = max(5, send_interval)
            
            log_message("ðŸš€ Bot dimulai (mode broadcast)...")
            token = next(discord_token_cycle)
            
            # Validasi token
            is_valid, _ = validate_token(token)
            if not is_valid:
                print("âŒ Token tidak valid!")
                exit(1)
            
            while True:
                msg = get_random_message()
                success = send_message(channel_id, msg, token, reply_mode=False, delete_after_send=delete_after_send)
                
                if not success:
                    token = next(discord_token_cycle)
                
                time.sleep(send_interval)
    
    except KeyboardInterrupt:
        log_message("\nðŸ‘‹ Bot dihentikan oleh user.")
    except Exception as e:
        log_message(f"âŒ Fatal error: {e}")
