
import os
import time
import threading
from queue import Queue, Empty
import requests
from datetime import datetime
from colorama import init
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel

init(autoreset=True)
console = Console()

logo = r"""
[bold blue]

                                  _                    
                                 | |                   
  ___ _ __   __ _ _ __ ___    ___| |__   __ _ _ __ ___ 
 / __| '_ \ / _` | '_ ` _ \  / __| '_ \ / _` | '__/ _ \
 \__ \ |_) | (_| | | | | | | \__ \ | | | (_| | | |  __/
 |___/ .__/ \__,_|_| |_| |_| |___/_| |_|\__,_|_|  \___|
     | |                                               
     |_|                                               

"""

APPROVAL_URL = "https://raw.githubusercontent.com/rihitoo/spam-share/main/approval.txt"
APPROVAL_FILE = "approval.txt"  # <-- dito lang, walang folder


def banner():
    clear()
    rprint(Panel(logo, title="[bold yellow]Facebook Automation Tool", subtitle="[bold cyan]@Rikuo", border_style="bold magenta"))


def clear():
    os.system('cls' if os.name == 'nt' else 'clear')


def linex():
    console.print("─" * 54, style="dim")


def check_approval():
    if os.path.exists(APPROVAL_FILE):
        with open(APPROVAL_FILE, "r") as f:
            local_key = f.read().strip()
        if validate_key(local_key):
            console.print(Panel("[green]Approval verified from local file.[/green]"))
            return True
        else:
            console.print(Panel("[red]Local approval key invalid. Please enter a valid key.[/red]"))
            os.remove(APPROVAL_FILE)

    while True:
        key = console.input("[bold green]Enter your approval key:[/bold green] ").strip()
        if validate_key(key):
            with open(APPROVAL_FILE, "w") as f:
                f.write(key)
            console.print(Panel("[green]Approval key accepted and saved![/green]"))
            return True
        else:
            console.print(Panel("[red]Invalid approval key. Please try again.[/red]"))


def validate_key(key):
    try:
        response = requests.get(APPROVAL_URL, timeout=10)
        if response.status_code == 200:
            approved_keys = [line.strip() for line in response.text.splitlines() if line.strip()]
            return key in approved_keys
        else:
            console.print(Panel("[yellow]Warning: Could not fetch approval list. Check your internet connection.[/yellow]"))
            return False
    except requests.RequestException as e:
        console.print(Panel(f"[yellow]Warning: Network error during approval check: {e}[/yellow]"))
        return False


class ShareManager:
    def __init__(self, tokens, ids, link, total_shares, delay):
        self.tokens = tokens
        self.ids = ids
        self.link = link
        self.total_shares = total_shares
        self.delay = delay
        self.success_count = 0
        self.lock = threading.Lock()
        self.queue = Queue()

        share_count = 0
        while share_count < self.total_shares:
            for token, page_id in zip(self.tokens, self.ids):
                if share_count >= self.total_shares:
                    break
                self.queue.put((token, page_id))
                share_count += 1

    def share_post(self, token, page_id):
        url = f"https://graph.facebook.com/v13.0/{page_id}/feed"
        payload = {
            'link': self.link,
            'published': '0',
            'access_token': token
        }

        try:
            response = requests.post(url, data=payload).json()
            if 'id' in response:
                with self.lock:
                    self.success_count += 1
                    console.print(Panel(f"✅ Shared successfully. Total: {self.success_count}/{self.total_shares}", style='cyan'))
            else:
                console.print(Panel(f"❌ Failed: {response}", style='red'))
        except requests.exceptions.RequestException as e:
            console.print(Panel(f"⚠️ Network error: {e}", style='yellow'))

        time.sleep(self.delay)

    def worker(self):
        while True:
            try:
                token, page_id = self.queue.get(timeout=0.5)
                self.share_post(token, page_id)
                self.queue.task_done()
            except Empty:
                break

    def start_sharing(self):
        start_time = datetime.now()

        threads = []
        max_threads = min(30, len(self.tokens))
        for _ in range(max_threads):
            t = threading.Thread(target=self.worker)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        end_time = datetime.now()

        console.print(Panel(
            f"🚀 Completed {self.success_count}/{self.total_shares}\n\n"
            f"[bold cyan]Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"[bold yellow]End time:   {end_time.strftime('%Y-%m-%d %H:%M:%S')}",
            style='green'))


def get_tokens():
    token_file = os.path.join("Rikuo", "token.txt")
    if not os.path.exists(token_file):
        console.print(Panel(f"❌ Token file not found: {token_file}", style='red'))
        return []
    with open(token_file, 'r') as f:
        return [line.strip() for line in f if line.strip()]


def get_ids():
    id_file = os.path.join("Rikuo", "id.txt")
    if not os.path.exists(id_file):
        console.print(Panel(f"❌ ID file not found: {id_file}", style='red'))
        return []
    with open(id_file, 'r') as f:
        return [line.strip() for line in f if line.strip()]


def spam_share():
    banner()

    tokens = get_tokens()
    if not tokens:
        console.print("❌ No valid tokens found. Exiting...", style='red')
        return

    ids = get_ids()
    if not ids:
        console.print("❌ No valid IDs found. Exiting...", style='red')
        return

    link = console.input("[bold green]Enter the post link to share: ").strip()
    linex()

    try:
        total_shares = int(console.input("[bold green]Enter total number of shares: [/]").strip())
        linex()
        if total_shares <= 0:
            console.print("❌ Share count must be greater than 0.", style='red')
            return
    except ValueError:
        console.print("❌ Invalid number input.", style='red')
        return

    try:
        delay = float(console.input("[bold green]Enter delay between shares (in seconds): ").strip())
        linex()
        if delay < 0:
            console.print("❌ Delay must not be negative.", style='red')
            return
    except ValueError:
        console.print("❌ Invalid delay input.", style='red')
        return

    manager = ShareManager(tokens, ids, link, total_shares, delay)
    manager.start_sharing()


def main():
    banner()
    if not check_approval():
        console.print(Panel("[red]Approval failed or not granted. Exiting.[/red]"))
        return

    console.print("[bold green]1.[/bold green] Spam Share")
    console.print("[bold green]0.[/bold green] Exit")
    choice = console.input("\n[bold blue]Choose an option:[/bold blue] ")
    if choice == "1":
        spam_share()
    elif choice == "0":
        exit()


if __name__ == "__main__":
    main()
