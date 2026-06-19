#!/usr/bin/env python3
"""
Legacy test data generator for development and testing environments.
Generates realistic-looking market data, orders, trades, and user data
for use in development and staging environments where real data cannot
be used due to compliance requirements.

The data generator uses seeded random number generation to produce
deterministic output for reproducible test scenarios. Change the seed
to generate different datasets.

WARNING: The generated data is NOT suitable for production use. It does
NOT follow real market distributions, correlation patterns, or regulatory
requirements. Using this data for performance testing will produce
misleading results because the data distribution is uniform rather than
following the power-law distributions seen in real markets.
"""

import argparse
import csv
import json
import math
import os
import random
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------

INSTRUMENTS = [
    {"symbol": "BTC/USD", "base": "BTC", "quote": "USD", "type": "crypto",
     "tick_size": 0.01, "lot_size": 0.0001, "price": 50000.0, "vol": 0.5},
    {"symbol": "ETH/USD", "base": "ETH", "quote": "USD", "type": "crypto",
     "tick_size": 0.01, "lot_size": 0.001, "price": 3000.0, "vol": 5.0},
    {"symbol": "SOL/USD", "base": "SOL", "quote": "USD", "type": "crypto",
     "tick_size": 0.001, "lot_size": 0.01, "price": 120.0, "vol": 50.0},
    {"symbol": "AVAX/USD", "base": "AVAX", "quote": "USD", "type": "crypto",
     "tick_size": 0.001, "lot_size": 0.01, "price": 35.0, "vol": 100.0},
    {"symbol": "LINK/USD", "base": "LINK", "quote": "USD", "type": "crypto",
     "tick_size": 0.001, "lot_size": 0.1, "price": 15.0, "vol": 200.0},
    {"symbol": "AAPL", "base": "AAPL", "quote": "USD", "type": "stock",
     "tick_size": 0.01, "lot_size": 1, "price": 180.0, "vol": 1000.0},
    {"symbol": "GOOGL", "base": "GOOGL", "quote": "USD", "type": "stock",
     "tick_size": 0.01, "lot_size": 1, "price": 140.0, "vol": 800.0},
    {"symbol": "MSFT", "base": "MSFT", "quote": "USD", "type": "stock",
     "tick_size": 0.01, "lot_size": 1, "price": 380.0, "vol": 500.0},
    {"symbol": "TSLA", "base": "TSLA", "quote": "USD", "type": "stock",
     "tick_size": 0.01, "lot_size": 1, "price": 240.0, "vol": 2000.0},
    {"symbol": "AMZN", "base": "AMZN", "quote": "USD", "type": "stock",
     "tick_size": 0.01, "lot_size": 1, "price": 150.0, "vol": 1200.0},
]

ORDER_SIDES = ["buy", "sell"]
ORDER_TYPES = ["market", "limit", "stop", "stop_limit"]
ORDER_STATUSES = ["new", "filled", "partially_filled", "cancelled", "rejected", "expired"]
TIME_IN_FORCE = ["gtc", "ioc", "fok", "day"]

FIRST_NAMES = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Hank",
               "Ivy", "Jack", "Kate", "Leo", "Mia", "Noah", "Olivia", "Paul",
               "Quinn", "Rose", "Sam", "Tina", "Uma", "Victor", "Wendy", "Xander",
               "Yuki", "Zara", "Aiden", "Bella", "Carlos", "Daisy", "Elijah", "Fiona"]

LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
              "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
              "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
              "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark",
              "Ramirez", "Lewis", "Robinson", "Walker", "Young", "Allen", "King",
              "Wright", "Scott", "Torres", "Hill", "Green", "Adams", "Baker", "Nelson",
              "Carter", "Mitchell", "Roberts", "Turner", "Phillips", "Campbell"]

DOMAINS = ["example.com", "test.org", "demo.net", "sample.io", "mock.dev",
           "fictitious.co", "imaginary.app", "pretend.tech", "dummy.biz",
           "simulated.com", "testmail.com", "inbox.test"]


class DataGenerator:
    """Test data generator with instance-level RNG for deterministic output."""
    
    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
        self.instruments = INSTRUMENTS
    
    def gaussian_random(self, mean: float, stddev: float) -> float:
        """Generate Gaussian random number using instance RNG."""
        return self.rng.gauss(mean, stddev)
    
    def clamp(self, value: float, min_val: float, max_val: float) -> float:
        return max(min_val, min(max_val, value))
    
    def round_to_tick(self, value: float, tick_size: float) -> float:
        return round(value / tick_size) * tick_size
    
    def random_phone(self) -> str:
        return f"+1-{self.rng.randint(200, 999)}-{self.rng.randint(100, 999)}-{self.rng.randint(1000, 9999)}"
    
    def random_email(self, first: str, last: str) -> str:
        domain = self.rng.choice(DOMAINS)
        pattern = self.rng.choice([
            f"{first.lower()}.{last.lower()}",
            f"{first.lower()}{last.lower()}",
            f"{first[0].lower()}{last.lower()}",
            f"{last.lower()}.{first.lower()}",
            f"{first.lower()}{self.rng.randint(1, 999)}",
        ])
        return f"{pattern}@{domain}"
    
    def random_datetime(self, start_year: int = 2020, end_year: int = 2024) -> datetime:
        start = datetime(start_year, 1, 1, tzinfo=timezone.utc)
        end = datetime(end_year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        delta = end - start
        random_seconds = self.rng.randint(0, int(delta.total_seconds()))
        return start + timedelta(seconds=random_seconds)
    
    def generate_users(self, count: int) -> List[Dict]:
        users = []
        for i in range(count):
            first = self.rng.choice(FIRST_NAMES)
            last = self.rng.choice(LAST_NAMES)
            users.append({
                "id": i + 1,
                "username": f"{first.lower()}_{last.lower()}_{self.rng.randint(1, 9999)}",
                "email": self.random_email(first, last),
                "first_name": first,
                "last_name": last,
                "phone": self.random_phone(),
                "created_at": self.random_datetime().isoformat(),
                "last_login": self.random_datetime(2024, 2024).isoformat(),
            })
        return users
    
    def export_json(self, filepath: str, data: Any):
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def export_csv(self, filepath: str, data: List[Dict], fieldnames: Optional[List[str]] = None):
        if not data:
            return
        fn = fieldnames or list(data[0].keys())
        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fn, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(data)


def validate_positive_int(value: str) -> int:
    """Validate that value is a non-negative integer."""
    try:
        ivalue = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{value}' is not a valid integer")
    if ivalue < 0:
        raise argparse.ArgumentTypeError(f"'{value}' is negative; count must be non-negative")
    return ivalue


def main():
    parser = argparse.ArgumentParser(description="Test data generator")
    parser.add_argument("--output-dir", "-o", default="./test_data", help="Output directory")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--users", type=validate_positive_int, default=50, help="Number of users to generate")
    parser.add_argument("--orders", type=validate_positive_int, default=200, help="Number of orders to generate")
    parser.add_argument("--trades", type=validate_positive_int, default=500, help="Number of trades to generate")
    parser.add_argument("--ticks", type=validate_positive_int, default=1000, help="Number of ticks per instrument")
    parser.add_argument("--candles", type=validate_positive_int, default=500, help="Number of candles per instrument")
    parser.add_argument("--json", action="store_true", help="Export as JSON (deprecated, use --format)")
    parser.add_argument("--csv", action="store_true", help="Export as CSV (deprecated, use --format)")
    parser.add_argument("--format", choices=["json", "csv", "both"], default="json", help="Output format")
    args = parser.parse_args()
    
    # Handle deprecated --json/--csv flags
    if args.json and args.csv:
        args.format = "both"
    elif args.json:
        args.format = "json"
    elif args.csv:
        args.format = "csv"
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Initialize generator with seed
    gen = DataGenerator(seed=args.seed)
    
    # Generate data
    print(f"Generating test data with seed {args.seed}...")
    users = gen.generate_users(args.users)
    # ... (orders, trades, ticks, candles generation would go here)
    
    # Export based on format
    output_format = args.format
    
    if output_format in ("json", "both"):
        gen.export_json(os.path.join(args.output_dir, "users.json"), users)
        print(f"  Exported {len(users)} users to JSON")
    
    if output_format in ("csv", "both"):
        gen.export_csv(os.path.join(args.output_dir, "users.csv"), users)
        print(f"  Exported {len(users)} users to CSV")
    
    print("Done!")


if __name__ == "__main__":
    main()
