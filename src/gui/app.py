import customtkinter as ctk
from typing import Dict, List
import threading
import queue
from send2trash import send2trash
import os
import tkinter as tk
from tkinter import filedialog
import time

from src.core.file_scanner import FileScanner
from src.core.ai_interface import AIInterface
from src.utils.logger import setup_logger
from src.gui.chatbox import ChatBox
from src.utils.debug_overlay import DebugOverlay

# Example queries for different operations
EXAMPLE_QUERIES = [
    "Show me all PDF files",
    "Find files larger than 100MB",
    "Find duplicate files",
    "Show space usage by file type",
    "Delete all temporary files",
    "List files modified in the last week"
]

class StorageAssistant:
    def __init__(self):
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        
        # Core components
        self.file_scanner = FileScanner()
        self.ai_interface = AIInterface()
        self.file_data = []
        
        # UI Setup
        self.root = ctk.CTk()
        self._setup_window()
        self._create_widgets()
        
        # Initialize scan_speed_label
        self.scan_speed_label = ctk.CTkLabel(
            self.status_bar,
            text="",
            font=("Segoe UI", 10)
        )
        self.scan_speed_label.pack(side="right", padx=(0, 10))
        self.auto_name_widgets()

        
    def _setup_window(self):
        """Configure main window properties"""
        self.root.title("Storage Assistant AI")
        self.root.geometry("1400x900")
        self.root.minsize(1200, 800)
        
        # 3-column layout (sidebar | main | chat)
        self.root.grid_columnconfigure(0, weight=0, minsize=240)  # Sidebar
        self.root.grid_columnconfigure(1, weight=1)               # Main content
        self.root.grid_columnconfigure(2, weight=0, minsize=0)    # Chat (starts hidden)
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(3, weight=0, minsize=0)    # Spacer column to prevent leftward shift

    def _create_widgets(self):
        """Create all UI components"""
        # Left Sidebar
        self.sidebar = ctk.CTkFrame(self.root, width=240, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=(0, 0))
        self._build_sidebar()

        # Main Content Area (middle)
        self.main_content = ctk.CTkFrame(self.root, corner_radius=0)
        self.main_content.grid(row=0, column=1, sticky="nsew")
        self._build_main_content()

        # Chat Panel (right, initially hidden)
        self.chat_panel = ChatBox(self.root, self.handle_chat_message)
        self.chat_panel.grid(row=0, column=2, sticky="nsew")
        self.chat_panel.grid_remove()
        self.chat_panel_visible = False

        # Spacer column (after chat to keep UI pinned to left)
        self.spacer = ctk.CTkFrame(self.root, width=0)
        self.spacer.grid(row=0, column=3, sticky="nsew")  # No need to remove


    def _build_sidebar(self):
        """Construct left sidebar components"""
        # Directory Controls
        dir_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        dir_frame.pack(pady=(15, 10), padx=15, fill="x")
        
        ctk.CTkLabel(dir_frame, text="WORKSPACE").pack(anchor="w")
        
        self.dir_entry = ctk.CTkEntry(dir_frame, placeholder_text="Select directory...")
        self.dir_entry.pack(fill="x", pady=(5, 0))
        
        btn_frame = ctk.CTkFrame(dir_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(5, 0))
        
        ctk.CTkButton(
            btn_frame,
            text="Browse",
            width=80,
            command=self.browse_directory
        ).pack(side="left", padx=(0, 5))
        
        self.scan_btn = ctk.CTkButton(
            btn_frame,
            text="Scan",
            width=80,
            command=self.start_scan
        )
        self.scan_btn.pack(side="left")

        # Quick Actions
        actions_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        actions_frame.pack(pady=15, padx=15, fill="x")
        
        ctk.CTkLabel(actions_frame, text="QUICK ACTIONS").pack(anchor="w")
        
        actions = [
            ("🔍 Find Large Files", "Find files >100MB"),
            ("🔄 Find Duplicates", "Find duplicate files"),
            ("📊 Analyze Space", "Analyze space usage")
        ]
        
        for icon_text, cmd in actions:
            btn = ctk.CTkButton(
                actions_frame,
                text=icon_text,
                command=lambda c=cmd: self._execute_quick_action(c),
                anchor="w",
                height=36,
                fg_color="transparent",
                border_width=1,
                text_color=("gray20", "gray90"),
                hover_color=("gray80", "gray30")
            )
            btn.pack(fill="x", pady=3)

        # AI Chat Toggle
        self.chat_toggle = ctk.CTkButton(
            self.sidebar,
            text="💬 Open AI Chat",
            command=self.toggle_chat,
            height=36,
            fg_color=("#3B8ED0", "#1F6AA5"),
            hover_color=("#36719F", "#1A5A8C")
        )
        self.chat_toggle.pack(side="bottom", pady=(0, 15), padx=15, fill="x")

    def _build_main_content(self):
        """Construct main content area"""
        # Progress/Status Bar
        self.status_bar = ctk.CTkFrame(self.main_content, height=28)
        self.status_bar.pack(fill="x", padx=15, pady=(15, 0))
        
        self.status_label = ctk.CTkLabel(
            self.status_bar,
            text="Ready",
            font=("Segoe UI", 12)
        )
        self.status_label.pack(side="left")
        
        self.progress_bar = ctk.CTkProgressBar(
            self.status_bar,
            height=16,
            mode="determinate"
        )
        self.progress_bar.pack(side="right", padx=(0, 5))
        self.progress_bar.set(0)
        
        # Results Display
        self.results_frame = ctk.CTkFrame(self.main_content)
        self.results_frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        self.results_text = ctk.CTkTextbox(
            self.results_frame,
            wrap="word",
            font=("Consolas", 11)
        )
        self.results_text.pack(fill="both", expand=True)

    def toggle_chat(self):
        CHAT_WIDTH = 320
        DURATION_MS = 250
        
        if self.chat_panel_visible:
            # Hide animation
            self._animate_columns(
                main_target=1.0, 
                chat_target=0, 
                spacer_target=0,
                duration_ms=DURATION_MS,
                on_complete=lambda: self.chat_panel.grid_remove()
            )
        else:
            # Show animation
            self.chat_panel.grid()
            self._animate_columns(
                main_target=0.7,  # Main content takes 70% of remaining space
                chat_target=CHAT_WIDTH,
                spacer_target=1,
                duration_ms=DURATION_MS
            )
        
        self.chat_panel_visible = not self.chat_panel_visible

    def _animate_columns(self, main_target, chat_target, spacer_target, duration_ms, on_complete=None):
        """Smoothly animate all columns simultaneously"""
        start_vals = {
            1: self.root.grid_bbox(1)[2],
            2: self.root.grid_bbox(2)[2],
            3: self.root.grid_bbox(3)[2]
        }
        target_vals = {1: main_target, 2: chat_target, 3: spacer_target}
        start_time = time.time()
        
        def ease_out_back(t):
            c1 = 1.70158
            c3 = c1 + 1
            return 1 + c3 * pow(t - 1, 3) + c1 * pow(t - 1, 2)
        
        def animate():
            elapsed = time.time() - start_time
            progress = min(1.0, elapsed / (duration_ms / 1000))
            eased_progress = ease_out_back(progress)
            
            for col in [1, 2, 3]:
                current = start_vals[col] + (target_vals[col] - start_vals[col]) * eased_progress
                self.root.grid_columnconfigure(col, minsize=int(current), weight=(1 if col == 1 else 0))
            
            if progress < 1.0:
                self.root.after(16, animate)  # ~60fps
            elif on_complete:
                on_complete()
        
        animate()


    def show_example_queries(self):
        """Show example queries in a popup window."""
        # Create a new window
        example_window = ctk.CTkToplevel(self.root)
        example_window.title("Example Queries")
        example_window.geometry("400x300")
        example_window.minsize(400, 300)
        
        # Make the window modal
        example_window.transient(self.root)
        example_window.grab_set()
        
        # Create a frame for the examples
        frame = ctk.CTkFrame(example_window)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Add a label
        label = ctk.CTkLabel(
            frame,
            text="Click an example to use it:",
            font=("Arial", 14, "bold")
        )
        label.pack(pady=10)
        
        # Add example buttons
        for query in EXAMPLE_QUERIES:
            btn = ctk.CTkButton(
                frame,
                text=query,
                command=lambda q=query: self.use_example_query(q, example_window),
                width=350,
                height=30,
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray70", "gray30")
            )
            btn.pack(pady=5)
            
    def use_example_query(self, query: str, window: ctk.CTkToplevel):
        """Use the selected example query."""
        self.dir_entry.delete(0, tk.END)
        self.dir_entry.insert(0, query)
        window.destroy()
        
    def browse_directory(self):
        """Open a directory browser dialog."""
        directory = filedialog.askdirectory()
        if directory:
            self.dir_entry.delete(0, tk.END)
            self.dir_entry.insert(0, directory)
            
    def change_theme(self, new_theme: str):
        """Change the application theme."""
        ctk.set_appearance_mode(new_theme)
        
    def toggle_analytics(self):
        """Toggle analytics mode."""
        self.analytics_mode = not getattr(self, 'analytics_mode', False)
        self.update_log(f"Analytics mode: {'enabled' if self.analytics_mode else 'disabled'}")
        
    def update_log(self, message: str):
        """Update the log display with a new message."""
        self.results_text.insert("end", f"{message}\n")
        self.results_text.see("end")
        self.root.update_idletasks()  # Ensure GUI updates
        
    def start_scan(self):
        """Start scanning the selected directory with real-time feedback."""
        directory = self.dir_entry.get()
        if not directory or not os.path.exists(directory):
            self.update_log("Please select a valid directory")
            return

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
            last_update = 0
            processed_files = 0

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
        
    def cancel_scan(self):
        """Cancel the ongoing scan."""
        self.file_scanner.scan_cancelled = True
        self.update_log("Scan cancelled")
        
    def update_progress(self, value: float, operation: str = ""):
        """Update progress bar and status label."""
        self.progress_bar.set(value / 100)
        if operation:
            self.status_label.configure(text=f"{operation}: {value:.1f}%")
        
        # Calculate and display scan speed
        current_time = time.time()
        if current_time - self.last_update_time >= 1.0:  # Update every second
            files_processed = len(self.file_data) - self.last_file_count
            files_per_sec = files_processed / (current_time - self.last_update_time)
            self.scan_speed_label.configure(text=f"{files_per_sec:.1f} files/sec")
            self.last_update_time = current_time
            self.last_file_count = len(self.file_data)
        
        self.root.update_idletasks()
        
    def execute_query(self):
        """Execute the AI query."""
        query = self.dir_entry.get()
        if not query:
            self.update_log("Please enter a query")
            return
            
        if not self.file_data:
            self.update_log("Please scan a directory first")
            return
            
        self.execute_button.configure(state="disabled")
        try:
            command = self.ai_interface.parse_query(query, self.file_data)
            self.execute_command(command, self.file_data)
        except Exception as e:
            self.update_log(f"Error executing query: {str(e)}")
        finally:
            self.execute_button.configure(state="normal")
            
    def execute_command(self, command: Dict, file_data: List[Dict], for_chat=False):
        """Modified to return results for chat"""
        action = command.get("action")
        params = command.get("parameters", {})
        
        if action == "list":
            results = self._filter_files(file_data, params)
            if for_chat:
                return results
            else:
                self.list_files(results, params)
        elif action == "delete":
            self.delete_files(file_data, params)
        elif action == "find_duplicates":
            threading.Thread(target=self.find_duplicates, args=(file_data,), daemon=True).start()
        elif action == "analyze_space":
            self.analyze_space(file_data)
        elif action == "error":
            self.update_log(f"Error: {params.get('message', 'Unknown error')}")
        else:
            self.update_log(f"Unknown action: {action}")
            
    def _filter_files(self, file_data: List[Dict], params: Dict) -> List[Dict]:
        """Filter files based on parameters"""
        filtered = file_data
        if "extension" in params:
            filtered = [f for f in filtered if f["extension"] == params["extension"]]
        if "min_size" in params:
            filtered = [f for f in filtered if f["size"] >= params["min_size"]]
        return filtered

    def list_files(self, file_data: List[Dict], params: Dict):
        """List files matching the given parameters."""
        # Filter files based on parameters
        filtered_files = file_data
        if "extension" in params:
            filtered_files = [f for f in filtered_files if f["extension"] == params["extension"]]
        if "min_size" in params:
            filtered_files = [f for f in filtered_files if f["size"] >= params["min_size"]]
            
        # Display results
        self.update_log(f"Found {len(filtered_files)} matching files:")
        for file in filtered_files[:10]:  # Show first 10 files
            self.update_log(f"- {file['path']} ({file['size'] / (1024*1024):.2f} MB)")
        if len(filtered_files) > 10:
            self.update_log(f"... and {len(filtered_files) - 10} more files")
            
    def delete_files(self, file_data: List[Dict], params: Dict):
        """Delete files matching the given parameters."""
        # Filter files based on parameters
        files_to_delete = file_data
        if "extension" in params:
            files_to_delete = [f for f in files_to_delete if f["extension"] == params["extension"]]
        if "min_size" in params:
            files_to_delete = [f for f in files_to_delete if f["size"] >= params["min_size"]]
            
        # Confirm deletion
        if not files_to_delete:
            self.update_log("No files match the criteria")
            return
            
        self.update_log(f"About to delete {len(files_to_delete)} files:")
        for file in files_to_delete[:5]:  # Show first 5 files
            self.update_log(f"- {file['path']}")
        if len(files_to_delete) > 5:
            self.update_log(f"... and {len(files_to_delete) - 5} more files")
            
        # Perform deletion
        for file in files_to_delete:
            try:
                send2trash(file["path"])
                self.update_log(f"Deleted: {file['path']}")
            except Exception as e:
                self.update_log(f"Error deleting {file['path']}: {str(e)}")
                
    def find_duplicates(self, file_data: List[Dict]):
        """Find duplicates with progress reporting."""
        self.status_label.configure(text="Finding duplicates...")
        size_groups = self._group_by_size(file_data)
        total_files = sum(len(files) for files in size_groups.values())
        processed_files = 0

        for size, files in size_groups.items():
            for file in files:
                self.file_scanner.calculate_file_hash(file["path"])
                processed_files += 1
                progress = (processed_files / total_files) * 100
                self.update_progress(progress, "Hashing")
                self.scan_speed_label.configure(text=f"{processed_files}/{total_files} files")

        # ... rest of the duplicate logic ...

    def _group_by_size(self, file_data: List[Dict]) -> Dict[int, List[Dict]]:
        """Group files by size for duplicate detection."""
        size_groups = {}
        for file in file_data:
            size = file["size"]
            if size not in size_groups:
                size_groups[size] = []
            size_groups[size].append(file)
        return size_groups

    def analyze_space(self, file_data: List[Dict]):
        """Analyze disk space usage."""
        # Group files by extension
        extension_groups = {}
        for file in file_data:
            ext = file["extension"] or "no_extension"
            if ext not in extension_groups:
                extension_groups[ext] = []
            extension_groups[ext].append(file)
            
        # Calculate statistics
        total_size = sum(f["size"] for f in file_data)
        extension_stats = {
            ext: {
                "count": len(files),
                "total_size": sum(f["size"] for f in files),
                "percentage": sum(f["size"] for f in files) / total_size * 100
            }
            for ext, files in extension_groups.items()
        }
        
        # Display results
        self.update_log(f"\nSpace Analysis:")
        self.update_log(f"Total files: {len(file_data)}")
        self.update_log(f"Total size: {total_size / (1024*1024):.2f} MB")
        self.update_log("\nBreakdown by extension:")
        
        # Sort by size
        sorted_stats = sorted(
            extension_stats.items(),
            key=lambda x: x[1]["total_size"],
            reverse=True
        )
        
        for ext, stats in sorted_stats:
            self.update_log(
                f"- {ext}: {stats['count']} files, "
                f"{stats['total_size'] / (1024*1024):.2f} MB "
                f"({stats['percentage']:.1f}%)"
            )
            
    def activate_chat_mode(self):
        """Switch to conversational mode with animation"""
        self.current_mode = "chat"
        if not self.chat_panel_visible:
            self.toggle_chat()
        
        # Auto-suggest first question
        self.root.after(1000, lambda: self.chat_panel.add_message(
            "AI",
            "What would you like to know about these files?\n"
            "Try asking:\n"
            "• 'What's using the most space?'\n"
            "• 'Show me recent documents'\n"
            "• 'List all PDF files'"
        ))
    
    def handle_chat_message(self, message: str):
        """Process messages based on current mode"""
        if self.current_mode == "command":
            self.handle_command(message)
        else:
            try:
                response = self.ai_interface.chat_query(message)
                
                # Special handling for file listings
                if "Here are the files" in response:
                    files = self._extract_files_from_query(message)
                    self.chat_panel.add_message("AI", response.split(":")[0] + ":")
                    self.chat_panel.add_file_response(files)
                else:
                    self.chat_panel.add_message("AI", response)
                
            except Exception as e:
                self.chat_panel.add_message("AI", f"Error: {str(e)}")
    
    def _extract_files_from_query(self, query: str) -> List[Dict]:
        """Convert natural language query to file results"""
        command = self.ai_interface.parse_query(query, self.file_data)
        return self.execute_command(command, self.file_data, for_chat=True)

    def _execute_quick_action(self, command: str):
        """Handle quick action commands from the sidebar."""
        if not self.file_data:
            self.update_log("Please scan a directory first")
            return

        try:
            parsed_command = self.ai_interface.parse_query(command, self.file_data)
            self.execute_command(parsed_command, self.file_data)
        except Exception as e:
            self.update_log(f"Error executing quick action: {str(e)}")

    def auto_name_widgets(self):
        for name, val in self.__dict__.items():
            try:
                if isinstance(val, (ctk.CTkBaseClass, tk.Widget)):
                    val._name = name
            except:
                pass

    def run(self):
        """Start the application."""
        self.debug_overlay = DebugOverlay(self.root)
        self.root.mainloop() 

    