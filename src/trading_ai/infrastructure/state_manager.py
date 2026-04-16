"""
State persistence and recovery for the Trading AI system.

Provides atomic state operations, backup creation, and corruption recovery.
"""

from __future__ import annotations

import json
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Try to import portalocker for file locking
try:
    import portalocker
    HAS_PORTALOCKER = True
except ImportError:
    HAS_PORTALOCKER = False
    import fcntl
    import errno

from .config import config
from .logging import get_logger


class StateManager:
    """Manages system state persistence and recovery."""
    
    def __init__(self) -> None:
        """Initialize state manager."""
        self.logger = get_logger("state_manager")
        self.state_file = config.STATE_FILE
        self.backup_dir = Path(config.DATA_DIR) / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.lock_timeout = 30  # 30 seconds timeout for file locks
        self.lock_retry_delay = 0.1  # 100ms retry delay
    
    def _acquire_file_lock(self, file_path: str, mode: str = 'r') -> Any:
        """Acquire file lock with retry logic."""
        lock_file = f"{file_path}.lock"
        
        for attempt in range(int(self.lock_timeout / self.lock_retry_delay)):
            try:
                if HAS_PORTALOCKER:
                    # Use portalocker for cross-platform locking
                    lock_fd = open(lock_file, mode)
                    portalocker.lock(lock_fd, portalocker.LOCK_EX | portalocker.LOCK_NB)
                    return lock_fd
                else:
                    # Use fcntl for Unix systems
                    lock_fd = os.open(lock_file, os.O_CREAT | os.O_WRONLY | os.O_TRUNC)
                    fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    return lock_fd
            except (IOError, OSError) as e:
                if e.errno == errno.EAGAIN or e.errno == errno.EACCES:
                    # File is locked, wait and retry
                    time.sleep(self.lock_retry_delay)
                    continue
                else:
                    raise
        
        raise TimeoutError(f"Could not acquire file lock for {file_path} within {self.lock_timeout} seconds")
    
    def _release_file_lock(self, lock_fd: Any) -> None:
        """Release file lock."""
        try:
            if HAS_PORTALOCKER:
                portalocker.unlock(lock_fd)
            else:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
            lock_fd.close()
        except Exception as e:
            self.logger.warning(f"Error releasing file lock: {e}")
    
    def save_state(self, state: Dict[str, Any]) -> None:
        """Save system state atomically with file locking."""
        lock_fd = None
        try:
            # Acquire file lock
            lock_fd = self._acquire_file_lock(self.state_file, 'w')
            
            # Create temporary file
            temp_file = f"{self.state_file}.tmp"
            
            # Write to temporary file
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, default=self._json_serializer)
            
            # Atomic move
            os.replace(temp_file, self.state_file)
            
            self.logger.debug(f"State saved to {self.state_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to save state: {e}")
            raise
        finally:
            # Release file lock
            if lock_fd:
                self._release_file_lock(lock_fd)
    
    def load_state(self) -> Dict[str, Any]:
        """Load system state with file locking."""
        lock_fd = None
        try:
            if not os.path.exists(self.state_file):
                self.logger.info("State file not found, returning empty state")
                return self._create_empty_state()
            
            # Acquire file lock for reading
            lock_fd = self._acquire_file_lock(self.state_file, 'r')
            
            with open(self.state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            # Validate state structure
            validated_state = self._validate_state(state)
            
            self.logger.debug(f"State loaded from {self.state_file}")
            return validated_state
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Corrupted state file: {e}")
            return self._recover_from_backup()
        
        except Exception as e:
            self.logger.error(f"Failed to load state: {e}")
            return self._create_empty_state()
        finally:
            # Release file lock
            if lock_fd:
                self._release_file_lock(lock_fd)
    
    def create_backup(self) -> str:
        """Create state backup with timestamp."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"state_{timestamp}.json"
        
        try:
            if os.path.exists(self.state_file):
                shutil.copy2(self.state_file, backup_file)
                self.logger.info(f"Backup created: {backup_file}")
                
                # Clean old backups (keep last 10)
                self._cleanup_old_backups()
                
                return str(backup_file)
            else:
                self.logger.warning("State file not found, cannot create backup")
                return ""
                
        except Exception as e:
            self.logger.error(f"Failed to create backup: {e}")
            raise
    
    def restore_backup(self, backup_id: str) -> None:
        """Restore state from backup."""
        try:
            if backup_id == "latest":
                backup_file = self._get_latest_backup()
            else:
                backup_file = self.backup_dir / f"state_{backup_id}.json"
            
            if not backup_file.exists():
                raise FileNotFoundError(f"Backup file not found: {backup_file}")
            
            # Validate backup before restore
            with open(backup_file, 'r', encoding='utf-8') as f:
                backup_state = json.load(f)
            
            self._validate_state(backup_state)
            
            # Create current backup before restore
            self.create_backup()
            
            # Restore backup
            shutil.copy2(backup_file, self.state_file)
            
            self.logger.info(f"State restored from backup: {backup_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to restore backup: {e}")
            raise
    
    def get_backup_list(self) -> List[Dict[str, Any]]:
        """Get list of available backups."""
        backups = []
        
        try:
            for backup_file in self.backup_dir.glob("state_*.json"):
                stat = backup_file.stat()
                backups.append({
                    "id": backup_file.stem.replace("state_", ""),
                    "file": str(backup_file),
                    "size": stat.st_size,
                    "created": datetime.fromtimestamp(stat.st_ctime, timezone.utc)
                })
            
            # Sort by creation time (newest first)
            backups.sort(key=lambda x: x["created"], reverse=True)
            
        except Exception as e:
            self.logger.error(f"Failed to list backups: {e}")
        
        return backups
    
    def _create_empty_state(self) -> Dict[str, Any]:
        """Create empty state structure."""
        return {
            "version": "2.0.0",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "pipeline_state": {
                "last_run": None,
                "last_success": None,
                "run_count": 0,
                "success_count": 0
            },
            "positions": {},
            "orders": {},
            "risk_metrics": {
                "current_exposure": 0.0,
                "daily_pnl": 0.0,
                "max_drawdown": 0.0
            },
            "validation_memory": {},
            "performance_metrics": {
                "total_trades": 0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "expectancy": 0.0
            },
            "metadata": {}
        }
    
    def _validate_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize state structure."""
        required_keys = [
            "version", "created_at", "last_updated", "pipeline_state",
            "positions", "orders", "risk_metrics", "validation_memory",
            "performance_metrics", "metadata"
        ]
        
        # Ensure all required keys exist
        for key in required_keys:
            if key not in state:
                self.logger.warning(f"Missing state key: {key}, adding default")
                if key == "pipeline_state":
                    state[key] = {
                        "last_run": None,
                        "last_success": None,
                        "run_count": 0,
                        "success_count": 0
                    }
                elif key in ["positions", "orders", "validation_memory", "metadata"]:
                    state[key] = {}
                elif key == "risk_metrics":
                    state[key] = {
                        "current_exposure": 0.0,
                        "daily_pnl": 0.0,
                        "max_drawdown": 0.0
                    }
                elif key == "performance_metrics":
                    state[key] = {
                        "total_trades": 0,
                        "win_rate": 0.0,
                        "profit_factor": 0.0,
                        "expectancy": 0.0
                    }
                else:
                    state[key] = None
        
        # Update timestamp
        state["last_updated"] = datetime.now(timezone.utc).isoformat()
        
        return state
    
    def _json_serializer(self, obj: Any) -> Any:
        """Custom JSON serializer for special types."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    def _get_latest_backup(self) -> Path:
        """Get the most recent backup file."""
        backups = list(self.backup_dir.glob("state_*.json"))
        if not backups:
            raise FileNotFoundError("No backup files found")
        
        return max(backups, key=lambda f: f.stat().st_ctime)
    
    def _cleanup_old_backups(self, keep_count: int = 10) -> None:
        """Clean up old backup files."""
        try:
            backups = list(self.backup_dir.glob("state_*.json"))
            backups.sort(key=lambda f: f.stat().st_ctime, reverse=True)
            
            for backup_file in backups[keep_count:]:
                backup_file.unlink()
                self.logger.debug(f"Removed old backup: {backup_file}")
                
        except Exception as e:
            self.logger.error(f"Failed to cleanup old backups: {e}")
    
    def _recover_from_backup(self) -> Dict[str, Any]:
        """Attempt to recover from latest backup."""
        try:
            self.logger.info("Attempting to recover from backup")
            latest_backup = self._get_latest_backup()
            
            with open(latest_backup, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            # Move corrupted file and restore backup
            corrupted_file = f"{self.state_file}.corrupted"
            if os.path.exists(self.state_file):
                shutil.move(self.state_file, corrupted_file)
                self.logger.warning(f"Corrupted state file moved to: {corrupted_file}")
            
            shutil.copy2(latest_backup, self.state_file)
            
            validated_state = self._validate_state(state)
            self.logger.info("State recovered from backup")
            
            return validated_state
            
        except Exception as e:
            self.logger.error(f"Failed to recover from backup: {e}")
            return self._create_empty_state()
    
    def get_state_info(self) -> Dict[str, Any]:
        """Get information about current state file."""
        try:
            if not os.path.exists(self.state_file):
                return {"exists": False}
            
            stat = os.stat(self.state_file)
            
            # Try to load state to get additional info
            try:
                state = self.load_state()
                return {
                    "exists": True,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc),
                    "version": state.get("version"),
                    "created_at": state.get("created_at"),
                    "last_updated": state.get("last_updated"),
                    "run_count": state.get("pipeline_state", {}).get("run_count", 0)
                }
            except:
                return {
                    "exists": True,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc),
                    "corrupted": True
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get state info: {e}")
            return {"exists": False, "error": str(e)}
