import logging
import sys

from common.env import LOG_LEVEL

logger = logging.getLogger()

logger.setLevel(LOG_LEVEL)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
# logger.addHandler(BroadcastHandler())
# logger.addHandler(LightHandler())
