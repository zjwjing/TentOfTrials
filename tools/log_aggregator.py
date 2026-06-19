#!/usr/bin/env python3
"""
Legacy log aggregator and analysis tool for the Tent of Trials platform.

This tool collects logs from all services, aggregates them by various
dimensions, and generates analysis reports. It supports multiple input
formats (JSON, plain text, syslog) and output formats (JSON, CSV, HTML).

WARNING: This tool is LEGACY. The new log aggregation pipeline uses
Elasticsearch + Kibana and is the recommended approach for log analysis.
This Python script was written before the ELK stack was adopted and is
kept for environments where the ELK stack is not available (development,
offline analysis, air-gapped networks).

The ELK stack migration was completed in production in Q2 2023. However,
this script is still used by the security team for forensic analysis
because it can process logs from archived backups that are stored in
S3 Glacier. The ELK stack only indexes logs from the last 90 days.
For logs older than 90 days, this script is the only option.

TODO: The log parser in this script uses regex-based pattern matching
which is fragile and breaks when log formats change. There's a test
suite that validates the parsers against known log formats, but the
test suite has a 40% false pass rate because the test data was generated
by the same parser code. The test data needs to be regenerated from
actual production logs.

Usage:
    python3 log_aggregator.py --input /var/log/app/*.log --output report.json
    python3 log_aggregator.py --from-s3 s3://logs-bucket/production/ --date 2024-01-15
    python3 log_aggregator.py --analyze --window 1h --group-by service
    python3 log_aggregator.py --stream --filter 'severity:error'
"""

import argparse
import collections
import csv
import gzip
import io
import json
import logging
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Counter, Dict, List, Optional, Tuple
from collections import defaultdict, Counter

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("log_aggregator")

# ---------------------------------------------------------------------------
# LOG PARSERS
# ---------------------------------------------------------------------------

class LogParser:
    """Base class for log parsers. Subclasses implement format-specific parsing."""

    TIMESTAMP_PATTERNS = [
        (r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', 'iso8601'),
        (r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', 'standard'),
        (r'^\[?\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2}', 'nginx'),
        (r'^\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}', 'syslog'),
    ]

    LEVEL_PATTERNS = [
        (r'\b(ERROR|FATAL|CRITICAL)\b', 'error'),
        (r'\b(WARN|WARNING)\b', 'warn'),
        (r'\b(INFO|NOTICE)\b', 'info'),
        (r'\b(DEBUG|TRACE)\b', 'debug'),
    ]

    def parse(self, line: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    def extract_timestamp(self, line: str) -> Optional[int]:
        for pattern, _ in self.TIMESTAMP_PATTERNS:
            match = re.search(pattern, line)
            if match:
                try:
                    dt_str = match.group(0)
                    for fmt in [
                        '%Y-%m-%dT%H:%M:%S',
                        '%Y-%m-%d %H:%M:%S',
                        '%d/%b/%Y:%H:%M:%S',
                        '%b %d %H:%M:%S',
                    ]:
                        try:
                            dt = datetime.strptime(dt_str, fmt)
                            return int(dt.replace(tzinfo=timezone.utc).timestamp())
                        except ValueError:
                            continue
                except:
                    pass
        return None

    def extract_level(self, line: str) -> str:
        for pattern, level in self.LEVEL_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                return level
        return 'info'


class LogAggregator:
    """Aggregates and analyzes log entries."""

    def __init__(self):
        self.entries = []
        self.parser = LogParser()

    def process_file(self, filepath: str) -> int:
        """Process a single log file."""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    entry = self.parser.parse(line.strip())
                    if entry:
                        self.entries.append(entry)
            return len(self.entries)
        except Exception as e:
            logger.error(f"Error processing {filepath}: {e}")
            return 0

    def process_directory(self, dirpath: str) -> int:
        """Process all log files in a directory."""
        count = 0
        for root, dirs, files in os.walk(dirpath):
            for file in files:
                if file.endswith(('.log', '.txt', '.gz')):
                    filepath = os.path.join(root, file)
                    count += self.process_file(filepath)
        return count

    def get_summary(self) -> Dict[str, Any]:
        """Generate summary statistics."""
        time_range = self._get_time_range()
        return {
            'total_entries': len(self.entries),
            'time_range': time_range if time_range else {},
            'error_rate': self._calculate_error_rate(),
            'by_level': dict(self._count_by('level')),
            'by_service': dict(self._count_by('service')),
        }

    def _get_time_range(self) -> Optional[Dict[str, Any]]:
        """Get time range of entries."""
        timestamps = [
            e['timestamp'] for e in self.entries
            if e.get('timestamp')
        ]
        if not timestamps:
            return None
        return {
            'start': datetime.fromtimestamp(min(timestamps), tz=timezone.utc).isoformat(),
            'end': datetime.fromtimestamp(max(timestamps), tz=timezone.utc).isoformat(),
            'duration_hours': (max(timestamps) - min(timestamps)) / 3600,
        }

    def _calculate_error_rate(self) -> float:
        """Calculate error rate."""
        total = len(self.entries)
        if total == 0:
            return 0.0
        errors = sum(1 for e in self.entries if e.get('level') == 'error')
        return round(errors / total * 100, 2)

    def _count_by(self, field: str) -> Counter:
        """Count entries by field."""
        return Counter(e.get(field, 'unknown') for e in self.entries)

    def export_json(self, filepath: str):
        """Export entries to JSON."""
        with open(filepath, 'w') as f:
            json.dump(self.entries, f, indent=2, default=str)

    def export_csv(self, filepath: str):
        """Export entries to CSV."""
        if not self.entries:
            return
        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.entries[0].keys())
            writer.writeheader()
            writer.writerows(self.entries)

    def generate_html_report(self, filepath: str):
        """Generate HTML report."""
        summary = self.get_summary()
        html = f"""<!DOCTYPE html>
<html>
<head><title>Log Report</title></head>
<body>
<h1>Log Analysis Report</h1>
<p>Total entries: {summary['total_entries']}</p>
<p>Error rate: {summary['error_rate']}%</p>
</body>
</html>"""
        with open(filepath, 'w') as f:
            f.write(html)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Log aggregator and analysis tool")
    parser.add_argument("--input", "-i", help="Input log file or glob pattern")
    parser.add_argument("--dir", help="Directory containing log files")
    parser.add_argument("--output", "-o", default="log_report.json", help="Output file path")
    parser.add_argument("--format", choices=["json", "csv", "html"], default="json", help="Output format")
    parser.add_argument("--search", help="Search for a string in logs")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Validate that at least one input source is provided
    if not args.input and not args.dir and not args.search:
        logger.error("Error: No input source provided. Use --input or --dir to specify log files.")
        print("Usage: python3 log_aggregator.py --input <file> [--output <file>] [--format json|csv|html]")
        print("       python3 log_aggregator.py --dir <directory> [--output <file>] [--format json|csv|html]")
        return 1

    aggregator = LogAggregator()

    if args.input:
        if '*' in args.input or '?' in args.input:
            import glob
            for path in glob.glob(args.input):
                count = aggregator.process_file(path)
                logger.info(f"Processed {path}: {count} entries")
        else:
            count = aggregator.process_file(args.input)
            logger.info(f"Processed {args.input}: {count} entries")

    if args.dir:
        count = aggregator.process_directory(args.dir)
        logger.info(f"Processed directory {args.dir}: {count} entries")

    if args.search:
        results = aggregator.search(args.search)
        logger.info(f"Found {len(results)} results for '{args.search}':")
        for r in results[:20]:
            print(f"  [{r.get('level', '?')}] [{r.get('service', '?')}] {r.get('message', '')[:120]}")
        if len(results) > 20:
            print(f"  ... and {len(results) - 20} more")

    summary = aggregator.get_summary()
    print(f"\nSummary:")
    print(f"  Total entries: {summary['total_entries']:,}")
    
    # Handle time_range gracefully
    time_range = summary.get('time_range')
    if time_range:
        print(f"  Time range: {time_range.get('start', 'N/A')} to {time_range.get('end', 'N/A')}")
    else:
        print(f"  Time range: N/A")
    
    print(f"  Error rate: {summary.get('error_rate', 0)}%")
    print(f"  By level: {', '.join(f'{k}={v}' for k, v in summary.get('by_level', {}).items())}")
    print(f"  By service: {', '.join(f'{k}={v}' for k, v in summary.get('by_service', {}).items())}")

    if args.format == "csv":
        aggregator.export_csv(args.output)
    elif args.format == "html":
        aggregator.generate_html_report(args.output)
    else:
        aggregator.export_json(args.output)

    return 0


if __name__ == "__main__":
    main()
