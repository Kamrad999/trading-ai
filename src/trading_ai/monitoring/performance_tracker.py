"""
Real pipeline performance tracking for Trading AI.

Implements true per-stage latency tracking, feed fetch latency, validation hit ratio,
duplicate rejection ratio, signal throughput, error rates, and state save latency.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

from ..infrastructure.config import config
from ..infrastructure.logging import get_logger
from ..infrastructure.state_manager import StateManager


class PerformanceTracker:
    """Real pipeline performance tracking engine."""
    
    def __init__(self) -> None:
        """Initialize performance tracker with metrics storage."""
        self.logger = get_logger("performance_tracker")
        self.state_manager = StateManager()
        
        # Metrics storage
        self.stage_metrics: Dict[str, List[float]] = defaultdict(list)
        self.pipeline_metrics: List[Dict[str, Any]] = []
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.feed_metrics: Dict[str, List[float]] = defaultdict(list)
        
        # Performance windows
        self.metrics_window = 1000  # Keep last 1000 pipeline runs
        self.stage_window = 100      # Keep last 100 stage runs per stage
        
        # Current pipeline run tracking
        self.current_pipeline_start: Optional[float] = None
        self.current_stage_start: Optional[str] = None
        self.current_stage_metrics: Dict[str, Any] = {}
        
        # Load historical metrics
        self._load_performance_state()
    
    def _load_performance_state(self) -> None:
        """Load performance metrics from persistent storage."""
        try:
            state = self.state_manager.load_state()
            perf_state = state.get("performance_tracker", {})
            
            self.stage_metrics = defaultdict(list, perf_state.get("stage_metrics", {}))
            self.pipeline_metrics = perf_state.get("pipeline_metrics", [])
            self.error_counts = defaultdict(int, perf_state.get("error_counts", {}))
            self.feed_metrics = defaultdict(list, perf_state.get("feed_metrics", {}))
            
            # Trim to window sizes
            self._trim_metrics()
            
            self.logger.info(
                f"Loaded performance state: {len(self.pipeline_metrics)} pipeline runs, "
                f"{sum(len(m) for m in self.stage_metrics.values())} stage metrics"
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to load performance state: {e}")
    
    def _trim_metrics(self) -> None:
        """Trim metrics to maintain window sizes."""
        # Trim pipeline metrics
        if len(self.pipeline_metrics) > self.metrics_window:
            self.pipeline_metrics = self.pipeline_metrics[-self.metrics_window:]
        
        # Trim stage metrics
        for stage_name in self.stage_metrics:
            if len(self.stage_metrics[stage_name]) > self.stage_window:
                self.stage_metrics[stage_name] = self.stage_metrics[stage_name][-self.stage_window:]
        
        # Trim feed metrics
        for feed_name in self.feed_metrics:
            if len(self.feed_metrics[feed_name]) > self.stage_window:
                self.feed_metrics[feed_name] = self.feed_metrics[feed_name][-self.stage_window:]
    
    def start_pipeline_tracking(self, pipeline_id: str) -> None:
        """Start tracking a new pipeline run."""
        self.current_pipeline_start = time.time()
        self.current_stage_metrics = {
            "pipeline_id": pipeline_id,
            "start_time": datetime.now(timezone.utc),
            "stages": {},
            "errors": []
        }
        
        self.logger.debug(f"Started tracking pipeline: {pipeline_id}")
    
    def start_stage_tracking(self, stage_name: str) -> None:
        """Start tracking a pipeline stage."""
        self.current_stage_start = stage_name
        stage_start_time = time.time()
        
        self.current_stage_metrics["stages"][stage_name] = {
            "start_time": stage_start_time,
            "start_datetime": datetime.now(timezone.utc)
        }
        
        self.logger.debug(f"Started tracking stage: {stage_name}")
    
    def end_stage_tracking(self, stage_name: str, success: bool, error_message: Optional[str] = None) -> float:
        """End tracking a pipeline stage and return latency."""
        if not self.current_stage_start or self.current_stage_start != stage_name:
            self.logger.warning(f"Stage tracking mismatch: expected {self.current_stage_start}, got {stage_name}")
            return 0.0
        
        stage_end_time = time.time()
        
        if stage_name in self.current_stage_metrics["stages"]:
            stage_start_time = self.current_stage_metrics["stages"][stage_name]["start_time"]
            latency_ms = (stage_end_time - stage_start_time) * 1000
            
            # Store stage metrics
            self.stage_metrics[stage_name].append(latency_ms)
            
            # Update current stage metrics
            self.current_stage_metrics["stages"][stage_name].update({
                "end_time": stage_end_time,
                "end_datetime": datetime.now(timezone.utc),
                "latency_ms": latency_ms,
                "success": success,
                "error_message": error_message
            })
            
            # Track errors
            if not success:
                self.error_counts[stage_name] += 1
                self.current_stage_metrics["errors"].append({
                    "stage": stage_name,
                    "error": error_message,
                    "timestamp": datetime.now(timezone.utc)
                })
            
            self.logger.debug(f"Stage {stage_name} completed: {latency_ms:.2f}ms, success={success}")
            return latency_ms
        
        return 0.0
    
    def record_feed_latency(self, feed_url: str, latency_ms: float, success: bool) -> None:
        """Record RSS feed fetch latency."""
        feed_name = feed_url.split("/")[-1]  # Extract feed name from URL
        self.feed_metrics[feed_name].append(latency_ms)
        
        if not success:
            self.error_counts[f"feed_{feed_name}"] += 1
        
        self.logger.debug(f"Feed {feed_name}: {latency_ms:.2f}ms, success={success}")
    
    def record_validation_metrics(self, total_articles: int, valid_articles: int, rejected_articles: int) -> None:
        """Record validation metrics."""
        validation_hit_ratio = valid_articles / total_articles if total_articles > 0 else 0
        rejection_ratio = rejected_articles / total_articles if total_articles > 0 else 0
        
        if "validation" not in self.current_stage_metrics["stages"]:
            self.current_stage_metrics["stages"]["validation"] = {}
        
        self.current_stage_metrics["stages"]["validation"].update({
            "total_articles": total_articles,
            "valid_articles": valid_articles,
            "rejected_articles": rejected_articles,
            "hit_ratio": validation_hit_ratio,
            "rejection_ratio": rejection_ratio
        })
        
        self.logger.info(
            f"Validation metrics: {valid_articles}/{total_articles} valid "
            f"({validation_hit_ratio:.3f} hit ratio)"
        )
    
    def record_signal_metrics(self, total_signals: int, buy_signals: int, sell_signals: int, avg_confidence: float) -> None:
        """Record signal generation metrics."""
        if "signals" not in self.current_stage_metrics["stages"]:
            self.current_stage_metrics["stages"]["signals"] = {}
        
        self.current_stage_metrics["stages"]["signals"].update({
            "total_signals": total_signals,
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
            "avg_confidence": avg_confidence,
            "throughput": total_signals / 60  # Signals per minute (assuming 1 minute pipeline)
        })
        
        self.logger.info(
            f"Signal metrics: {total_signals} signals ({buy_signals} buy, {sell_signals} sell), "
            f"avg confidence: {avg_confidence:.3f}"
        )
    
    def record_risk_metrics(self, total_assessed: int, approved_signals: int, avg_risk_score: float) -> None:
        """Record risk assessment metrics."""
        approval_ratio = approved_signals / total_assessed if total_assessed > 0 else 0
        
        if "risk" not in self.current_stage_metrics["stages"]:
            self.current_stage_metrics["stages"]["risk"] = {}
        
        self.current_stage_metrics["stages"]["risk"].update({
            "total_assessed": total_assessed,
            "approved_signals": approved_signals,
            "rejected_signals": total_assessed - approved_signals,
            "approval_ratio": approval_ratio,
            "avg_risk_score": avg_risk_score
        })
        
        self.logger.info(
            f"Risk metrics: {approved_signals}/{total_assessed} approved "
            f"({approval_ratio:.3f} approval ratio)"
        )
    
    def record_state_metrics(self, save_latency_ms: float, state_size_bytes: int) -> None:
        """Record state persistence metrics."""
        if "state" not in self.current_stage_metrics["stages"]:
            self.current_stage_metrics["stages"]["state"] = {}
        
        self.current_stage_metrics["stages"]["state"].update({
            "save_latency_ms": save_latency_ms,
            "state_size_bytes": state_size_bytes,
            "save_rate_mbps": (state_size_bytes / 1024 / 1024) / (save_latency_ms / 1000) if save_latency_ms > 0 else 0
        })
        
        self.logger.debug(f"State metrics: {save_latency_ms:.2f}ms, {state_size_bytes} bytes")
    
    def end_pipeline_tracking(self, articles_processed: int, signals_generated: int, orders_sent: int, alerts_sent: int) -> Dict[str, Any]:
        """End tracking a pipeline run and return metrics."""
        if not self.current_pipeline_start:
            self.logger.warning("No active pipeline tracking to end")
            return {}
        
        pipeline_end_time = time.time()
        total_latency_ms = (pipeline_end_time - self.current_pipeline_start) * 1000
        
        # Complete pipeline metrics
        pipeline_metrics = {
            "pipeline_id": self.current_stage_metrics["pipeline_id"],
            "start_time": self.current_stage_metrics["start_time"],
            "end_time": datetime.now(timezone.utc),
            "total_latency_ms": total_latency_ms,
            "articles_processed": articles_processed,
            "signals_generated": signals_generated,
            "orders_sent": orders_sent,
            "alerts_sent": alerts_sent,
            "stages": self.current_stage_metrics["stages"],
            "errors": self.current_stage_metrics["errors"],
            "throughput_articles_per_sec": articles_processed / (total_latency_ms / 1000) if total_latency_ms > 0 else 0,
            "throughput_signals_per_sec": signals_generated / (total_latency_ms / 1000) if total_latency_ms > 0 else 0
        }
        
        # Store pipeline metrics
        self.pipeline_metrics.append(pipeline_metrics)
        
        # Trim metrics
        self._trim_metrics()
        
        # Save state
        self._save_performance_state()
        
        self.logger.info(
            f"Pipeline completed: {total_latency_ms:.2f}ms, "
            f"{articles_processed} articles, {signals_generated} signals"
        )
        
        # Reset tracking
        self.current_pipeline_start = None
        self.current_stage_start = None
        self.current_stage_metrics = {}
        
        return pipeline_metrics
    
    def _save_performance_state(self) -> None:
        """Save performance metrics to persistent storage."""
        try:
            state = self.state_manager.load_state()
            
            perf_state = {
                "stage_metrics": dict(self.stage_metrics),
                "pipeline_metrics": self.pipeline_metrics,
                "error_counts": dict(self.error_counts),
                "feed_metrics": dict(self.feed_metrics),
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
            state["performance_tracker"] = perf_state
            self.state_manager.save_state(state)
            
            self.logger.debug("Performance state saved")
            
        except Exception as e:
            self.logger.error(f"Failed to save performance state: {e}")
    
    def get_stage_metrics(self, stage_name: Optional[str] = None) -> Dict[str, Any]:
        """Get stage performance metrics."""
        if stage_name:
            latencies = self.stage_metrics.get(stage_name, [])
            if not latencies:
                return {}
            
            return {
                "stage_name": stage_name,
                "sample_count": len(latencies),
                "avg_latency_ms": sum(latencies) / len(latencies),
                "min_latency_ms": min(latencies),
                "max_latency_ms": max(latencies),
                "p95_latency_ms": sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) > 20 else max(latencies),
                "error_count": self.error_counts.get(stage_name, 0),
                "error_rate": self.error_counts.get(stage_name, 0) / len(latencies) if latencies else 0
            }
        else:
            # Return all stage metrics
            return {
                stage_name: self.get_stage_metrics(stage_name)
                for stage_name in self.stage_metrics.keys()
            }
    
    def get_pipeline_metrics(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent pipeline performance metrics."""
        return self.pipeline_metrics[-limit:]
    
    def get_feed_metrics(self, feed_name: Optional[str] = None) -> Dict[str, Any]:
        """Get RSS feed performance metrics."""
        if feed_name:
            latencies = self.feed_metrics.get(feed_name, [])
            if not latencies:
                return {}
            
            return {
                "feed_name": feed_name,
                "sample_count": len(latencies),
                "avg_latency_ms": sum(latencies) / len(latencies),
                "min_latency_ms": min(latencies),
                "max_latency_ms": max(latencies),
                "p95_latency_ms": sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) > 20 else max(latencies),
                "error_count": self.error_counts.get(f"feed_{feed_name}", 0),
                "success_rate": 1.0 - (self.error_counts.get(f"feed_{feed_name}", 0) / len(latencies)) if latencies else 0
            }
        else:
            # Return all feed metrics
            return {
                feed_name: self.get_feed_metrics(feed_name)
                for feed_name in self.feed_metrics.keys()
            }
    
    def get_system_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive system performance summary."""
        recent_pipelines = self.pipeline_metrics[-100:]  # Last 100 runs
        
        if not recent_pipelines:
            return {"status": "No pipeline data available"}
        
        # Calculate aggregates
        total_latency = sum(p["total_latency_ms"] for p in recent_pipelines)
        total_articles = sum(p["articles_processed"] for p in recent_pipelines)
        total_signals = sum(p["signals_generated"] for p in recent_pipelines)
        total_errors = sum(len(p["errors"]) for p in recent_pipelines)
        
        # Stage performance
        stage_summary = {}
        for stage_name in self.stage_metrics:
            latencies = self.stage_metrics[stage_name]
            if latencies:
                stage_summary[stage_name] = {
                    "avg_latency_ms": sum(latencies) / len(latencies),
                    "sample_count": len(latencies),
                    "error_rate": self.error_counts.get(stage_name, 0) / len(latencies)
                }
        
        return {
            "summary_period": f"Last {len(recent_pipelines)} pipeline runs",
            "pipeline_performance": {
                "avg_latency_ms": total_latency / len(recent_pipelines),
                "min_latency_ms": min(p["total_latency_ms"] for p in recent_pipelines),
                "max_latency_ms": max(p["total_latency_ms"] for p in recent_pipelines),
                "throughput_articles_per_sec": total_articles / (total_latency / 1000) if total_latency > 0 else 0,
                "throughput_signals_per_sec": total_signals / (total_latency / 1000) if total_latency > 0 else 0,
                "error_rate": total_errors / len(recent_pipelines)
            },
            "stage_performance": stage_summary,
            "feed_performance": self.get_feed_metrics(),
            "total_pipelines": len(self.pipeline_metrics),
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
    
    def reset_metrics(self) -> None:
        """Reset all performance metrics."""
        self.stage_metrics.clear()
        self.pipeline_metrics.clear()
        self.error_counts.clear()
        self.feed_metrics.clear()
        self._save_performance_state()
        self.logger.info("All performance metrics reset")
