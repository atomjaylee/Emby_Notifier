from __future__ import annotations

import threading

from emby_notifier.domain.media import AggregatedMediaDetail, MediaDetail


class EpisodeBuffer:
    def __init__(
        self,
        notifier,
        timeout_seconds: int,
        auto_start_timer: bool = True,
        timer_factory=threading.Timer,
    ):
        self.notifier = notifier
        self.timeout_seconds = timeout_seconds
        self.auto_start_timer = auto_start_timer
        self.timer_factory = timer_factory
        self._buffers: dict[str, list[tuple[int, MediaDetail]]] = {}
        self._timers: dict[str, threading.Timer] = {}
        self._lock = threading.Lock()

    def add(self, buffer_key: str, detail: MediaDetail, episode_number: int) -> None:
        with self._lock:
            if buffer_key not in self._buffers:
                self._buffers[buffer_key] = []
            self._buffers[buffer_key].append((episode_number, detail))
            self._restart_timer(buffer_key)

    def flush(self, buffer_key: str) -> None:
        with self._lock:
            episodes = self._buffers.pop(buffer_key, [])
            timer = self._timers.pop(buffer_key, None)
            if timer is not None and timer.is_alive():
                timer.cancel()

        if not episodes:
            return

        episodes = sorted(episodes, key=lambda episode: episode[0])
        if len(episodes) == 1:
            self.notifier.send_media(episodes[0][1])
            return

        episode_numbers = tuple(number for number, _ in episodes)
        self.notifier.send_aggregated_media(
            AggregatedMediaDetail(
                detail=episodes[0][1],
                tv_episode_min=min(episode_numbers),
                tv_episode_max=max(episode_numbers),
                tv_episode_total=len(episode_numbers),
                tv_episode_list=episode_numbers,
            )
        )

    def _restart_timer(self, buffer_key: str) -> None:
        if not self.auto_start_timer:
            return

        old_timer = self._timers.pop(buffer_key, None)
        if old_timer is not None and old_timer.is_alive():
            old_timer.cancel()

        timer = self.timer_factory(self.timeout_seconds, self.flush, args=(buffer_key,))
        timer.daemon = True
        timer.start()
        self._timers[buffer_key] = timer
