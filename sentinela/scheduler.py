"""Agendador: dispara os backups automáticos e a limpeza por retenção."""

import logging
import threading
import time

from . import engine, settings
from .storage import now

log = logging.getLogger("sentinela")


class Scheduler(threading.Thread):
    def __init__(self, tick=None):
        super().__init__(daemon=True, name="sentinela-scheduler")
        self.tick = tick or settings.SCHEDULER_TICK
        self._stop = threading.Event()
        self._last_housekeeping = 0.0

    def stop(self):
        self._stop.set()

    def run(self):
        log.info("Agendador iniciado (verificação a cada %ss)", self.tick)
        if engine.next_run_at() is None:
            engine.schedule_next()
        while not self._stop.is_set():
            try:
                self.step()
            except Exception:
                log.exception("Erro no agendador")
            self._stop.wait(self.tick)

    def step(self):
        current = now()
        nxt = engine.next_run_at()
        if nxt is None:
            nxt = engine.schedule_next(current)

        if current >= nxt:
            if not engine.connection_ready():
                # Sem conexão configurada: apenas reagenda.
                engine.schedule_next(current, engine.interval_days())
            elif not engine.is_busy():
                late = (current - nxt).total_seconds()
                if late > 3600:
                    log.info("Backup automático atrasado (agendado para %s) — executando agora", nxt)
                try:
                    engine.start_backup("auto", wait=True)
                except engine.Busy:
                    return  # tenta de novo no próximo ciclo
                except Exception as e:
                    log.error("Backup automático não pôde ser iniciado: %s", e)
                engine.schedule_next(now(), engine.interval_days())

        # Limpeza periódica (retenção e logs antigos), a cada hora.
        if time.monotonic() - self._last_housekeeping > 3600:
            self._last_housekeeping = time.monotonic()
            if not engine.is_busy():
                engine.apply_retention()
                engine.prune_exec_logs()
