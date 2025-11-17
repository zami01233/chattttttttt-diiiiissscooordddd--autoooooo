import requests
import json
import sys

def get_discord_token(email, password):
    """
    Login ke Discord dan dapatkan token

    Args:
        email (str): Email Discord Anda
        password (str): Password Discord Anda

    Returns:
        str: Discord token jika berhasil, None jika gagal
    """

    print("\n" + "="*50)
    print("🔐 DISCORD TOKEN EXTRACTOR")
    print("="*50 + "\n")

    url = "https://discord.com/api/v9/auth/login"

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    payload = {
        "login": email,
        "password": password,
        "undelete": False,
        "captcha_key": None,
        "login_source": None,
        "gift_code_sku_id": None
    }

    try:
        print("📡 Menghubungi server Discord...")

        response = requests.post(url, headers=headers, json=payload)

        if response.status_code == 200:
            data = response.json()

            if "token" in data:
                token = data["token"]
                print("\n✅ LOGIN BERHASIL!\n")
                print("="*50)
                print("🎫 TOKEN ANDA:")
                print("="*50)
                print(f"\n{token}\n")
                print("="*50)
                print("\n⚠️  PENTING:")
                print("- Simpan token ini dengan AMAN")
                print("- JANGAN bagikan ke siapa pun")
                print("- Token ini = akses penuh ke akun Anda")
                print("="*50 + "\n")
                return token

            elif "ticket" in data:
                print("\n⚠️  AKUN ANDA MENGGUNAKAN 2FA (Two-Factor Authentication)")
                print("Masukkan kode 2FA Anda:")
                code_2fa = input("Kode 2FA: ").strip()
                return handle_2fa(data["ticket"], code_2fa)

            elif "captcha_key" in data:
                print("\n❌ Discord meminta CAPTCHA")
                print("Silakan coba lagi nanti atau gunakan browser")
                return None

        elif response.status_code == 400:
            print("\n❌ LOGIN GAGAL!")
            print("Email atau password salah. Cek kembali kredensial Anda.")
            return None

        elif response.status_code == 429:
            print("\n⏳ TERLALU BANYAK PERCOBAAN")
            print("Anda terkena rate limit. Tunggu beberapa menit.")
            return None

        else:
            print(f"\n❌ ERROR: Status code {response.status_code}")
            print(f"Response: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"\n❌ ERROR KONEKSI: {e}")
        print("Pastikan Anda terhubung ke internet.")
        return None
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return None

def handle_2fa(ticket, code):
    """
    Handle 2FA authentication

    Args:
        ticket (str): Ticket dari response login
        code (str): Kode 2FA dari user

    Returns:
        str: Token jika berhasil, None jika gagal
    """
    url = "https://discord.com/api/v9/auth/mfa/totp"

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    payload = {
        "code": code,
        "ticket": ticket,
        "login_source": None,
        "gift_code_sku_id": None
    }

    try:
        response = requests.post(url, headers=headers, json=payload)

        if response.status_code == 200:
            data = response.json()
            if "token" in data:
                token = data["token"]
                print("\n✅ VERIFIKASI 2FA BERHASIL!\n")
                print("="*50)
                print("🎫 TOKEN ANDA:")
                print("="*50)
                print(f"\n{token}\n")
                print("="*50)
                return token
        else:
            print("\n❌ Kode 2FA salah atau expired")
            return None

    except Exception as e:
        print(f"\n❌ ERROR 2FA: {e}")
        return None

def save_token_to_file(token, filename="discord_token.txt"):
    """
    Simpan token ke file

    Args:
        token (str): Discord token
        filename (str): Nama file untuk menyimpan token
    """
    try:
        with open(filename, 'w') as f:
            f.write(token)
        print(f"✅ Token berhasil disimpan ke '{filename}'")
    except Exception as e:
        print(f"❌ Gagal menyimpan token: {e}")

def main():
    """
    Main function
    """
    print("\n" + "="*50)
    print("⚠️  PERINGATAN KEAMANAN")
    print("="*50)
    print("- Gunakan HANYA untuk akun pribadi")
    print("- JANGAN bagikan token ke siapa pun")
    print("- Self-botting MELANGGAR Discord ToS")
    print("- Akun bisa di-ban jika ketahuan")
    print("="*50 + "\n")

    email = input("📧 Masukkan email Discord: ").strip()
    password = input("🔑 Masukkan password: ").strip()

    if not email or not password:
        print("\n❌ Email dan password tidak boleh kosong!")
        sys.exit(1)

    token = get_discord_token(email, password)

    if token:
        save = input("\n💾 Simpan token ke file? (y/n): ").strip().lower()
        if save == 'y' or save == 'yes':
            save_token_to_file(token)
        print("\n✅ Selesai!\n")
    else:
        print("\n❌ Gagal mendapatkan token.\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
