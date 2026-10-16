"""
Eurostat API data retrieval application
============================
Author: David Chaloupka
============================

A small GUI application that lets:
  1. Enter a Eurostat database code (e.g. "lfsq_eegais").
  2. Load that database's dimensions/parameters without downloading the whole dataset directly (databases can be huge).
  3. Filter every parameter by selecting one or several codelist values from a multi-select list.
  4. Fetch only the filtered subset via eurostat.get_data() function.
  5. Download the resulting DataFrame to a single .xlsx file stored in the same folder as this script.
  * Quit/terminate the program from a button in the bottom corner if needed anytime.
"""

import os
import threading
import sys
from datetime import datetime
import json

from src.eurostat_utils import fetch_dimensions, fetch_codelist, fetch_data, to_eurostat_period, melt_to_panel

from src.helpers import _ensure, output_folder, dim_display_name, value_label, _flatten_leaves

# Install any that are missing (import name, pip name)
if not getattr(sys, "frozen", False):
    _ensure("numpy", "numpy")
    _ensure("PIL", "pillow")
    _ensure("openpyxl", "openpyxl")
    _ensure("eurostat", "eurostat")

import pandas as pd

import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ==========================================================================
# GUI
# ==========================================================================
class EurostatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Eurostat API data retrieval")
        self.root.geometry("1032x768")
        self.root.minsize(864, 624)

        self.db_name = None
        self.dimensions = []
        self.check_vars = {}
        self.current_df = None

        BG, TEXT, ACCENT = "#E6EBF4", "#00235A", "#003299"
        root.configure(bg=BG)
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", background=BG, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("TFrame", background=BG)
        style.configure("TLabelframe", background=BG, bordercolor="#4D74B4")
        style.configure("TLabelframe.Label", background=BG, foreground=TEXT)
        style.configure("TCheckbutton", background=BG)
        style.configure("TButton", padding=(12, 6))
        style.map("TButton", background=[("active", "#99AFD4")])
        style.configure("Accent.TButton", foreground="white", background=ACCENT)
        style.map("Accent.TButton", background=[("active", "#1e40af")])
        style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"), background=BG)
        style.configure("Demo.TLabel", foreground="#FF4B00", font=("Segoe UI", 9, "bold"))
        style.configure("Treeview", rowheight=24, fieldbackground="white")
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))

        self.container = ttk.Frame(root, padding=0)
        self.container.pack(fill="both", expand=True)

        self.page_db = ttk.Frame(self.container, padding=20)
        self.page_filter = ttk.Frame(self.container, padding=20)
        for page in (self.page_db, self.page_filter):
            page.grid(row=0, column=0, sticky="nsew")
        self.container.rowconfigure(0, weight=1)
        self.container.columnconfigure(0, weight=1)

        self._build_page_db()
        self._build_page_filter()
        self._show(self.page_db)

    def _show(self, page):
        page.tkraise()

    def _run_async(self, work, on_ok, on_err):
        """Run `work()` off the main thread, deliver result back on the GUI thread."""
        def worker():
            try:
                result = work()
            except Exception as exc: 
                self.root.after(0, lambda e=exc: on_err(e))
                return
            self.root.after(0, lambda: on_ok(result))
        threading.Thread(target=worker, daemon=True).start()

    def _quit(self):
        self.root.destroy()

    # ----------------  FIRST PAGE  -------------------------------------------- 
    def _build_page_db(self):
            p = self.page_db

            bottom = ttk.Frame(p)
            bottom.pack(side="bottom", fill="x", pady=(20, 0))
            ttk.Button(bottom, text="Quit / terminate", command=self._quit).pack(side="right")
            ttk.Label(bottom, text="David Chaloupka | v0.1", foreground="#99AFD4").pack(side="left")

            # Centered content block.
            center = ttk.Frame(p)
            center.pack(expand=True)

            # Header image
            img_path = os.path.join(BASE_DIR, "src", "icons", "title.png")
            img = Image.open(img_path)
            max_w = 700
            ratio = max_w / img.width
            img = img.resize((max_w, int(img.height * ratio)), Image.LANCZOS)
            self.header_img = ImageTk.PhotoImage(img)
            ttk.Label(center, image=self.header_img).pack(pady=(0, 12))

            ttk.Label(center, text="Eurostat API data retrieval", style="Title.TLabel").pack()
            ttk.Label(center, text="Step 1 - Enter the Eurostat database code you want to work on.",
            ).pack(pady=(6, 18))

            form = ttk.Frame(center)
            form.pack()
            ttk.Label(form, text="Database code:").grid(row=0, column=0, padx=(0, 8), pady=4, sticky="w")
            self.db_entry = ttk.Entry(form, width=32)
            self.db_entry.grid(row=0, column=1, pady=4)
            self.db_entry.bind("<Return>", lambda _e: self._load_dimensions())
            self.search_btn = ttk.Button(form, text="Search\u2026", command=self._open_search)
            self.search_btn.grid(row=0, column=2, padx=(8, 0), pady=4)
            self.load_btn = ttk.Button(form, text="Load database  →", command=self._load_dimensions)
            self.load_btn.grid(row=0, column=3, padx=(10, 0), pady=4)

            self.db_status = ttk.Label(center, text="", foreground="#003299")
            self.db_status.pack(pady=(14, 0))

    # ----------------  DATABASE SEARCHING WINDOW  -------------------------------------------- 
    def _load_db_dict(self):
        """Load the Eurostat database tree from the P: drive."""
        try:
            with open(os.path.join(BASE_DIR, "src", "create dictionaries", "database dictionary", "database_dictionary.json"), encoding="utf-8") as f:
                self._db_dict = json.load(f)
        except Exception as e:
            messagebox.showerror("Search unavailable",
                                 f"Could not load the database list:\n{e}")
            self._db_dict = []
        return self._db_dict

    def _open_search(self):
        db_dict = self._load_db_dict()
        if not db_dict:
            return

        flat_leaves = []
        _flatten_leaves(db_dict, flat_leaves)

        win = tk.Toplevel(self.root)
        win.title("Search Eurostat databases")
        win.geometry("780x620")
        win.transient(self.root)

        # search bar
        top = ttk.Frame(win, padding=10)
        top.pack(fill="x")
        ttk.Label(top, text="Search:").pack(side="left")
        search_var = tk.StringVar()
        search_entry = ttk.Entry(top, textvariable=search_var)
        search_entry.pack(side="left", fill="x", expand=True, padx=(6, 0))
        search_entry.focus()

        info = ttk.Label(win, text="Browse the tree, or type to search. "
                                   "Double-click a dataset to select it.",
                         style="Muted.TLabel")
        info.pack(anchor="w", padx=10)

        # build tree
        mid = ttk.Frame(win, padding=(10, 6, 10, 10))
        mid.pack(fill="both", expand=True)
        tree = ttk.Treeview(mid, show="tree")
        vsb = ttk.Scrollbar(mid, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        tree.pack(side="left", fill="both", expand=True)

        node_by_iid = {}
        loaded = {}

        def insert_node(parent, node):
            is_folder = node.get("type") == "folder"
            title = node.get("title", "")
            code = node.get("code", "")
            if is_folder:
                iid = tree.insert(parent, "end", text=title, open=False)
                node_by_iid[iid] = node
                tree.insert(iid, "end", text="\u2026")
                loaded[iid] = False
            else:
                iid = tree.insert(parent, "end", text=f"{title}   ({code})")
                node_by_iid[iid] = node

        def build_tree():
            tree.delete(*tree.get_children())
            node_by_iid.clear()
            loaded.clear()
            for node in db_dict:
                insert_node("", node)

        def on_open(_e):
            iid = tree.focus()
            if loaded.get(iid) is False:
                for c in tree.get_children(iid):
                    tree.delete(c)
                for child in node_by_iid[iid].get("children", []):
                    insert_node(iid, child)
                loaded[iid] = True

        def run_search():
            q = search_var.get().strip().casefold()
            tree.delete(*tree.get_children())
            node_by_iid.clear()
            loaded.clear()
            if not q:
                build_tree()
                info.config(text="Browse the tree, or type to search. "
                                 "Double-click a dataset to select it.")
                return
            matches = [n for n in flat_leaves
                       if q in n.get("title", "").casefold()
                       or q in n.get("code", "").casefold()]
            cap = 500
            for n in matches[:cap]:
                iid = tree.insert("", "end",
                                  text=f'{n.get("title","")}   ({n.get("code","")})')
                node_by_iid[iid] = n
            extra = f" (showing first {cap})" if len(matches) > cap else ""
            info.config(text=f"{len(matches)} match(es){extra}. Double-click one to select it.")

        self._search_after = None

        def schedule(*_):
            if self._search_after:
                win.after_cancel(self._search_after)
            self._search_after = win.after(150, run_search)

        def choose(node):
            code = node.get("code", "")
            if not code:
                return
            self.db_entry.delete(0, tk.END)
            self.db_entry.insert(0, code)
            win.destroy()

        def on_double(_e):
            iid = tree.focus()
            node = node_by_iid.get(iid)
            if not node:
                return
            if node.get("type") == "folder":
                return
            choose(node)
            return "break"

        search_var.trace_add("write", schedule)
        tree.bind("<<TreeviewOpen>>", on_open)
        tree.bind("<Double-1>", on_double)

        # buttons
        bar = ttk.Frame(win, padding=(10, 0, 10, 10))
        bar.pack(fill="x")

        def select_current():
            node = node_by_iid.get(tree.focus())
            if node and node.get("type") != "folder":
                choose(node)
        ttk.Button(bar, text="Select", command=select_current,
                   style="Accent.TButton").pack(side="right")
        ttk.Button(bar, text="Cancel", command=win.destroy).pack(side="right", padx=(0, 8))

        build_tree()
        win.grab_set()

    #################### CONTINUE FIRST PAGE ####################

    def _load_dimensions(self):
        db = self.db_entry.get().strip()
        if not db:
            messagebox.showwarning("Missing input", "Please enter a database code.")
            return
        self.db_name = db
        self.load_btn.config(state="disabled")
        self.db_status.config(text=f"Connecting to '{db}' database …")

        def work():
            dims = fetch_dimensions(db)
            codelists = {d: fetch_codelist(db, d) for d in dims}
            return dims, codelists
        self._run_async(work, self._on_dimensions_ok, self._on_dimensions_err)

    def _on_dimensions_ok(self, result):
        dims, codelists = result
        self.dimensions = dims
        self.load_btn.config(state="normal")
        self.db_status.config(text="")
        self._populate_filters(dims, codelists)
        self._show(self.page_filter)

    def _on_dimensions_err(self, exc):
        self.load_btn.config(state="normal")
        self.db_status.config(text="")
        messagebox.showerror("Error", "Could not load database.")

    # ----------------  SECOND PAGE  --------------------------------------------

    def _build_page_filter(self):
        p = self.page_filter

        header = ttk.Frame(p)
        header.pack(fill="x")
        ttk.Label(header, text="Step 2 - Filter parameters", style="Title.TLabel").pack(side="left")
        self.filter_db_label = ttk.Label(header, text="", foreground="#555")
        self.filter_db_label.pack(side="left", padx=12)
        ttk.Button(header, text="←  Back", command=lambda: self._show(self.page_db)).pack(side="right")

        ttk.Label(
            p,
            text="Select one or several values per parameter. "
                 "Parameters left empty are downloaded in full.",
        ).pack(anchor="w", pady=(6, 10))

        tf = ttk.LabelFrame(p, text="Time filter (optional)", padding=8)
        tf.pack(fill="x", pady=(0, 10))
        ttk.Label(tf, text="From:").grid(row=0, column=0, padx=(0, 4), sticky="w")
        self.time_start_entry = ttk.Entry(tf, width=14)
        self.time_start_entry.grid(row=0, column=1, padx=(0, 12))
        ttk.Label(tf, text="To:").grid(row=0, column=2, padx=(0, 4), sticky="w")
        self.time_end_entry = ttk.Entry(tf, width=14)
        self.time_end_entry.grid(row=0, column=3, padx=(0, 12))
        ttk.Label(tf, text="Period type:").grid(row=0, column=4, padx=(0, 4), sticky="w")
        self.time_ptype = ttk.Combobox(
            tf, width=18, state="readonly",
            values=["Annual (year only)", "Quarterly", "Monthly", "Daily"],
        )
        self.time_ptype.set("Annual (year only)")
        self.time_ptype.grid(row=0, column=5)
        ttk.Label(
            tf,
            text="dd/mm/yyyy (or a native period like 2019, 2019-Q1, 2019-M03). "
                 "Leave blank for no bound.",
            foreground="#666",
        ).grid(row=1, column=0, columnspan=6, sticky="w", pady=(6, 0))

        # Scrollable area holding one multi-select list per dimension.
        outer = ttk.Frame(p)
        outer.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(outer, highlightthickness=0)
        vsb = ttk.Scrollbar(outer, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.canvas.bind(
            "<Enter>",
            lambda _e: self.canvas.bind_all(
                "<MouseWheel>",
                lambda ev: self.canvas.yview_scroll(int(-ev.delta / 120), "units")))
        self.canvas.bind("<Leave>", lambda _e: self.canvas.unbind_all("<MouseWheel>"))

        self.filters_frame = ttk.Frame(self.canvas)
        self._filters_window = self.canvas.create_window((0, 0), window=self.filters_frame, anchor="nw")
        self.filters_frame.bind(
            "<Configure>",
            lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfigure(self._filters_window, width=e.width),
        )

        # Action bar
        actions = ttk.Frame(p)
        actions.pack(fill="x", pady=(12, 4))
        self.apply_btn = ttk.Button(actions, text="Apply filters & fetch data", command=self._apply_filters, style="Accent.TButton")
        self.apply_btn.pack(side="left")
        self.panel_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(actions, text="Panel data format", variable=self.panel_var).pack(side="left", padx=(10, 0))
        self.download_btn = ttk.Button(actions, text="Download to Excel", command=self._download, state="disabled")
        self.download_btn.pack(side="left", padx=(10, 0))
        self.fetch_status = ttk.Label(actions, text="", foreground="#003299")
        self.fetch_status.pack(side="left", padx=12)
        ttk.Button(actions, text="Quit / terminate", command=self._quit).pack(side="right")

        credit_bar = ttk.Frame(p)
        credit_bar.pack(side="bottom", fill="x", pady=(6, 0))
        ttk.Label(credit_bar, text="David Chaloupka | v0.1", foreground="#99AFD4").pack(side="left")

        # Preview of fetched data
        prev = ttk.LabelFrame(p, text="Preview (first 50 rows)", padding=6)
        prev.pack(fill="both", expand=True, pady=(6, 0))
        self.tree = ttk.Treeview(prev, show="headings", height=8)
        tree_vsb = ttk.Scrollbar(prev, orient="vertical", command=self.tree.yview)
        tree_hsb = ttk.Scrollbar(prev, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=tree_vsb.set, xscrollcommand=tree_hsb.set)
        tree_vsb.pack(side="right", fill="y")
        tree_hsb.pack(side="bottom", fill="x")
        self.tree.pack(side="left", fill="both", expand=True)

    def _populate_filters(self, dims, codelists):
            # Clear any previous widgets/state
            for child in self.filters_frame.winfo_children():
                child.destroy()
            self.check_vars.clear()
            self.current_df = None
            self.download_btn.config(state="disabled")
            self.fetch_status.config(text="")
            self._clear_tree()
            self.filter_db_label.config(text=f"database: {self.db_name}")

            for dim in dims:
                if str(dim).lower() in ("time", "time_period"):
                    continue
                # show parameters to filter on if len(values) in parameter is <2
                # values = codelists.get(dim,[])
                # if len(values) < 2:
                #    continue

                group = ttk.LabelFrame(self.filters_frame, text=dim_display_name(dim), padding=8)
                group.pack(fill="x", expand=True, pady=6)

                values = codelists.get(dim, [])
                vars_ = []

                # small toolbar: select all/clear + count
                bar = ttk.Frame(group)
                bar.pack(fill="x", pady=(0, 4))
                ttk.Button(bar, text="Select all", width=10,
                        command=lambda v=vars_: [bv.set(True) for _, bv in v]).pack(side="left")
                ttk.Button(bar, text="Clear", width=8,
                        command=lambda v=vars_: [bv.set(False) for _, bv in v]).pack(side="left", padx=(6, 0))
                ttk.Label(bar, text=f"{len(values)} values", foreground="#888").pack(side="right")

                # one tick box per value
                for code, label in values:
                    var = tk.BooleanVar(value=False)
                    full = value_label(dim, code, label)
                    display = code if code == full else f"[{code}]  {full}"
                    ttk.Checkbutton(group, text=display, variable=var).pack(anchor="w")
                    vars_.append((code, var))

                self.check_vars[dim] = vars_

    def _collect_filters(self):
        filters = {}
        for dim, vars_ in self.check_vars.items():
            chosen = [code for code, var in vars_ if var.get()]
            if chosen:
                filters[dim] = chosen
        ptype = self.time_ptype.get()
        start = to_eurostat_period(self.time_start_entry.get(), ptype)
        end = to_eurostat_period(self.time_end_entry.get(), ptype)
        if start is not None:
            filters["startPeriod"] = start
        if end is not None:
            filters["endPeriod"] = end
        return filters

    def _apply_filters(self):
        if not self.db_name:
            return
        try:
            filters = self._collect_filters()
        except ValueError as e:
            messagebox.showwarning("Invalid time filter", str(e))
            return
        self.apply_btn.config(state="disabled")
        if not self.db_name:
            return
        filters = self._collect_filters()
        self.apply_btn.config(state="disabled")
        self.download_btn.config(state="disabled")
        self.fetch_status.config(text="Fetching data …")

        db = self.db_name
        to_panel = self.panel_var.get()

        def work():
            df = fetch_data(db, filters)
            if to_panel:
                df = melt_to_panel(df)
            return df
        self._run_async(work, self._on_data_ok, self._on_data_err)

    def _on_data_ok(self, df):
        self.apply_btn.config(state="normal")
        if not isinstance(df, pd.DataFrame):
            df = pd.DataFrame(df)
        self.current_df = df
        self.fetch_status.config(text=f"Loaded {len(df):,} rows × {df.shape[1]} columns.")
        self._fill_tree(df)
        self.download_btn.config(state="normal" if len(df) else "disabled")

    def _on_data_err(self, exc):
        self.apply_btn.config(state="normal")
        self.fetch_status.config(text="")
        messagebox.showerror("Could not fetch data", f"{type(exc).__name__}: {exc}")

    # ----------------  PREVIEW TABLE  --------------------------------------------
    def _clear_tree(self):
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = ()

    def _fill_tree(self, df):
        self._clear_tree()
        cols = list(df.columns)
        self.tree["columns"] = cols
        for c in cols:
            self.tree.heading(c, text=str(c))
            self.tree.column(c, width=110, anchor="w", stretch=False)
        for _, row in df.head(50).iterrows():
            self.tree.insert("", tk.END, values=[row[c] for c in cols])

    # ----------------  EXCEL EXPORT  --------------------------------------------
    def _download(self):
        if self.current_df is None or self.current_df.empty:
            messagebox.showinfo("Nothing to download", "Fetch some data first.")
            return
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.db_name}_{stamp}.xlsx"
        path = os.path.join(output_folder(), filename)
        self.current_df.to_excel(path, index=False)
        messagebox.showinfo("Download complete", f"Saved to:\n{path}")

def main():
    root = tk.Tk()
    EurostatApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
