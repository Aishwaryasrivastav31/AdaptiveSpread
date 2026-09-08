import numpy as np
from typing import List, Dict, Tuple
import logging
import pickle
import os

logger = logging.getLogger(__name__)


class LinUCB:
    def __init__(
        self, arms: List[float], alpha: float = 1.0, d: int = 9, ridge: float = 1.0
    ):
        self.arms = arms
        self.n_arms = len(arms)
        self.alpha = alpha
        self.d = d
        self.ridge = ridge
        self.A = [ridge * np.eye(d) for _ in range(self.n_arms)]
        self.b = [np.zeros(d) for _ in range(self.n_arms)]
        self.theta = [np.zeros(d) for _ in range(self.n_arms)]
        self.history = []
        self.total_reward = 0
        self.n_pulls = 0
        self._update_all_thetas()

    def _update_theta(self, arm_idx: int):
        try:
            self.theta[arm_idx] = np.linalg.inv(self.A[arm_idx]) @ self.b[arm_idx]
        except:
            self.theta[arm_idx] = np.linalg.pinv(self.A[arm_idx]) @ self.b[arm_idx]

    def _update_all_thetas(self):
        for i in range(self.n_arms):
            self._update_theta(i)

    def get_scores(self, x: np.ndarray) -> np.ndarray:
        scores = np.zeros(self.n_arms)
        for i in range(self.n_arms):
            mean = self.theta[i] @ x
            A_inv = np.linalg.inv(self.A[i])
            uncertainty = self.alpha * np.sqrt(x @ A_inv @ x)
            scores[i] = mean + uncertainty
        return scores

    def select_arm(self, x: np.ndarray) -> Tuple[int, float]:
        scores = self.get_scores(x)
        arm_idx = np.argmax(scores)
        self.history.append(
            {"context": x.copy(), "arm_idx": arm_idx, "spread": self.arms[arm_idx]}
        )
        self.n_pulls += 1
        return arm_idx, self.arms[arm_idx]

    def update(self, arm_idx: int, x: np.ndarray, reward: float):
        reward = np.clip(reward, 0, 1)
        self.A[arm_idx] += np.outer(x, x)
        self.b[arm_idx] += reward * x
        self._update_theta(arm_idx)
        self.total_reward += reward
        if self.history:
            self.history[-1]["reward"] = reward

    def get_state(self) -> Dict:
        return {
            "A": [a.tolist() for a in self.A],
            "b": [b.tolist() for b in self.b],
            "theta": [t.tolist() for t in self.theta],
            "arms": self.arms,
            "alpha": self.alpha,
            "d": self.d,
            "ridge": self.ridge,
            "total_reward": self.total_reward,
            "n_pulls": self.n_pulls,
        }

    def load_state(self, state: Dict):
        self.A = [np.array(a) for a in state["A"]]
        self.b = [np.array(b) for b in state["b"]]
        self.theta = [np.array(t) for t in state["theta"]]
        self.arms = state["arms"]
        self.alpha = state["alpha"]
        self.d = state["d"]
        self.ridge = state["ridge"]
        self.total_reward = state["total_reward"]
        self.n_pulls = state["n_pulls"]

    def save_to_file(self, filepath: str):
        with open(filepath, "wb") as f:
            pickle.dump(self.get_state(), f)

    def load_from_file(self, filepath: str) -> bool:
        if os.path.exists(filepath):
            with open(filepath, "rb") as f:
                self.load_state(pickle.load(f))
            return True
        return False
