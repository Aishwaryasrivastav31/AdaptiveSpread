import sqlite3
import json
import logging
from typing import Optional, Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_path: str = "adaptivespread.db"):
        self.db_path = db_path
        self._init_tables()

    def _get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)

    def _init_tables(self):
        """Initialize all database tables"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Table 1: RFQs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rfqs (
                    rfq_id TEXT PRIMARY KEY,
                    pair TEXT NOT NULL,
                    notional REAL NOT NULL,
                    tier TEXT NOT NULL,
                    context TEXT NOT NULL,
                    quote_spread REAL NOT NULL,
                    final_spread REAL NOT NULL,
                    mid_price REAL NOT NULL,
                    arm_idx INTEGER NOT NULL,
                    feature_vector TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)

            # Table 2: Outcomes
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS outcomes (
                    rfq_id TEXT PRIMARY KEY,
                    accepted INTEGER NOT NULL,
                    reward REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (rfq_id) REFERENCES rfqs(rfq_id)
                )
            """)

            # Table 3: Model States
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS model_states (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    state TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)

            # Table 4: Metrics
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)

            conn.commit()
            logger.info("✅ Database tables initialized successfully")

    def store_rfq(self, rfq_id: str, request: Dict, quote: Dict, context: Dict):
        """Store RFQ data"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT OR REPLACE INTO rfqs 
                (rfq_id, pair, notional, tier, context, quote_spread, final_spread, 
                 mid_price, arm_idx, feature_vector, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    rfq_id,
                    request.get("pair", ""),
                    request.get("notional", 0),
                    request.get("tier", ""),
                    json.dumps(context),
                    quote.get("spread_bps", 0),
                    quote.get("final_spread_bps", 0),
                    quote.get("mid_price", 0),
                    context.get("arm_idx", 0),
                    json.dumps(context.get("feature_vector", [])),
                    datetime.now().isoformat(),
                ),
            )

            conn.commit()
            logger.debug(f"✅ RFQ stored: {rfq_id}")

    def get_rfq(self, rfq_id: str) -> Optional[Dict]:
        """Get RFQ by ID"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM rfqs WHERE rfq_id = ?", (rfq_id,))
            row = cursor.fetchone()

            if row:
                columns = [
                    "rfq_id",
                    "pair",
                    "notional",
                    "tier",
                    "context",
                    "quote_spread",
                    "final_spread",
                    "mid_price",
                    "arm_idx",
                    "feature_vector",
                    "timestamp",
                ]
                result = dict(zip(columns, row))
                result["context"] = json.loads(result["context"])
                result["feature_vector"] = json.loads(result["feature_vector"])
                return result
            return None

    def get_all_rfqs(self, limit: int = 100) -> List[Dict]:
        """Get all RFQs"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM rfqs ORDER BY timestamp DESC LIMIT ?", (limit,)
            )
            rows = cursor.fetchall()

            columns = [
                "rfq_id",
                "pair",
                "notional",
                "tier",
                "context",
                "quote_spread",
                "final_spread",
                "mid_price",
                "arm_idx",
                "feature_vector",
                "timestamp",
            ]

            results = []
            for row in rows:
                result = dict(zip(columns, row))
                result["context"] = json.loads(result["context"])
                result["feature_vector"] = json.loads(result["feature_vector"])
                results.append(result)

            return results

    def store_outcome(self, rfq_id: str, accepted: bool, reward: float):
        """Store RFQ outcome"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT OR REPLACE INTO outcomes 
                (rfq_id, accepted, reward, timestamp)
                VALUES (?, ?, ?, ?)
            """,
                (rfq_id, 1 if accepted else 0, reward, datetime.now().isoformat()),
            )

            conn.commit()
            logger.debug(
                f"✅ Outcome stored: {rfq_id} - {'Accepted' if accepted else 'Rejected'}"
            )

    def get_outcome(self, rfq_id: str) -> Optional[Dict]:
        """Get outcome by RFQ ID"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM outcomes WHERE rfq_id = ?", (rfq_id,))
            row = cursor.fetchone()

            if row:
                return {
                    "rfq_id": row[0],
                    "accepted": bool(row[1]),
                    "reward": row[2],
                    "timestamp": row[3],
                }
            return None

    def store_model_state(self, state: Dict):
        """Store model state"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO model_states (state, timestamp)
                VALUES (?, ?)
            """,
                (json.dumps(state), datetime.now().isoformat()),
            )

            conn.commit()
            logger.debug("✅ Model state stored")

    def get_latest_model_state(self) -> Optional[Dict]:
        """Get latest model state"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT state FROM model_states ORDER BY timestamp DESC LIMIT 1"
            )
            row = cursor.fetchone()

            if row:
                return json.loads(row[0])
            return None

    def store_metric(self, name: str, value: float):
        """Store a metric"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO metrics (metric_name, metric_value, timestamp)
                VALUES (?, ?, ?)
            """,
                (name, value, datetime.now().isoformat()),
            )

            conn.commit()

    def get_metrics(self, name: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Get metrics"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            if name:
                cursor.execute(
                    """
                    SELECT metric_name, metric_value, timestamp 
                    FROM metrics 
                    WHERE metric_name = ?
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """,
                    (name, limit),
                )
            else:
                cursor.execute(
                    """
                    SELECT metric_name, metric_value, timestamp 
                    FROM metrics 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """,
                    (limit,),
                )

            rows = cursor.fetchall()
            return [
                {"metric_name": row[0], "metric_value": row[1], "timestamp": row[2]}
                for row in rows
            ]

    def get_summary_stats(self) -> Dict:
        """Get summary statistics"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Total RFQs
            cursor.execute("SELECT COUNT(*) FROM rfqs")
            total_rfqs = cursor.fetchone()[0]

            # Accepted RFQs
            cursor.execute("SELECT COUNT(*) FROM outcomes WHERE accepted = 1")
            accepted = cursor.fetchone()[0] or 0

            # Average reward
            cursor.execute("SELECT AVG(reward) FROM outcomes")
            avg_reward = cursor.fetchone()[0] or 0

            # Total revenue
            cursor.execute("SELECT SUM(reward) FROM outcomes")
            total_reward = cursor.fetchone()[0] or 0

            # Spread distribution
            cursor.execute("""
                SELECT quote_spread, COUNT(*) 
                FROM rfqs 
                GROUP BY quote_spread 
                ORDER BY quote_spread
            """)
            spread_dist = dict(cursor.fetchall())

            # Pair distribution
            cursor.execute("""
                SELECT pair, COUNT(*) 
                FROM rfqs 
                GROUP BY pair
            """)
            pair_dist = dict(cursor.fetchall())

            # Tier distribution
            cursor.execute("""
                SELECT tier, COUNT(*) 
                FROM rfqs 
                GROUP BY tier
            """)
            tier_dist = dict(cursor.fetchall())

            return {
                "total_rfqs": total_rfqs,
                "accepted": accepted,
                "rejected": total_rfqs - accepted,
                "acceptance_rate": accepted / max(total_rfqs, 1),
                "avg_reward": avg_reward,
                "total_reward": total_reward,
                "spread_distribution": spread_dist,
                "pair_distribution": pair_dist,
                "tier_distribution": tier_dist,
            }

    def clear_all(self):
        """Clear all data (for testing)"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM rfqs")
            cursor.execute("DELETE FROM outcomes")
            cursor.execute("DELETE FROM model_states")
            cursor.execute("DELETE FROM metrics")
            conn.commit()
            logger.warning("⚠️ All data cleared!")


# Global database instance
db = Database()


def init_db():
    """Initialize database (called on startup)"""
    db._init_tables()
    logger.info("✅ Database ready")
