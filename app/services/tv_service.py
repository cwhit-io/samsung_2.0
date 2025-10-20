import subprocess
import json
import time
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.models.tv import TVConfig, PairResponse, TVListResponse, TVStatusResponse, ValidationResponse, ConcurrentPairResponse, GenericScriptResponse

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent


class TVService:
    """Service for TV operations"""
    
    @staticmethod
    def get_available_tvs() -> TVListResponse:
        """Get list of all configured TVs with their pairing status"""
        try:
            config_path = PROJECT_ROOT / "config" / "config.json"
            with open(config_path, 'r') as file:
                config = json.load(file)
                
            # Load tokens to check pairing status
            tokens = TVService._load_tokens()
            
            tv_statuses = []
            for tv_data in config['tvs']:
                tv_config = TVConfig(**tv_data)
                token_info = tokens.get(tv_config.id, {})
                
                tv_status = TVStatusResponse(
                    tv_id=tv_config.id,
                    name=tv_config.name,
                    host=tv_config.host,
                    port=tv_config.port,
                    mac_address=tv_config.mac_address,
                    is_paired=bool(token_info),
                    paired_at=token_info.get('paired_at') if token_info else None
                )
                tv_statuses.append(tv_status)
            
            return TVListResponse(tvs=tv_statuses, count=len(tv_statuses))
        except Exception as e:
            raise Exception(f"Failed to load TV configuration: {str(e)}")
    
    @staticmethod
    def validate_tv_exists(tv_id: str) -> ValidationResponse:
        """Check if TV ID exists in configuration"""
        try:
            tvs = TVService.get_available_tvs()
            exists = any(tv.tv_id == tv_id for tv in tvs.tvs)
            
            return ValidationResponse(
                tv_id=tv_id,
                exists=exists,
                message="TV ID is valid" if exists else "TV ID not found in configuration"
            )
        except Exception as e:
            return ValidationResponse(
                tv_id=tv_id,
                exists=False,
                message=f"Error validating TV ID: {str(e)}"
            )
    
    @staticmethod
    def get_tv_by_id(tv_id: str) -> Optional[TVStatusResponse]:
        """Get specific TV configuration by ID"""
        try:
            tvs = TVService.get_available_tvs()
            for tv in tvs.tvs:
                if tv.tv_id == tv_id:
                    return tv
            return None
        except:
            return None
    
    @staticmethod
    def pair_tv(tv_id: str) -> PairResponse:
        """Pair with a TV using the pairing script"""
        try:
            # First validate TV exists
            tv = TVService.get_tv_by_id(tv_id)
            if not tv:
                return PairResponse(
                    status="not_found",
                    message=f"TV with ID '{tv_id}' not found in configuration",
                    tv_id=tv_id,
                    timestamp=datetime.now()
                )
            
            # Call the pairing script
            script_path = PROJECT_ROOT / "scripts" / "pair_tv.py"
            python_path = PROJECT_ROOT / ".venv" / "bin" / "python"
            
            result = subprocess.run(
                [str(python_path), str(script_path), tv_id],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(PROJECT_ROOT)
            )
            
            # Parse script output
            output = result.stdout.strip()
            
            if output == "pair_success":
                return PairResponse(
                    status="success",
                    message=f"Successfully paired with {tv.name}",
                    tv_id=tv_id,
                    tv_name=tv.name,
                    timestamp=datetime.now()
                )
            elif output == "id_not_found":
                return PairResponse(
                    status="not_found",
                    message=f"TV with ID '{tv_id}' not found",
                    tv_id=tv_id,
                    timestamp=datetime.now()
                )
            else:  # pair_failed or any other output
                return PairResponse(
                    status="failed",
                    message=f"Failed to pair with {tv.name}. Make sure TV is on and accept the pairing request.",
                    tv_id=tv_id,
                    tv_name=tv.name,
                    timestamp=datetime.now()
                )
                
        except subprocess.TimeoutExpired:
            return PairResponse(
                status="failed",
                message="Pairing timed out. Make sure TV is on and reachable.",
                tv_id=tv_id,
                timestamp=datetime.now()
            )
        except Exception as e:
            return PairResponse(
                status="failed",
                message=f"Pairing failed: {str(e)}",
                tv_id=tv_id,
                timestamp=datetime.now()
            )
    
    @staticmethod
    def concurrent_pair_tvs(tv_ids: List[str]) -> ConcurrentPairResponse:
        """Pair with multiple TVs concurrently using threads"""
        start_time = time.time()
        results = []
        
        def pair_single_tv(tv_id: str) -> PairResponse:
            """Thread worker function to pair a single TV"""
            # Validate TV exists first
            validation = TVService.validate_tv_exists(tv_id)
            if not validation.exists:
                return PairResponse(
                    status="not_found",
                    message=f"TV with ID '{tv_id}' not found in configuration",
                    tv_id=tv_id,
                    timestamp=datetime.now()
                )
            
            # Attempt pairing
            return TVService.pair_tv(tv_id)
        
        # Use ThreadPoolExecutor to run pairing operations concurrently
        max_workers = len(tv_ids)  # Allow all TVs to pair simultaneously
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all pairing tasks
            future_to_tv_id = {executor.submit(pair_single_tv, tv_id): tv_id for tv_id in tv_ids}
            
            # Collect results as they complete
            for future in as_completed(future_to_tv_id):
                tv_id = future_to_tv_id[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    # Handle any unexpected errors
                    error_result = PairResponse(
                        status="failed",
                        message=f"Unexpected error pairing {tv_id}: {str(e)}",
                        tv_id=tv_id,
                        timestamp=datetime.now()
                    )
                    results.append(error_result)
        
        # Sort results by TV ID for consistent ordering
        results.sort(key=lambda x: x.tv_id)
        
        # Calculate summary
        execution_time = time.time() - start_time
        success_count = sum(1 for r in results if r.status == "success")
        failed_count = sum(1 for r in results if r.status == "failed")
        not_found_count = sum(1 for r in results if r.status == "not_found")
        total = len(results)
        
        summary = f"Processed {total} TVs in {execution_time:.2f}s: {success_count} successful"
        if failed_count > 0:
            summary += f", {failed_count} failed"
        if not_found_count > 0:
            summary += f", {not_found_count} not found"
        
        return ConcurrentPairResponse(
            total_requested=total,
            results=results,
            summary=summary,
            execution_time_seconds=round(execution_time, 2)
        )
    
    @staticmethod
    def execute_script(script_name: str, tv_ids: List[str], args: List[str] = None, concurrent: bool = True) -> GenericScriptResponse:
        """Generic script executor for any TV script"""
        start_time = time.time()
        args = args or []
        results = []
        
        # Define python path once at the top level
        venv_python = PROJECT_ROOT / ".venv" / "bin" / "python"
        if venv_python.exists():
            python_path = str(venv_python)
        else:
            python_path = "python3"
        
        def execute_single_script(tv_id):
            """Execute script for a single TV"""
            tv_start_time = time.time()
            
            try:
                script_path = PROJECT_ROOT / "scripts" / f"{script_name}.py"
                
                # Check if script exists
                if not script_path.exists():
                    return {
                        "tv_id": tv_id,
                        "status": "error",
                        "output": f"Script '{script_name}.py' not found",
                        "success": False,
                        "timestamp": datetime.now().isoformat()
                    }
                
                # Build command: python script.py tv_id [args...]
                cmd = [python_path, str(script_path), tv_id] + args
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=str(PROJECT_ROOT)
                )
                
                return {
                    "tv_id": tv_id,
                    "status": "success" if result.returncode == 0 else "error",
                    "output": result.stdout.strip() if result.stdout else (result.stderr.strip() if result.stderr else "No output"),
                    "success": result.returncode == 0,
                    "timestamp": datetime.now().isoformat()
                }
                
            except subprocess.TimeoutExpired:
                return {
                    "tv_id": tv_id,
                    "status": "error",
                    "output": "Script execution timed out after 30 seconds",
                    "success": False,
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                return {
                    "tv_id": tv_id,
                    "status": "error",
                    "output": f"Error executing script: {str(e)}",
                    "success": False,
                    "timestamp": datetime.now().isoformat()
                }
        
        # Execute scripts
        if concurrent and len(tv_ids) > 1:
            # Concurrent execution
            with ThreadPoolExecutor(max_workers=len(tv_ids)) as executor:
                future_to_tv = {executor.submit(execute_single_script, tv_id): tv_id for tv_id in tv_ids}
                
                for future in as_completed(future_to_tv):
                    results.append(future.result())
        else:
            # Sequential execution
            for tv_id in tv_ids:
                results.append(execute_single_script(tv_id))
        
        # Sort results by TV ID for consistent output
        results.sort(key=lambda x: x['tv_id'])
        
        # Generate summary
        end_time = time.time()
        execution_time = end_time - start_time
        
        successful = len([r for r in results if r['success']])
        failed = len(results) - successful
        
        if failed > 0:
            summary = f"Executed '{script_name}' on {len(tv_ids)} TVs in {execution_time:.2f}s: {successful} successful, {failed} errors"
        else:
            summary = f"Executed '{script_name}' on {len(tv_ids)} TVs in {execution_time:.2f}s: {successful} successful"
        
        return GenericScriptResponse(
            script_name=script_name,
            total_requested=len(tv_ids),
            results=results,
            summary=summary,
            execution_time_seconds=execution_time,
            concurrent=concurrent
        )

    @staticmethod
    def _load_tokens() -> dict:
        """Load pairing tokens from tokens.json"""
        tokens_path = PROJECT_ROOT / "tokens.json"
        try:
            with open(tokens_path, 'r') as file:
                return json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}


def load_tokens() -> dict:
    """Load pairing tokens from tokens.json."""
    tokens_path = PROJECT_ROOT / "tokens.json"
    try:
        with open(tokens_path, 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


