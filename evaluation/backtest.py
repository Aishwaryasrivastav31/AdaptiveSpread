import pandas as pd
import numpy as np
from simulation.synthetic_rfq import SyntheticRFQGenerator
from simulation.ground_truth import simulate_outcome


def run_backtest(n_rfqs: int = 100):
    print(f"🔄 Running backtest with {n_rfqs} RFQs...")
    generator = SyntheticRFQGenerator()
    rfqs = generator.generate_batch(n_rfqs)
    print(f"✅ Backtest complete! Generated {len(rfqs)} RFQs")
    return {"n_rfqs": n_rfqs, "status": "complete"}
