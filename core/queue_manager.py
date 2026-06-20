import threading
from typing import List, Dict, Any, Callable, Optional
from core.downloader import YoutubeDownloader

class DownloadQueueManager:
    """Manages a queue of download tasks with concurrency limits."""
    def __init__(self, max_concurrent: int = 3, progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> None:
        self.max_concurrent = max_concurrent
        self.progress_callback = progress_callback
        self.tasks: List[YoutubeDownloader] = []
        self.lock = threading.Lock()

    def add_task(self, url: str, save_path: str, format_choice: str, quality_choice: str, audio_only: bool, audio_format: str) -> YoutubeDownloader:
        """
        Creates a new downloader task and adds it to the queue.
        """
        with self.lock:
            downloader = YoutubeDownloader(
                url=url,
                save_path=save_path,
                format_choice=format_choice,
                quality_choice=quality_choice,
                audio_only=audio_only,
                audio_format=audio_format,
                progress_callback=self._on_task_progress
            )
            # Initial status is Pending
            downloader.status = "Pending"
            self.tasks.append(downloader)
            
            # Send initial event to UI
            if self.progress_callback:
                self.progress_callback({
                    "id": downloader.download_id,
                    "status": "Pending",
                    "title": "Initializing...",
                    "percent": 0
                })

        self.process_queue()
        return downloader

    def _on_task_progress(self, data: Dict[str, Any]) -> None:
        """
        Internal callback received from active downloaders.
        Forward it to the UI and process queue on completion states.
        """
        status = data.get("status")
        download_id = data.get("id")
        
        # Track latest stats on the task object itself for dashboard aggregation
        with self.lock:
            for t in self.tasks:
                if t.download_id == download_id:
                    if "speed" in data:
                        t.speed = data.get("speed", 0)
                    if "eta" in data:
                        t.eta = data.get("eta", 0)
                    if "downloaded_bytes" in data:
                        t.downloaded_bytes = data.get("downloaded_bytes", 0)
                    break
        
        
        # When a download finishes, we trigger the queue check
        if status in ["Completed", "Failed", "Cancelled"]:
            # Needs to run in background or handle queue processing
            threading.Thread(target=self.process_queue, daemon=True).start()

        if self.progress_callback:
            self.progress_callback(data)

    def process_queue(self) -> None:
        """
        Processes pending tasks up to the concurrency limit.
        """
        with self.lock:
            active_count = sum(1 for t in self.tasks if t.status in ["Downloading", "Merging"])
            
            if active_count >= self.max_concurrent:
                return

            for t in self.tasks:
                if t.status == "Pending":
                    # Launch task in background thread
                    t.status = "Downloading"
                    threading.Thread(target=t.run, daemon=True).start()
                    active_count += 1
                    
                    if active_count >= self.max_concurrent:
                        break

    def pause_task(self, download_id: str) -> None:
        """
        Pauses an active download by cancelling the thread.
        """
        with self.lock:
            for t in self.tasks:
                if t.download_id == download_id:
                    if t.status in ["Downloading", "Merging"]:
                        t.cancel()
                        t.status = "Paused"
                        if self.progress_callback:
                            self.progress_callback({
                                "id": download_id,
                                "status": "Paused"
                            })
                    elif t.status == "Pending":
                        t.status = "Paused"
                        if self.progress_callback:
                            self.progress_callback({
                                "id": download_id,
                                "status": "Paused"
                            })
                    break
        threading.Thread(target=self.process_queue, daemon=True).start()

    def resume_task(self, download_id: str) -> None:
        """
        Resumes a paused download by creating a new downloader wrapper.
        """
        with self.lock:
            for i, t in enumerate(self.tasks):
                if t.download_id == download_id:
                    if t.status == "Paused":
                        # Instantiate fresh downloader for clean execution state
                        new_downloader = YoutubeDownloader(
                            url=t.url,
                            save_path=t.save_path,
                            format_choice=t.format_choice,
                            quality_choice=t.quality_choice,
                            audio_only=t.audio_only,
                            audio_format=t.audio_format,
                            progress_callback=self._on_task_progress
                        )
                        new_downloader.download_id = t.download_id
                        new_downloader.title = t.title
                        new_downloader.status = "Pending"
                        self.tasks[i] = new_downloader
                        
                        if self.progress_callback:
                            self.progress_callback({
                                "id": download_id,
                                "status": "Pending",
                                "percent": 0
                            })
                    break
        threading.Thread(target=self.process_queue, daemon=True).start()

    def cancel_task(self, download_id: str) -> None:
        """
        Cancels a task.
        """
        with self.lock:
            for t in self.tasks:
                if t.download_id == download_id:
                    t.cancel()
                    t.status = "Cancelled"
                    # status callback will trigger process_queue inside _on_task_progress
                    break

    def remove_task(self, download_id: str) -> None:
        """
        Cancels and completely removes a task from the list.
        """
        with self.lock:
            for t in self.tasks:
                if t.download_id == download_id:
                    t.cancel()
            self.tasks = [t for t in self.tasks if t.download_id != download_id]
        threading.Thread(target=self.process_queue, daemon=True).start()

    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """
        Aggregates metrics across all tasks for the UI dashboard.
        """
        with self.lock:
            total_speed = 0
            total_remaining_time = 0
            storage_used = 0
            
            for t in self.tasks:
                if t.status == "Downloading":
                    total_speed += getattr(t, 'speed', 0)
                    # Taking the maximum ETA of active downloads as a rough total remaining time
                    eta = getattr(t, 'eta', 0)
                    if eta and eta > total_remaining_time:
                        total_remaining_time = eta
                
                # All downloaded bytes across active, paused, or completed tasks
                storage_used += getattr(t, 'downloaded_bytes', 0)
            
            total_success = sum(1 for t in self.tasks if t.status == "Completed")
            total_failed = sum(1 for t in self.tasks if t.status == "Failed")
            total_downloads = len(self.tasks)
            
            success_rate = 0.0
            if (total_success + total_failed) > 0:
                success_rate = (total_success / (total_success + total_failed)) * 100
                
            return {
                "total_speed": total_speed,
                "remaining_eta": total_remaining_time,
                "storage_used": storage_used,
                "total_downloads": total_downloads,
                "success_rate": success_rate,
                "completed": total_success,
                "failed": total_failed
            }

