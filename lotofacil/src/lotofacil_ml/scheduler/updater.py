"""APScheduler-based background scheduler for automated data/model lifecycle."""

import logging
from typing import Optional

from lotofacil_ml.config import (
    SCHEDULE_RETRAIN_DAY,
    SCHEDULE_RETRAIN_HOUR,
    SCHEDULE_UPDATE_DAYS,
    SCHEDULE_UPDATE_HOUR,
)

logger = logging.getLogger(__name__)


class LotofacilScheduler:
    """Manages periodic data updates, retraining, validation, and prediction."""

    def __init__(self):
        from apscheduler.schedulers.background import BackgroundScheduler
        self._scheduler = BackgroundScheduler()
        self._setup_jobs()

    def _setup_jobs(self) -> None:
        # Job 1: Update data (Mon/Wed/Fri at 23:00)
        self._scheduler.add_job(
            self._job_update_data,
            trigger="cron",
            day_of_week=",".join(SCHEDULE_UPDATE_DAYS),
            hour=SCHEDULE_UPDATE_HOUR,
            minute=0,
            id="update_data",
            name="Fetch latest draw data",
            replace_existing=True,
        )

        # Job 2: Retrain models (Monday at 02:00)
        self._scheduler.add_job(
            self._job_retrain_models,
            trigger="cron",
            day_of_week=SCHEDULE_RETRAIN_DAY,
            hour=SCHEDULE_RETRAIN_HOUR,
            minute=0,
            id="retrain_models",
            name="Retrain all models",
            replace_existing=True,
        )

        logger.info("Scheduler jobs configured")

    # ── Job implementations ────────────────────────────────────────────────────

    def _job_update_data(self) -> None:
        logger.info("[Scheduler] Running update_data job")
        try:
            from lotofacil_ml.data.database import DatabaseManager
            from lotofacil_ml.data.fetcher import LotofacilFetcher
            db = DatabaseManager()
            fetcher = LotofacilFetcher(db)
            new_count = fetcher.sync_new_draws()
            logger.info("[Scheduler] Synced %d new draws", new_count)
            self._job_validate_predictions()
        except Exception as exc:
            logger.error("[Scheduler] update_data failed: %s", exc, exc_info=True)

    def _job_retrain_models(self) -> None:
        logger.info("[Scheduler] Running retrain_models job")
        try:
            from lotofacil_ml.data.database import DatabaseManager
            from lotofacil_ml.models.ensemble import EnsemblePredictor
            db = DatabaseManager()
            draws = db.get_all_concursos()
            predictor = EnsemblePredictor()
            predictor.train(draws)
            logger.info("[Scheduler] Retraining complete")
            self._job_generate_prediction()
        except Exception as exc:
            logger.error("[Scheduler] retrain_models failed: %s", exc, exc_info=True)

    def _job_validate_predictions(self) -> None:
        logger.info("[Scheduler] Running validate_predictions job")
        try:
            from lotofacil_ml.data.database import DatabaseManager
            db = DatabaseManager()
            pending = db.get_pending_validations()
            all_draws = {d["concurso"]: d for d in db.get_all_concursos()}
            for pred in pending:
                concurso = pred["concurso_alvo"]
                if concurso in all_draws:
                    actual = all_draws[concurso]["dezenas"]
                    hits = len(set(pred["dezenas_sugeridas"]) & set(actual))
                    db.update_validation(concurso, hits)
                    logger.info("[Scheduler] Concurso %d validated: %d hits", concurso, hits)
        except Exception as exc:
            logger.error("[Scheduler] validate_predictions failed: %s", exc, exc_info=True)

    def _job_generate_prediction(self) -> None:
        logger.info("[Scheduler] Running generate_prediction job")
        try:
            from lotofacil_ml.data.database import DatabaseManager
            from lotofacil_ml.models.ensemble import EnsemblePredictor
            db = DatabaseManager()
            draws = db.get_all_concursos()
            predictor = EnsemblePredictor()
            predictor.load()
            pred = predictor.predict_next_concurso(draws)
            db.save_prediction(
                pred["concurso_previsto"],
                pred["dezenas_sugeridas"],
                pred["probabilidades"],
                pred["confianca_media"],
                pred["modelos_utilizados"],
            )
            logger.info("[Scheduler] Prediction saved for concurso %d", pred["concurso_previsto"])
        except Exception as exc:
            logger.error("[Scheduler] generate_prediction failed: %s", exc, exc_info=True)

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def start(self) -> None:
        self._scheduler.start()
        logger.info("Scheduler started")
        jobs = self._scheduler.get_jobs()
        for job in jobs:
            logger.info("  Job: %s | next run: %s", job.name, job.next_run_time)

    def stop(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped")

    def list_jobs(self):
        return [
            {
                "id": j.id,
                "name": j.name,
                "next_run": str(j.next_run_time),
            }
            for j in self._scheduler.get_jobs()
        ]
