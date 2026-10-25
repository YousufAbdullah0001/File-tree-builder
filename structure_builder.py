"""
Folder Structure Builder - GUI
Parses tree-style text and creates folder/file structures.
"""

import re
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class StructureItem:
    path: str
    is_folder: bool


def parse_structure(text: str) -> tuple[Optional[str], list[StructureItem]]:
    """Parse tree-style text into (root, items)."""
    lines = text.strip().splitlines()
    if not lines:
        return None, []

    root = lines[0].strip().rstrip('/\\')
    items: list[StructureItem] = []
    stack: list[tuple[str, int]] = [(root, -1)]

    for line in lines[1:]:
        if not line.strip():
            continue

        match = re.search(r'[├└│─\s]+(.+)', line)
        if not match:
            continue

        name = match.group(1).strip()
        prefix = line[:match.start(1)]

        # Count indentation depth: each '│   ' or '    ' block = 1 level
        level = 0
        i = 0
        while i < len(prefix):
            if prefix[i:i+4] == '│   ':
                level += 1
                i += 4
            elif prefix[i:i+4] == '    ':
                level += 1
                i += 4
            elif prefix[i:i+3] in ('├──', '└──'):
                level += 1
                break
            else:
                i += 1

        while len(stack) > 1 and stack[-1][1] >= level:
            stack.pop()

        parent_path = stack[-1][0]
        is_folder = name.endswith('/') or name.endswith('\\')
        clean_name = name.rstrip('/\\')
        full_path = os.path.join(parent_path, clean_name)

        stack.append((full_path, level))
        items.append(StructureItem(path=full_path, is_folder=is_folder))

    return root, items


def create_structure(text: str, base_dir: str) -> list[str]:
    """Create the folder structure. Returns list of log messages."""
    root, items = parse_structure(text)
    if not root:
        return ["Error: No valid structure found."]

    log: list[str] = []
    root_path = Path(base_dir) / root
    root_path.mkdir(parents=True, exist_ok=True)
    log.append(f"Root: {root_path}")

    for item in items:
        full = Path(base_dir) / item.path
        if item.is_folder:
            full.mkdir(parents=True, exist_ok=True)
            log.append(f"  [DIR]  {full}")
        else:
            full.parent.mkdir(parents=True, exist_ok=True)
            if not full.exists():
                full.touch()
                log.append(f"  [FILE] {full}")
            else:
                log.append(f"  [SKIP] {full} (exists)")

    return log


def export_structure(dir_path: str) -> str:
    """Export an existing directory as tree text."""
    path = Path(dir_path)
    if not path.is_dir():
        return ""

    lines: list[str] = [path.name]

    def _walk(current: Path, prefix: str = ""):
        entries = sorted(
            [e for e in current.iterdir() if not e.name.startswith('.')],
            key=lambda e: (not e.is_dir(), e.name.lower())
        )
        for i, entry in enumerate(entries):
            is_last = i == len(entries) - 1
            connector = "└── " if is_last else "├── "
            suffix = "/" if entry.is_dir() else ""
            lines.append(f"{prefix}{connector}{entry.name}{suffix}")
            if entry.is_dir():
                extension = "    " if is_last else "│   "
                _walk(entry, prefix + extension)

    _walk(path)
    return "\n".join(lines)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Folder Structure Builder")
        self.geometry("800x600")
        self.minsize(600, 400)

        # Style
        style = ttk.Style(self)
        style.theme_use("clam")

        # Tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self._build_input_tab()
        self._build_preview_tab()
        self._build_export_tab()
        self._build_log_tab()

    def _build_input_tab(self):
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text="  Input  ")

        ttk.Label(frame, text="Paste tree structure or load from file:").pack(anchor=tk.W)

        # Toolbar
        toolbar = ttk.Frame(frame)
        toolbar.pack(fill=tk.X, pady=(8, 4))

        ttk.Button(toolbar, text="Load File", command=self._load_file).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="Clear", command=self._clear_input).pack(side=tk.LEFT, padx=4)
        ttk.Button(toolbar, text="Parse & Preview", command=self._parse_and_preview).pack(side=tk.RIGHT)

        # Text area
        text_frame = ttk.Frame(frame)
        text_frame.pack(fill=tk.BOTH, expand=True)

        self.input_text = tk.Text(text_frame, wrap=tk.NONE, font=("Consolas", 10))
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.input_text.yview)
        self.input_text.configure(yscrollcommand=scrollbar.set)

        self.input_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Placeholder
        self.input_text.insert(tk.END,
            "project/\n"
            "├── src/\n"
            "│   ├── main.py\n"
            "│   └── utils/\n"
            "│       └── helpers.py\n"
            "├── tests/\n"
            "│   └── test_main.py\n"
            "└── README.md\n")
        self.input_text.insert(tk.END,
    "project/\n"
    "├── src/\n"
    "│   ├── main.py\n"
    "│   └── utils/\n"
    "│       └── helpers.py\n"
    "├── tests/\n"
    "│   └── test_main.py\n"
    "└── README.md\n")

    def _build_preview_tab(self):
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text="  Preview  ")

        ttk.Label(frame, text="Parsed structure (read-only):").pack(anchor=tk.W)

        preview_frame = ttk.Frame(frame)
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=8)

        self.preview_text = tk.Text(preview_frame, state=tk.DISABLED, font=("Consolas", 10))
        p_scroll = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL, command=self.preview_text.yview)
        self.preview_text.configure(yscrollcommand=p_scroll.set)

        self.preview_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        p_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Create section
        create_frame = ttk.LabelFrame(frame, text="Create Structure", padding=10)
        create_frame.pack(fill=tk.X, pady=(8, 0))

        ttk.Label(create_frame, text="Base directory:").pack(side=tk.LEFT)
        self.base_dir_var = tk.StringVar(value=str(Path.cwd()))
        ttk.Entry(create_frame, textvariable=self.base_dir_var).pack(side=tk.LEFT, padx=8, fill=tk.X, expand=True)
        ttk.Button(create_frame, text="Browse...", command=self._browse_base_dir).pack(side=tk.LEFT, padx=4)
        ttk.Button(create_frame, text="Create", command=self._create, style="Accent.TButton").pack(side=tk.LEFT, padx=4)

    def _build_export_tab(self):
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text="  Export  ")

        ttk.Label(frame, text="Export an existing directory as tree text:").pack(anchor=tk.W)

        export_frame = ttk.LabelFrame(frame, text="Source Directory", padding=10)
        export_frame.pack(fill=tk.X, pady=8)

        ttk.Label(export_frame, text="Directory:").pack(side=tk.LEFT)
        self.export_dir_var = tk.StringVar()
        ttk.Entry(export_frame, textvariable=self.export_dir_var).pack(side=tk.LEFT, padx=8, fill=tk.X, expand=True)
        ttk.Button(export_frame, text="Browse...", command=self._browse_export_dir).pack(side=tk.LEFT, padx=4)
        ttk.Button(export_frame, text="Export", command=self._export).pack(side=tk.LEFT, padx=4)

        export_text_frame = ttk.Frame(frame)
        export_text_frame.pack(fill=tk.BOTH, expand=True)

        self.export_text = tk.Text(export_text_frame, font=("Consolas", 10))
        e_scroll = ttk.Scrollbar(export_text_frame, orient=tk.VERTICAL, command=self.export_text.yview)
        self.export_text.configure(yscrollcommand=e_scroll.set)

        self.export_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        e_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _build_log_tab(self):
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text="  Log  ")

        log_frame = ttk.Frame(frame)
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(log_frame, state=tk.DISABLED, font=("Consolas", 10))
        l_scroll = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=l_scroll.set)

        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        l_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    # --- Tab methods ---

    def _load_file(self):
        path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if path:
            self._set_input(Path(path).read_text(encoding="utf-8"))

    def _clear_input(self):
        self._set_input("")

    def _set_input(self, text: str):
        self.input_text.configure(state=tk.NORMAL)
        self.input_text.delete("1.0", tk.END)
        self.input_text.configure(state=tk.DISABLED)

    def _parse_and_preview(self):
        text = self.input_text.get("1.0", tk.END).strip()
        root, items = parse_structure(text)
        if not root:
            messagebox.showwarning("Parse Error", "No valid structure found.")
            return

        lines = [root]
        for item in items:
            lines.append(f"{item.path}  {'[DIR]' if item.is_folder else '[FILE]'}")

        self.preview_text.configure(state=tk.NORMAL)
        self.preview_text.delete("1.0", tk.END)
        self.preview_text.insert(tk.END, "\n".join(lines))
        self.preview_text.configure(state=tk.DISABLED)

        self.notebook.select(1)  # Switch to Preview tab

    def _browse_base_dir(self):
        d = filedialog.askdirectory()
        if d:
            self.base_dir_var.set(d)

    def _create(self):
        text = self.input_text.get("1.0", tk.END).strip()
        base = self.base_dir_var.get().strip()
        if not base:
            messagebox.showwarning("Missing", "Select a base directory.")
            return

        log = create_structure(text, base)
        self._show_log(log)
        self.notebook.select(3)

    def _browse_export_dir(self):
        d = filedialog.askdirectory()
        if d:
            self.export_dir_var.set(d)

    def _export(self):
        d = self.export_dir_var.get().strip()
        if not d:
            messagebox.showwarning("Missing", "Select a directory to export.")
            return
        result = export_structure(d)
        if not result:
            messagebox.showerror("Error", "Directory not found or empty.")
            return
        self.export_text.delete("1.0", tk.END)
        self.export_text.insert(tk.END, result)

    def _show_log(self, lines: list[str]):
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.insert(tk.END, "\n".join(lines) + "\n")
        self.log_text.configure(state=tk.DISABLED)


if __name__ == "__main__":
    app = App()
    app.mainloop()   