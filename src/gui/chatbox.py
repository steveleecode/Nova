import customtkinter as ctk
from typing import Callable, List, Dict
import time
import webbrowser
import tkinter as tk

class ChatBox(ctk.CTkFrame):
    def __init__(self, master, send_callback: Callable, **kwargs):
        super().__init__(master, width=0, **kwargs)
        self.send_callback = send_callback
        self.configure(
            width=320,
            fg_color=("#FFFFFF", "#2B2B2B"),
            border_width=1,
            border_color=("#E1E1E1", "#3D3D3D")
        )
        
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=10)
        
        self.title_label = ctk.CTkLabel(
            header,
            text="AI Assistant",
            font=("Segoe UI", 14, "bold"),
            text_color=("#2B2B2B", "#FFFFFF")
        )
        self.title_label.pack(side="left")
        
        # Chat History
        self.chat_history = ctk.CTkTextbox(
            self,
            wrap="word",
            state="disabled",
            font=("Segoe UI", 12),
            fg_color=("#FAFAFA", "#252525"),
            text_color=("#2B2B2B", "#E0E0E0")
        )
        self.chat_history.pack(fill="both", expand=True, padx=10, pady=(0,10))
        
        # Input Area
        input_frame = ctk.CTkFrame(self, fg_color="transparent")
        input_frame.pack(fill="x", padx=10, pady=(0,10))
        
        self.user_input = ctk.CTkEntry(
            input_frame,
            placeholder_text="Ask about your files...",
            font=("Segoe UI", 12)
        )
        self.user_input.pack(side="left", fill="x", expand=True, padx=(0,5))
        self.user_input.bind("<Return>", lambda e: self.send_message())
        
        send_button = ctk.CTkButton(
            input_frame,
            text="Send",
            width=60,
            command=self.send_message
        )
        send_button.pack(side="right")
        
        # Configure tags for clickable links
        self.chat_history.tag_config("file_link", foreground="blue", underline=True)
        self.chat_history.tag_bind("file_link", "<Button-1>", self.open_file)
        
        self.update()  # Ensures winfo_width is accurate
        self.typing_indicator = None
    
    def clear_chat(self):
        """Clear the chat history completely"""
        self.chat_history.configure(state="normal")
        self.chat_history.delete(1.0, "end")
        self.chat_history.configure(state="disabled")
        self.add_message("System", "Chat history cleared. Start a new conversation.")

    def send_message(self):
        """Handle sending a message"""
        message = self.user_input.get()
        if message.strip():
            self.add_message("You", message)
            self.user_input.delete(0, "end")
            self.show_typing()
            self.after(100, lambda: self.send_callback(message))

    def add_message(self, sender: str, message: str):
        """Add a message to the chat history"""
        self.chat_history.configure(state="normal")
        self.chat_history.insert("end", f"{sender}: {message}\n\n")
        self.chat_history.configure(state="disabled")
        self.chat_history.see("end")

    def show_typing(self):
        """Show 'AI is typing...' indicator."""
        if self.typing_indicator:
            self.chat_history.configure(state="normal")
            self.chat_history.delete("end-3c", "end")  # Remove previous typing indicator
            self.chat_history.configure(state="disabled")
        
        self.chat_history.configure(state="normal")
        self.typing_indicator = self.chat_history.insert("end", "AI is typing...\n")
        self.chat_history.configure(state="disabled")
        self.chat_history.see("end")
        self.master.after(1500, self.hide_typing)  # Hide after 1.5 seconds

    def hide_typing(self):
        """Hide typing indicator."""
        if self.typing_indicator:
            self.chat_history.configure(state="normal")
            self.chat_history.delete("end-2l", "end")  # Remove typing indicator
            self.chat_history.configure(state="disabled")
            self.typing_indicator = None

    def send_suggestion(self, text: str):
        """Send a suggested query"""
        self.user_input.delete(0, "end")
        self.user_input.insert(0, text)
        self.send_message()
    
    def open_file(self, event):
        """Handle clicking on file paths"""
        index = self.chat_history.index(f"@{event.x},{event.y}")
        line = self.chat_history.get(index + " linestart", index + " lineend")
        if line.startswith(("/", "C:", "D:", "E:")):
            webbrowser.open(f"file://{line.strip()}")
    
    def add_file_response(self, files: List[Dict]):
        """Format file listings with clickable paths"""
        self.chat_history.configure(state="normal")
        for file in files[:5]:  # Show first 5 files
            path = file["path"]
            self.chat_history.insert("end", f"• {path}\n", "file_link")
        if len(files) > 5:
            self.chat_history.insert("end", f"... and {len(files)-5} more files\n")
        self.chat_history.configure(state="disabled")
        self.chat_history.see("end")

