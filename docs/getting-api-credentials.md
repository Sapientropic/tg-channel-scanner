# Getting Telegram API Credentials

You need `api_id` and `api_hash` from Telegram to use tgcli. Here's how to get them.

## Normal Method

1. Go to **https://my.telegram.org/apps**
2. Log in with your phone number
3. Fill in the form (app name, short name, etc. — anything works)
4. Copy the `api_id` (number) and `api_hash` (string)

## Common Issue: "ERROR" on the Form

Telegram sometimes shows a blank ERROR page. This is usually **IP-based rate limiting**.

### Fixes (in order of reliability)

**Option A: Mobile cellular data**
- Switch your computer/phone to mobile data (not Wi-Fi)
- Open my.telegram.org again
- This works because the IP block is usually against datacenter/VPN IPs

**Option B: GitHub Codespaces**
1. Go to github.com/codespaces
2. Create a new codespace
3. In the terminal: `curl https://my.telegram.org` (just to verify access)
4. Then open the codespace's forwarded port in your browser
5. Log in and get your credentials

**Option C: Google Colab**
1. Open a Colab notebook
2. Use `!curl` or a Python `requests` session to interact with the form
3. Automate the login + form submission

### If All Else Fails

Ask someone who already has credentials to help, or try again from a different network after 24 hours.

## After Getting Credentials

Edit `config.toml` in the project root:

```toml
api_id = 12345678
api_hash = "your_api_hash_here"
session_store = "file"
```

Then authenticate:

```bash
# Mac/Linux
source .venv/bin/activate
tg auth login

# Windows
.venv\Scripts\activate.bat
tg auth login
```

Telegram will send a verification code to your app. Enter it when prompted.

## Security Notes

- **Never share** your `api_hash` or commit it to Git
- **Never share** your `.session` file (it's your login token)
- `config.toml` and `*.session` are in `.gitignore` by default
- Each account can create up to 20 API apps, but you only need one
