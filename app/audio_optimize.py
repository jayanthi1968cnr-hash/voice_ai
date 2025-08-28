"""Optimizations for audio processing to reduce latency"""
import threading
import os
import time

# Track files that need cleanup
cleanup_queue = []
cleanup_lock = threading.Lock()
cleanup_thread = None
cleanup_exit = threading.Event()

def queue_file_for_cleanup(filepath):
    """Add file to cleanup queue instead of immediately deleting"""
    if not filepath or not os.path.exists(filepath):
        return
        
    with cleanup_lock:
        cleanup_queue.append(filepath)
        
    # Start the cleanup thread if not running
    global cleanup_thread
    if cleanup_thread is None or not cleanup_thread.is_alive():
        cleanup_thread = threading.Thread(target=_cleanup_worker, daemon=True)
        cleanup_thread.start()

def _cleanup_worker():
    """Background thread that cleans up files without blocking main thread"""
    while not cleanup_exit.is_set():
        # Process any files in the queue
        files_to_clean = []
        with cleanup_lock:
            if cleanup_queue:
                files_to_clean = cleanup_queue.copy()
                cleanup_queue.clear()
        
        # Process the files outside the lock
        for filepath in files_to_clean:
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
            except Exception:
                # If we can't remove now, try again later
                with cleanup_lock:
                    cleanup_queue.append(filepath)
        
        # Sleep briefly to prevent high CPU usage
        time.sleep(0.5)

def shutdown_cleanup_thread():
    """Gracefully shutdown the cleanup thread"""
    cleanup_exit.set()
    
    global cleanup_thread
    if cleanup_thread and cleanup_thread.is_alive():
        cleanup_thread.join(timeout=1.0)