import os
import hashlib
import struct
from datetime import datetime
from typing import Dict, List, Optional, Callable
import win32file
import win32con
import queue
import logging
import time
import threading

from src.utils.windows_api import USN_RECORD, FSCTL_QUERY_USN_JOURNAL, FSCTL_ENUM_USN_DATA, is_ntfs_drive

class FileScanner:
    def __init__(self):
        self.file_cache: Dict[str, Dict] = {}
        self.logger = logging.getLogger(__name__)
        self.scan_cancelled = False
        self.log_queue = queue.Queue()
        self.current_queries = []
        
    def get_usn_journal_data(self, drive: str) -> List[Dict]:
        """Read the USN Journal for fast file enumeration."""
        try:
            # Open the volume handle
            handle = win32file.CreateFile(
                f"\\\\.\\{drive}",
                win32con.GENERIC_READ,
                win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE,
                None,
                win32con.OPEN_EXISTING,
                win32con.FILE_FLAG_SEQUENTIAL_SCAN,
                None
            )
            
            # Query USN Journal
            usn_data = win32file.DeviceIoControl(
                handle,
                FSCTL_QUERY_USN_JOURNAL,
                None,
                1024
            )
            
            # Get USN Journal ID and start USN
            journal_id = struct.unpack("<Q", usn_data[0:8])[0]
            start_usn = struct.unpack("<Q", usn_data[8:16])[0]
            
            # Prepare for enumeration
            results = []
            current_usn = start_usn
            buffer_size = 65536  # 64KB buffer
            
            while True:
                if self.scan_cancelled:
                    break
                    
                # Create input buffer for enumeration
                input_buffer = struct.pack("<QQQ", start_usn, current_usn, journal_id)
                
                try:
                    # Enumerate USN records
                    output_buffer = win32file.DeviceIoControl(
                        handle,
                        FSCTL_ENUM_USN_DATA,
                        input_buffer,
                        buffer_size
                    )
                    
                    # Get next USN
                    next_usn = struct.unpack("<Q", output_buffer[0:8])[0]
                    
                    # Process USN records
                    offset = 8
                    while offset < len(output_buffer):
                        record = USN_RECORD.from_buffer_copy(output_buffer[offset:])
                        
                        # Skip if record is invalid
                        if record.RecordLength == 0:
                            break
                            
                        # Get file name
                        name_length = record.FileNameLength // 2  # Convert bytes to characters
                        name_offset = offset + record.FileNameOffset
                        file_name = output_buffer[name_offset:name_offset + record.FileNameLength].decode('utf-16')
                        
                        # Skip directories
                        if not (record.FileAttributes & win32con.FILE_ATTRIBUTE_DIRECTORY):
                            try:
                                file_path = os.path.join(drive, file_name)
                                stats = os.stat(file_path)
                                
                                results.append({
                                    "path": file_path,
                                    "size": stats.st_size,
                                    "last_modified": datetime.fromtimestamp(stats.st_mtime),
                                    "last_accessed": datetime.fromtimestamp(stats.st_atime),
                                    "extension": os.path.splitext(file_name)[1].lower(),
                                    "hash": ""  # We'll calculate this only if needed
                                })
                            except:
                                # Skip files we can't access
                                pass
                        
                        offset += record.RecordLength
                    
                    # Check if we've reached the end
                    if next_usn == current_usn:
                        break
                    current_usn = next_usn
                    
                except Exception as e:
                    self.logger.warning(f"Error reading USN records: {str(e)}")
                    break
            
            win32file.CloseHandle(handle)
            return results
            
        except Exception as e:
            self.logger.error(f"Error reading USN Journal: {str(e)}")
            return []
            
    def calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of a file."""
        if self.scan_cancelled:
            return ""
        self.logger.debug(f"Calculating hash for: {file_path}")
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                if self.scan_cancelled:
                    return ""
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def fast_scan_directory(self, directory: str, progress_callback=None, log_callback=None) -> List[Dict]:
        """Fast directory scanning using win32file.FindFilesIterator."""
        # Reset state for a new scan
        self.scan_cancelled = False
        results = []
        total_size = 0
        processed_files = 0
        skip_dirs = {"Windows", "Program Files", "Program Files (x86)", "System Volume Information"}

        try:
            # Get total file count first, excluding skipped directories
            total_files = 0
            for root, dirs, files in os.walk(directory):
                # Remove skipped directories from traversal
                dirs[:] = [d for d in dirs if d not in skip_dirs]
                total_files += len(files)
            
            if log_callback:
                log_callback(f"Found {total_files} files to scan")
            
            # Use a stack for iterative traversal instead of recursion
            stack = [directory]
            while stack and not self.scan_cancelled:
                current_dir = stack.pop()
                dir_name = os.path.basename(current_dir)
                
                try:
                    pattern = os.path.join(current_dir, "*")
                    for file_info in win32file.FindFilesIterator(pattern):
                        file_name = file_info[8]
                        file_attrs = file_info[0]
                        # Skip . and .. directories
                        if file_name in (".", ".."):
                            continue
                        full_path = os.path.join(current_dir, file_name)
                        if file_attrs & win32con.FILE_ATTRIBUTE_DIRECTORY:
                            # Skip directories in skip_dirs
                            if file_name in skip_dirs:
                                continue
                            stack.append(full_path)
                            continue
                        try:
                            stats = os.stat(full_path)
                            file_size = stats.st_size
                            total_size += file_size
                            results.append({
                                "path": full_path,
                                "size": file_size,
                                "last_modified": datetime.fromtimestamp(stats.st_mtime),
                                "last_accessed": datetime.fromtimestamp(stats.st_atime),
                                "extension": os.path.splitext(file_name)[1].lower(),
                                "hash": ""  # We'll calculate this only if needed
                            })
                            processed_files += 1
                            if processed_files % 100 == 0:
                                if log_callback:
                                    progress_msg = f"Processed {processed_files}/{total_files} files ({(processed_files/total_files)*100:.1f}%)"
                                    size_msg = f"Current total size: {total_size/(1024*1024):.2f} MB"
                                    log_callback(progress_msg)
                                    log_callback(size_msg)
                                if progress_callback:
                                    progress_callback(processed_files / total_files * 100)
                        except (PermissionError, FileNotFoundError):
                            continue
                except Exception as e:
                    self.logger.error(f"Error scanning directory {current_dir}: {str(e)}")
                    continue
            return results
        except Exception as e:
            self.logger.error(f"Error in fast_scan_directory: {str(e)}")
            return [] 

    def start_scan(self):
        """Start scanning the selected directory with real-time feedback."""
        directory = self.dir_entry.get()
        if not directory or not os.path.exists(directory):
            self.update_log("Please select a valid directory")
            return

        # Cancel any ongoing scan
        if hasattr(self, 'scan_thread') and self.scan_thread.is_alive():
            self.scan_cancelled = True
            self.scan_thread.join()  # Wait for the previous scan to finish

        # Reset UI and state
        self.scan_btn.configure(state="disabled")
        self.dir_entry.configure(state="disabled")
        self.progress_bar.set(0)
        self.file_data = []
        self.status_label.configure(text="Scanning...")
        self.scan_speed_label.configure(text="")
        self.last_update_time = time.time()
        self.last_file_count = 0

        def scan_thread():
            start_time = time.time()
            try:
                self.file_data = self.file_scanner.fast_scan_directory(
                    directory,
                    progress_callback=lambda p: self.update_progress(p, "Scanning"),
                    log_callback=lambda msg: self.update_log(msg)
                )
                self.ai_interface.add_scan_context(self.file_data)
                self.update_log(f"Scan complete. Found {len(self.file_data)} files.")
                self.root.after(0, self.activate_chat_mode)
            except Exception as e:
                self.update_log(f"Error during scan: {str(e)}")
            finally:
                self.scan_btn.configure(state="normal")
                self.dir_entry.configure(state="normal")
                self.status_label.configure(text="Ready")

        self.scan_thread = threading.Thread(target=scan_thread, daemon=True)
        self.scan_thread.start() 