import tkinter as tk

class DebugOverlay:
    def __init__(self, root):
        self.root = root
        self.debug_enabled = False
        self.tooltip = None
        self.overlays = []
        self.root.bind("<F12>", self.toggle_debug)

    def toggle_debug(self, event=None):
        self.debug_enabled = not self.debug_enabled
        if self.debug_enabled:
            self.update_overlays_loop()
        else:
            self.remove_overlays()

    def update_overlays_loop(self):
        self.remove_overlays()
        self.create_overlays(self.root)
        if self.debug_enabled:
            self.root.after(500, self.update_overlays_loop)

    def create_overlays(self, widget):
        for child in widget.winfo_children():
            self.add_overlay(child)
            self.create_overlays(child)

    def add_overlay(self, widget):
        try:
            widget.update_idletasks()

            x = widget.winfo_x()
            y = widget.winfo_y()
            w = widget.winfo_width()
            h = widget.winfo_height()
            parent = widget.nametowidget(widget.winfo_parent())

            overlay = tk.Frame(parent, bg="", highlightbackground="red", highlightthickness=2)
            overlay.place(x=x, y=y, width=w, height=h)
            overlay.lift(widget)

            widget_name = getattr(widget, "_name", widget.__class__.__name__)
            overlay.bind("<Enter>", lambda e, w=widget, name=widget_name: self.show_tooltip(e, w, name))
            overlay.bind("<Leave>", self.hide_tooltip)

            self.overlays.append(overlay)
        except Exception as e:
            print(f"[Overlay Error] {e}")

    def remove_overlays(self):
        for overlay in self.overlays:
            overlay.destroy()
        self.overlays.clear()
        self.hide_tooltip()

    def show_tooltip(self, event, widget, name):
        x, y = event.x_root + 10, event.y_root + 10
        class_name = widget.__class__.__name__
        dims = f"{widget.winfo_width()}x{widget.winfo_height()}"
        text = f"{name}  [{class_name}]  {dims}"

        self.tooltip = tk.Toplevel(self.root)
        self.tooltip.overrideredirect(True)
        self.tooltip.geometry(f"+{x}+{y}")
        label = tk.Label(self.tooltip, text=text, bg="yellow", fg="black", font=("Arial", 9))
        label.pack()

    def hide_tooltip(self, event=None):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None
