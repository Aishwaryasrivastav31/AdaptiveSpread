# evaluation/evaluation.py
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
import logging
from datetime import datetime

from rfq.service import RFQService
from pricing.linucb import LinUCB
from simulation.ground_truth import true_accept_prob
from storage.database import db

logger = logging.getLogger(__name__)


class ModelEvaluator:
    """Real model evaluation with actual calculations"""

    def __init__(self):
        self.rfq_service = RFQService()
        self.spread_arms = [2, 5, 8, 12, 16, 20, 25, 35, 45]

    def evaluate_online_performance(self, n_rfqs: int = 100) -> Dict:
        """
        Evaluate model performance using actual RFQ history from database
        """
        # Get actual data from database
        rfqs = db.get_all_rfqs(limit=n_rfqs)

        if not rfqs:
            return {"error": "No data found in database", "total_rfqs": 0}

        # Calculate metrics from actual data
        accepted = 0
        total_reward = 0
        avg_spread = 0

        for rfq in rfqs:
            # Get outcome
            outcome = db.get_outcome(rfq["rfq_id"])
            if outcome:
                if outcome["accepted"]:
                    accepted += 1
                total_reward += outcome["reward"]
            avg_spread += rfq["final_spread"]

        total = len(rfqs)
        avg_spread = avg_spread / total if total > 0 else 0

        return {
            "total_rfqs": total,
            "accepted": accepted,
            "rejected": total - accepted,
            "acceptance_rate": accepted / total if total > 0 else 0,
            "avg_spread": avg_spread,
            "total_reward": total_reward,
            "avg_reward": total_reward / total if total > 0 else 0,
            "timestamp": datetime.now().isoformat(),
        }

    def evaluate_on_synthetic_data(self, n_rfqs: int = 1000) -> Dict:
        """
        Evaluate model on synthetic test data (for simulation mode)
        """
        from simulation.synthetic_rfq import SyntheticRFQGenerator
        from simulation.ground_truth import simulate_outcome

        generator = SyntheticRFQGenerator(seed=42)
        rfqs = generator.generate_batch(n_rfqs)

        total_reward = 0
        accepted_count = 0
        spread_choices = []
        optimal_spreads = []

        # Create a fresh bandit for testing
        test_bandit = LinUCB(arms=self.spread_arms, alpha=1.0, d=8)

        for rfq in rfqs:
            pair = rfq["pair"]
            notional = rfq["notional"]
            tier = rfq["tier"]

            # Get features
            x = self.rfq_service.feature_engine.get_feature_vector(pair, notional, tier)

            # Select spread
            arm_idx, spread = test_bandit.select_arm(x)
            spread_choices.append(spread)

            # Simulate outcome using ground truth
            volatility = self.rfq_service.feature_engine.get_volatility(pair)
            accepted = simulate_outcome(spread, tier, notional, volatility, pair)

            # Calculate reward
            reward = self.rfq_service.calculate_reward(spread, accepted)
            total_reward += reward

            if accepted:
                accepted_count += 1

            # Update model
            test_bandit.update(arm_idx, x, reward)

            # Calculate optimal spread for comparison
            optimal = self._find_optimal_spread(pair, tier, notional, volatility)
            optimal_spreads.append(optimal)

        # Calculate metrics
        avg_spread = np.mean(spread_choices)
        avg_optimal = np.mean(optimal_spreads)

        # Revenue capture ratio
        optimal_reward = 0
        for i, rfq in enumerate(rfqs):
            pair = rfq["pair"]
            tier = rfq["tier"]
            notional = rfq["notional"]
            volatility = self.rfq_service.feature_engine.get_volatility(pair)
            prob = true_accept_prob(
                optimal_spreads[i], tier, notional, volatility, pair
            )
            optimal_reward += optimal_spreads[i] * prob

        revenue_capture = (total_reward / optimal_reward) if optimal_reward > 0 else 0

        return {
            "total_rfqs": n_rfqs,
            "accepted_count": accepted_count,
            "acceptance_rate": accepted_count / n_rfqs,
            "avg_chosen_spread": avg_spread,
            "avg_optimal_spread": avg_optimal,
            "total_reward": total_reward,
            "optimal_reward": optimal_reward,
            "revenue_capture_ratio": min(revenue_capture, 1.0),  # Cap at 100%
            "spread_distribution": self._get_spread_distribution(spread_choices),
            "timestamp": datetime.now().isoformat(),
        }

    def _find_optimal_spread(
        self, pair: str, tier: str, notional: float, volatility: float
    ) -> float:
        """Find optimal spread that maximizes expected revenue"""
        spreads = np.arange(1, 50, 0.5)
        best_spread = spreads[0]
        best_value = -np.inf

        for spread in spreads:
            prob = true_accept_prob(spread, tier, notional, volatility, pair)
            expected_value = spread * prob
            if expected_value > best_value:
                best_value = expected_value
                best_spread = spread

        return best_spread

    def _get_spread_distribution(self, spreads: List[float]) -> Dict:
        """Get distribution of chosen spreads"""
        unique, counts = np.unique(spreads, return_counts=True)
        total = len(spreads)
        return {str(int(u)): c / total for u, c in zip(unique, counts)}

    def compare_with_baseline(self, n_rfqs: int = 100) -> Dict:
        """
        Compare LinUCB performance vs fixed spread baseline
        """
        from simulation.synthetic_rfq import SyntheticRFQGenerator
        from simulation.ground_truth import simulate_outcome

        generator = SyntheticRFQGenerator(seed=42)
        rfqs = generator.generate_batch(n_rfqs)

        # Fixed baseline: 10 bps
        baseline_spread = 10
        baseline_reward = 0

        # LinUCB
        linucb_reward = 0
        test_bandit = LinUCB(arms=self.spread_arms, alpha=1.0, d=8)

        for rfq in rfqs:
            pair = rfq["pair"]
            notional = rfq["notional"]
            tier = rfq["tier"]
            volatility = self.rfq_service.feature_engine.get_volatility(pair)

            # Baseline
            accepted = simulate_outcome(
                baseline_spread, tier, notional, volatility, pair
            )
            baseline_reward += self.rfq_service.calculate_reward(
                baseline_spread, accepted
            )

            # LinUCB
            x = self.rfq_service.feature_engine.get_feature_vector(pair, notional, tier)
            arm_idx, spread = test_bandit.select_arm(x)
            accepted = simulate_outcome(spread, tier, notional, volatility, pair)
            reward = self.rfq_service.calculate_reward(spread, accepted)
            linucb_reward += reward
            test_bandit.update(arm_idx, x, reward)

        uplift = (
            ((linucb_reward - baseline_reward) / baseline_reward)
            if baseline_reward > 0
            else 0
        )

        return {
            "n_rfqs": n_rfqs,
            "baseline_spread": baseline_spread,
            "baseline_reward": baseline_reward,
            "linucb_reward": linucb_reward,
            "revenue_uplift": uplift,
            "revenue_uplift_pct": uplift * 100,
            "timestamp": datetime.now().isoformat(),
        }


# ============= MAIN EVALUATION FUNCTIONS =============


def evaluate_model(mode: str = "synthetic", n_rfqs: int = 100) -> Dict:
    """
    Main evaluation function

    Args:
        mode: "synthetic" or "online"
        n_rfqs: Number of RFQs to evaluate

    Returns:
        Evaluation metrics
    """
    evaluator = ModelEvaluator()

    if mode == "online":
        return evaluator.evaluate_online_performance(n_rfqs)
    else:
        return evaluator.evaluate_on_synthetic_data(n_rfqs)


def compare_with_baseline(n_rfqs: int = 100) -> Dict:
    """Compare LinUCB vs fixed spread baseline"""
    evaluator = ModelEvaluator()
    return evaluator.compare_with_baseline(n_rfqs)


def get_detailed_report() -> Dict:
    """
    Generate comprehensive evaluation report
    """
    evaluator = ModelEvaluator()

    # Get metrics
    synthetic_metrics = evaluator.evaluate_on_synthetic_data(500)
    comparison = evaluator.compare_with_baseline(100)

    # Database stats
    db_stats = db.get_summary_stats()

    return {
        "synthetic_performance": synthetic_metrics,
        "baseline_comparison": comparison,
        "database_stats": db_stats,
        "timestamp": datetime.now().isoformat(),
    }


# ============= QUICK TEST =============

if __name__ == "__main__":
    print("=" * 60)
    print("📊 Model Evaluation")
    print("=" * 60)

    # Test 1: Synthetic evaluation
    print("\n[1] Evaluating on synthetic data...")
    result = evaluate_model(mode="synthetic", n_rfqs=100)
    print(f"✅ Acceptance Rate: {result['acceptance_rate'] * 100:.1f}%")
    print(f"✅ Revenue Capture: {result['revenue_capture_ratio'] * 100:.1f}%")

    # Test 2: Compare with baseline
    print("\n[2] Comparing with fixed baseline...")
    comparison = compare_with_baseline(n_rfqs=100)
    print(f"✅ Revenue Uplift: {comparison['revenue_uplift_pct']:.1f}%")

    # Test 3: Detailed report
    print("\n[3] Generating detailed report...")
    report = get_detailed_report()
    print(f"✅ Total RFQs in DB: {report['database_stats']['total_rfqs']}")
    print(
        f"✅ Acceptance Rate: {report['database_stats']['acceptance_rate'] * 100:.1f}%"
    )

    print("\n" + "=" * 60)
    print("✅ Evaluation complete!")
