from __future__ import annotations

import re
from pathlib import Path
from typing import List, Tuple, Dict, Any

from rich.console import Console
from rich.table import Table

console = Console()

# Define reasonable time thresholds (in seconds) for each step.
DEFAULT_THRESHOLDS = {
    "Preflight checks": 5.0,
    "Parsing docker-compose file": 1.0,
    "Allocating ports": 0.5,
    "Setting up networking": 10.0,  # Can be slow due to sudo/scripts
    "Generating environment variables": 0.5,
    "Applying /etc/hosts fallback": 2.0,
    "Starting Caddy reverse-proxy": 5.0,
    "Starting application containers": 30.0,  # Can be very slow if images are pulled
    "Configuring reverse-proxy": 2.0,
}


class PerformanceAnalyzer:
    """Analyzes DynaDock startup performance based on timer logs."""

    def __init__(self, project_dir: Path, thresholds: Dict[str, float] | None = None):
        self.project_dir = project_dir
        self.log_file = self.project_dir / ".dynadock" / "dynadock.log"
        self.thresholds = thresholds or DEFAULT_THRESHOLDS
        self.timer_log_pattern = re.compile(
            r"TIMER: Step '(.+?)' finished in ([\d.]+)s"
        )
        self.session_start_pattern = re.compile(r"DynaDock CLI started")

    def get_latest_session_logs(self) -> List[str]:
        """Extracts log lines from the most recent 'up' command session."""
        if not self.log_file.exists():
            return []

        with open(self.log_file, "r") as f:
            lines = f.readlines()

        session_starts = [
            i for i, line in enumerate(lines) if self.session_start_pattern.search(line)
        ]
        if not session_starts:
            return []

        latest_session_start = session_starts[-1]
        return lines[latest_session_start:]

    def parse_timings(self) -> List[Tuple[str, float]]:
        """Parses step timings from the latest session logs."""
        session_logs = self.get_latest_session_logs()
        timings = []
        for line in session_logs:
            match = self.timer_log_pattern.search(line)
            if match:
                step_name = match.group(1)
                duration = float(match.group(2))
                timings.append((step_name, duration))
        return timings

    def analyze(self) -> Dict[str, Any]:
        """Analyzes timings and identifies bottlenecks."""
        timings = self.parse_timings()
        bottlenecks = []
        recommendations = []

        for step, duration in timings:
            base_step = next(
                (key for key in self.thresholds if step.startswith(key)), None
            )

            if base_step and duration > self.thresholds[base_step]:
                bottlenecks.append(
                    {
                        "step": step,
                        "duration": duration,
                        "threshold": self.thresholds[base_step],
                    }
                )

        if bottlenecks:
            recommendations = self._generate_recommendations(bottlenecks)

        return {
            "timings": timings,
            "bottlenecks": bottlenecks,
            "recommendations": recommendations,
        }

    def _generate_recommendations(self, bottlenecks: List[Dict]) -> List[str]:
        """Generates repair/optimization recommendations based on bottlenecks."""
        recs = []
        for bottleneck in bottlenecks:
            step = bottleneck["step"]
            if "Starting application containers" in step:
                recs.append(
                    "Uruchamianie kontenerów trwa długo. Spróbuj wcześniej pobrać obrazy poleceniem 'docker pull' lub wyczyść stare obrazy i wolumeny za pomocą 'docker system prune'."
                )
            elif "Setting up networking" in step:
                recs.append(
                    "Konfiguracja sieci trwa długo, co może być spowodowane przez skrypty systemowe. Jeśli problem się powtarza, rozważ użycie flagi '--manage-hosts' dla prostszej i szybszej konfiguracji."
                )
            elif "Preflight checks" in step:
                recs.append(
                    "Sprawdzanie wstępne trwa dłużej niż oczekiwano. Może to wskazywać na powolne działanie demona Docker. Sprawdź 'docker info' w poszukiwaniu ostrzeżeń."
                )

        return sorted(list(set(recs)))

    def display_report(self, analysis: Dict[str, Any]) -> None:
        """Displays a performance analysis report to the console."""
        if not analysis["bottlenecks"]:
            console.print(
                "\n[green]✓ Analiza wydajności zakończona. Nie wykryto znaczących opóźnień.[/green]"
            )
            return

        console.print("\n[bold yellow]🚀 Raport Analizy Wydajności[/bold yellow]")

        table = Table(title="Wykryte Wąskie Gardła")
        table.add_column("Krok", style="cyan")
        table.add_column("Rzeczywisty Czas", style="magenta")
        table.add_column("Próg", style="green")
        table.add_column("Przekroczono o", style="red")

        for bottleneck in analysis["bottlenecks"]:
            exceeded_by = bottleneck["duration"] - bottleneck["threshold"]
            table.add_row(
                bottleneck["step"],
                f"{bottleneck['duration']:.2f}s",
                f"{bottleneck['threshold']:.2f}s",
                f"{exceeded_by:.2f}s",
            )

        console.print(table)

        if analysis["recommendations"]:
            console.print("\n[bold blue]💡 Rekomendacje[/bold blue]")
            for rec in analysis["recommendations"]:
                console.print(f"  - {rec}")
