import os
from concurrent.futures import ThreadPoolExecutor

from colorama import Fore


cpu_workers = max(1, os.cpu_count() - 1)
# cpu_workers = 24
THREAD_POOL = ThreadPoolExecutor(max_workers=cpu_workers)

#   _________       __
#  /   _____/ _____/  |_ __ ________
#  \_____  \_/ __ \   __\  |  \____ \
#  /        \  ___/|  | |  |  /  |_> >
# /_______  /\___  >__| |____/|   __/
#         \/     \/           |__|


BOT_NAME = f"{Fore.LIGHTRED_EX}AGIMUS{Fore.RESET}"
ROOT_DIR:str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


__all__ = ["BOT_NAME", "ROOT_DIR", "THREAD_POOL"]
