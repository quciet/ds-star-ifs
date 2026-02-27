from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PlanStep:
    id: int
    title: str
    details: str
    status: str = "todo"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "details": self.details,
            "status": self.status,
        }


@dataclass
class ExecResult:
    exit_code: int
    stdout: str
    stderr: str
    duration_sec: float
    timeout: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration_sec": self.duration_sec,
            "timeout": self.timeout,
        }


@dataclass
class VerifierResult:
    sufficient: bool
    reason: str
    missing: List[str] = field(default_factory=list)
    next_action: str = "add_step"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sufficient": self.sufficient,
            "reason": self.reason,
            "missing": self.missing,
            "next_action": self.next_action,
        }


@dataclass
class RouterDecision:
    action: str
    backtrack_to_step_id: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "backtrack_to_step_id": self.backtrack_to_step_id,
        }


@dataclass
class RunMetadata:
    provider: str
    model: str
    max_rounds: int
    question: str
    files: List[str]
    repo_root: str = ""
    run_dir: str = ""
    executor_cwd: str = ""
    proposed_changes_dir: str = ""
    proposed_changes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "max_rounds": self.max_rounds,
            "question": self.question,
            "files": self.files,
            "repo_root": self.repo_root,
            "run_dir": self.run_dir,
            "executor_cwd": self.executor_cwd,
            "proposed_changes_dir": self.proposed_changes_dir,
            "proposed_changes": self.proposed_changes,
        }
