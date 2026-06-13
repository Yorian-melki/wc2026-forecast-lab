"""
Model factory for WC2026 tournament simulation.

Usage:
  from wc2026.model_factory import make_match_model
  model = make_match_model("expert", config)
  model = make_match_model("elo_calibrated", config)
"""
from __future__ import annotations

from typing import Union

from .match_model import MatchModel

MODEL_NAMES = ("expert", "elo_calibrated")


def make_match_model(
    model_name: str,
    config: dict | None = None,
) -> Union[MatchModel, "CalibratedEloMatchModel"]:
    """
    Create a match model by name.

    model_name:
      "expert"         — MatchModel with analyst priors + StatsBomb features (P0 model)
      "elo_calibrated" — CalibratedEloMatchModel (P3: Elo + calibrated Poisson)

    Note: Full Hybrid Elo-DC rejected (P2.5 gate: BORDERLINE_EXPERIMENTAL, ECE +17%).
    """
    if model_name == "expert":
        from .data_loader import load_config
        cfg = config or load_config()
        return MatchModel(cfg)

    if model_name == "elo_calibrated":
        from .calibrated_elo_model import CalibratedEloMatchModel, load_calibrated_params
        from .data_loader import load_config
        cfg = config or load_config()
        params = load_calibrated_params()
        return CalibratedEloMatchModel(config=cfg, params=params)

    raise ValueError(
        f"Unknown model '{model_name}'. Valid choices: {MODEL_NAMES}"
    )
