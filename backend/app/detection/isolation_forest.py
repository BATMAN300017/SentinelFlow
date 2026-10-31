"""Unsupervised Isolation Forest anomaly detector for account-level risk scoring.

Uses sklearn's IsolationForest to detect statistical outliers across
account-level behavioral features. Designed for unsupervised operation —
NEVER accesses ground-truth labels.

Typical usage:
    detector = IsolationForestDetector()
    detector.fit_account_features(accounts_df)
    results = detector.score_accounts(accounts_df)
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import RobustScaler

from app.core.logging import logger

__all__ = [
    "IsolationForestDetector",
    "IsolationForestResult",
    "ACCOUNT_FEATURE_COLUMNS",
]

ACCOUNT_FEATURE_COLUMNS: List[str] = [
    "total_in",
    "total_out",
    "txn_count",
    "unique_counterparties",
    "avg_amount",
    "std_amount",
    "in_out_ratio",
    "max_single_txn",
    "time_span_hours",
    "unique_currencies",
]

# Minimum number of transactions before an account is considered
# sufficiently mature for Isolation Forest scoring.
_COLD_START_THRESHOLD: int = 3

# Default cold-start risk score (mildly elevated to prompt analyst review).
_COLD_START_SCORE: float = 15.0


@dataclass
class IsolationForestResult:
    """Result container for a single account's Isolation Forest score."""

    account_id: str
    risk_score: float  # 0-100, higher = more anomalous
    raw_if_score: float  # Original sklearn score (-1 to 1)
    is_cold_start: bool
    feature_snapshot: Dict[str, float] = field(default_factory=dict)
    evidence: str = ""


class IsolationForestDetector:
    """Unsupervised anomaly detector using Isolation Forest.

    The detector fits an Isolation Forest model on account-level feature
    matrices and returns normalised anomaly scores (0-100).

    Parameters
    ----------
    contamination : str | float
        Fraction of outliers expected.  ``'auto'`` lets sklearn decide.
    n_estimators : int
        Number of isolation trees.
    random_state : int | None
        Seed for reproducibility.
    """

    def __init__(
        self,
        contamination: str | float = "auto",
        n_estimators: int = 200,
        random_state: int | None = 42,
    ) -> None:
        self._contamination = contamination
        self._n_estimators = n_estimators
        self._random_state = random_state

        self._model: Optional[IsolationForest] = None
        self._scaler: RobustScaler = RobustScaler()
        self._is_fitted: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fit_account_features(self, accounts_df: List[Dict[str, Any]]) -> None:
        """Fit the Isolation Forest model on account-level feature dicts.

        Parameters
        ----------
        accounts_df : list[dict]
            Each dict must contain keys from ``ACCOUNT_FEATURE_COLUMNS``
            plus ``account_id`` and ``txn_count``.

        Raises
        ------
        ValueError
            If *accounts_df* is empty or contains no mature accounts.
        """
        if not accounts_df:
            logger.warning("IsolationForestDetector.fit called with empty data")
            raise ValueError("Cannot fit Isolation Forest on empty account data")

        # Filter out cold-start accounts for fitting
        mature = [
            a for a in accounts_df
            if a.get("txn_count", 0) >= _COLD_START_THRESHOLD
        ]
        if not mature:
            logger.warning(
                "All %d accounts are cold-start (txn_count < %d); "
                "Isolation Forest will not be fitted.",
                len(accounts_df),
                _COLD_START_THRESHOLD,
            )
            raise ValueError(
                "Cannot fit Isolation Forest: all accounts are cold-start"
            )

        X = self._extract_matrix(mature)

        self._scaler = RobustScaler()
        X_scaled = self._scaler.fit_transform(X)

        self._model = IsolationForest(
            contamination=self._contamination,
            n_estimators=self._n_estimators,
            random_state=self._random_state,
            n_jobs=-1,
        )
        self._model.fit(X_scaled)
        self._is_fitted = True
        logger.info(
            "IsolationForest fitted on %d mature accounts (%d total, %d cold-start)",
            len(mature),
            len(accounts_df),
            len(accounts_df) - len(mature),
        )

    def score_accounts(
        self,
        accounts_df: List[Dict[str, Any]],
    ) -> List[IsolationForestResult]:
        """Score a list of accounts and return normalised risk scores.

        Cold-start accounts (``txn_count < 3``) receive a default mildly-
        elevated score with an explanatory evidence string.

        Parameters
        ----------
        accounts_df : list[dict]
            Same schema as ``fit_account_features``.

        Returns
        -------
        list[IsolationForestResult]
        """
        if not accounts_df:
            return []

        if not self._is_fitted or self._model is None:
            logger.warning(
                "score_accounts called before fit; returning cold-start "
                "scores for all %d accounts",
                len(accounts_df),
            )
            return [
                self._cold_start_result(a) for a in accounts_df
            ]

        results: List[IsolationForestResult] = []

        for account in accounts_df:
            acct_id = str(account.get("account_id", "unknown"))

            if account.get("txn_count", 0) < _COLD_START_THRESHOLD:
                results.append(self._cold_start_result(account))
                continue

            x = self._extract_row(account)
            x_scaled = self._scaler.transform(x)

            # sklearn score_samples returns values where lower = more
            # anomalous (typically in range [-1, 1]).
            raw_score = float(self._model.score_samples(x_scaled)[0])
            risk_score = self._normalise_score(raw_score)

            snapshot = {
                col: float(account.get(col, 0.0))
                for col in ACCOUNT_FEATURE_COLUMNS
            }

            evidence = self._build_evidence(acct_id, risk_score, snapshot)

            results.append(
                IsolationForestResult(
                    account_id=acct_id,
                    risk_score=risk_score,
                    raw_if_score=raw_score,
                    is_cold_start=False,
                    feature_snapshot=snapshot,
                    evidence=evidence,
                )
            )

        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_matrix(self, rows: List[Dict[str, Any]]) -> np.ndarray:
        """Build an (N, F) numpy matrix from account dicts."""
        return np.array(
            [
                [float(row.get(col, 0.0)) for col in ACCOUNT_FEATURE_COLUMNS]
                for row in rows
            ],
            dtype=np.float64,
        )

    def _extract_row(self, account: Dict[str, Any]) -> np.ndarray:
        """Extract a single (1, F) row."""
        return np.array(
            [[float(account.get(col, 0.0)) for col in ACCOUNT_FEATURE_COLUMNS]],
            dtype=np.float64,
        )

    @staticmethod
    def _normalise_score(raw_score: float) -> float:
        """Map sklearn's raw anomaly score to 0-100 risk scale.

        sklearn score_samples returns values where:
        - Values near 0 or negative → strong anomalies
        - Values near +0.5 → normal observations

        We use a shifted sigmoid-style mapping:
        risk = 100 * (1 - sigmoid(raw_score * k))
        This gracefully maps the open range to [0, 100].
        """
        # Linear rescale from typical [-0.5, 0.5] range,
        # then clip to [0, 100].
        # More negative raw = more anomalous → higher risk.
        # The offset in decision_function is ~0 at the boundary.
        risk = max(0.0, min(100.0, 50.0 - raw_score * 100.0))
        return round(risk, 1)

    def _cold_start_result(self, account: Dict[str, Any]) -> IsolationForestResult:
        """Return a default result for cold-start accounts."""
        acct_id = str(account.get("account_id", "unknown"))
        txn_count = account.get("txn_count", 0)
        return IsolationForestResult(
            account_id=acct_id,
            risk_score=_COLD_START_SCORE,
            raw_if_score=0.0,
            is_cold_start=True,
            feature_snapshot={
                col: float(account.get(col, 0.0))
                for col in ACCOUNT_FEATURE_COLUMNS
            },
            evidence=(
                f"Account {acct_id} has insufficient history "
                f"({txn_count} transactions, minimum {_COLD_START_THRESHOLD} "
                f"required). Assigned default cold-start score of "
                f"{_COLD_START_SCORE}."
            ),
        )

    @staticmethod
    def _build_evidence(
        acct_id: str,
        risk_score: float,
        snapshot: Dict[str, float],
    ) -> str:
        """Build human-readable evidence string."""
        parts = [f"Isolation Forest anomaly score for {acct_id}: {risk_score}/100."]

        # Highlight notable feature values
        if snapshot.get("in_out_ratio", 1.0) > 3.0:
            parts.append(
                f"In/out ratio is elevated at {snapshot['in_out_ratio']:.2f}."
            )
        if snapshot.get("in_out_ratio", 1.0) < 0.3:
            parts.append(
                f"In/out ratio is very low at {snapshot['in_out_ratio']:.2f} "
                f"(mostly outgoing funds)."
            )
        if snapshot.get("unique_counterparties", 0) >= 20:
            parts.append(
                f"Transacts with {int(snapshot['unique_counterparties'])} "
                f"unique counterparties."
            )
        if snapshot.get("std_amount", 0) > snapshot.get("avg_amount", 1) * 2:
            parts.append(
                "Transaction amounts show high variance "
                f"(std={snapshot['std_amount']:,.2f} vs "
                f"avg={snapshot['avg_amount']:,.2f})."
            )

        return " ".join(parts)

_global_if_detector: Optional[IsolationForestDetector] = None

def get_isolation_forest_score(features: Dict[str, Any]) -> Dict[str, Any]:
    """Scores a single transaction's operational feature snapshot using Isolation Forest."""
    global _global_if_detector
    if _global_if_detector is None or not _global_if_detector._is_fitted:
        _global_if_detector = IsolationForestDetector(n_estimators=50, random_state=42)
        # Seed with synthetic baseline operational distributions
        synthetic_baseline = [
            {
                "total_in": float(i * 1000),
                "total_out": float(i * 900),
                "txn_count": max(3, i),
                "unique_counterparties": max(1, i // 2),
                "avg_amount": 2500.0,
                "std_amount": 1000.0,
                "in_out_ratio": 1.1,
                "max_single_txn": 10000.0,
                "time_span_hours": 72.0,
                "unique_currencies": 1.0,
            }
            for i in range(1, 30)
        ]
        _global_if_detector.fit_account_features(synthetic_baseline)

    mapped_account = {
        "account_id": features.get("account_id", "CURRENT"),
        "total_in": float(features.get("recent_inbound_sum", 0.0)),
        "total_out": float(features.get("short_window_sum", features.get("amount", 0.0))),
        "txn_count": int(features.get("history_count", 1)),
        "unique_counterparties": int(features.get("unique_counterparties", 1)),
        "avg_amount": float(features.get("amount", 1000.0)),
        "std_amount": float(features.get("amount", 1000.0) * 0.3),
        "in_out_ratio": float(features.get("in_out_ratio", 1.0)),
        "max_single_txn": float(features.get("amount", 1000.0)),
        "time_span_hours": 24.0,
        "unique_currencies": 1.0,
    }
    
    results = _global_if_detector.score_accounts([mapped_account])
    res = results[0] if results else _global_if_detector._cold_start_result(mapped_account)
    return {
        "isolation_forest_score": res.risk_score,
        "raw_score": res.raw_if_score,
        "is_cold_start": res.is_cold_start,
        "evidence": res.evidence
    }
