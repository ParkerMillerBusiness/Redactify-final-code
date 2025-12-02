# core/policy.py

from __future__ import annotations

import yaml
from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class EntityPolicy:
    id: str
    action: str
    threshold: float = 0.75
    placeholder: str | None = None
    mask_rules: Dict[str, Any] | None = None


@dataclass
class Policy:
    entities: Dict[str, EntityPolicy]
    preserve_separators: bool = True
    pseudonym_scope: str = "per_document"

    def threshold_for(self, ent: str) -> float:
        ep = self.entities.get(ent)
        return ep.threshold if ep else 0.5

    def action_for(self, ent: str) -> str:
        ep = self.entities.get(ent)
        return ep.action if ep else "none"

    def entity_policy(self, ent: str) -> EntityPolicy | None:
        return self.entities.get(ent)


def load_policy(path: str) -> Policy:
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    entities_cfg = cfg.get("entities", {})
    entities: Dict[str, EntityPolicy] = {}
    for ent_id, props in entities_cfg.items():
        entities[ent_id] = EntityPolicy(
            id=ent_id,
            action=props.get("action", "redact"),
            threshold=float(props.get("threshold", 0.75)),
            placeholder=props.get("placeholder"),
            mask_rules=props.get("mask_rules"),
        )

    format_cfg = cfg.get("format", {})
    pseudo_cfg = cfg.get("pseudonymization", {})

    return Policy(
        entities=entities,
        preserve_separators=bool(format_cfg.get("preserve_separators", True)),
        pseudonym_scope=pseudo_cfg.get("scope", "per_document"),
    )
