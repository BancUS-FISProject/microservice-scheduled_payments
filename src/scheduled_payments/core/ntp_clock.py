import time
import datetime
import threading
from logging import getLogger
import ntplib

logger = getLogger(__name__)


class NtpClock:
    def __init__(self, server: str, refresh_seconds: int = 60, timeout: int = 3):
        self.server = server
        self.refresh_seconds = refresh_seconds
        self.timeout = timeout

        self._offset = 0.0
        self._lock = threading.Lock()

        self._stop = threading.Event()
        self._thread: threading.Thread = None

        logger.info("Inicializando NtpClock (server=%s refresh=%ss timeout=%ss)",
                    self.server, self.refresh_seconds, self.timeout)

        self._sync_safe(initial=True)

        self._thread = threading.Thread(target=self._loop, daemon=True, name="ntp-clock")
        self._thread.start()

    def _loop(self):
        while not self._stop.is_set():
            self._stop.wait(self.refresh_seconds)
            if self._stop.is_set():
                break
            self._sync_safe(initial=False)

    def stop(self):
        logger.info("Parando NtpClock (server=%s)", self.server)
        self._stop.set()

    def _sync_safe(self, initial: bool):
        try:
            self._sync_once()
        except Exception as e:
            msg = "Sync inicial NTP fallido" if initial else "Error refrescando NTP"
            logger.warning("%s (%s): %s", msg, self.server, e, exc_info=True)

    def _sync_once(self):
        client = ntplib.NTPClient()
        t0 = time.time()
        response = client.request(self.server, version=4, timeout=self.timeout)
        t1 = time.time()

        offset = response.tx_time - time.time()
        rtt = t1 - t0

        with self._lock:
            self._offset = offset

        logger.info("NTP sync OK (server=%s offset=%.6fs rtt=%.3fs stratum=%s)",
                    self.server, offset, rtt, getattr(response, "stratum", None))

        logger.debug("NTP details: delay=%s dispersion=%s tx_time=%s",
                     getattr(response, "delay", None),
                     getattr(response, "root_dispersion", None),
                     getattr(response, "tx_time", None))

    def now_epoch(self) -> float:
        with self._lock:
            return time.time() + self._offset

    def now_utc(self) -> datetime.datetime:
        return datetime.datetime.fromtimestamp(self.now_epoch(), tz=datetime.timezone.utc)

    def offset_seconds(self) -> float:
        with self._lock:
            return self._offset
