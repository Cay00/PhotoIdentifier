import os
import json
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk, ImageOps, ImageDraw, ImageFont


class PhotoTagger:
    def __init__(self, root):
        self.root = root
        self.root.title("Photo Tagger")

        self.folder = ""
        self.photos = []
        self.index = 0
        self.data = []

        # obraz i zoom
        self.orig_image = None
        self.tk_image = None
        self.scale = 1.0

        # globalna baza: osoba -> zbiór nazw plików, w których wystąpiła
        self.people_index = {}

        # czcionka do etykiet z przezroczystością (renderowane przez PIL)
        self.label_font = self.load_label_font()
        self.label_images = {}  # tag -> (obraz_50%, obraz_100%) - referencje trzymane żywo

        # ---------- obszar zdjęcia (canvas + scrollbary) ----------
        canvas_frame = tk.Frame(root)
        canvas_frame.pack(side="left", fill="both", expand=True)
        canvas_frame.rowconfigure(0, weight=1)
        canvas_frame.columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(canvas_frame, bg="gray20")
        vbar = tk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        hbar = tk.Scrollbar(canvas_frame, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=vbar.set, xscrollcommand=hbar.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        vbar.grid(row=0, column=1, sticky="ns")
        hbar.grid(row=1, column=0, sticky="ew")

        # lewy klik = dodaj tag, prawy klik = usuń najbliższy tag
        self.canvas.bind("<Button-1>", self.click)
        self.canvas.bind("<Button-3>", self.right_click_delete)

        # scroll = zoom (wyśrodkowany na kursorze)
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)
        self.canvas.bind("<Button-4>", self.on_mousewheel)
        self.canvas.bind("<Button-5>", self.on_mousewheel)

        # środkowy przycisk = przesuwanie widoku (panning)
        self.canvas.bind("<ButtonPress-2>", lambda e: self.canvas.scan_mark(e.x, e.y))
        self.canvas.bind("<B2-Motion>", lambda e: self.canvas.scan_dragto(e.x, e.y, gain=1))

        # ---------- panel boczny ----------
        panel = tk.Frame(root, width=280)
        panel.pack(side="right", fill="y")

        tk.Button(panel, text="Otwórz folder", command=self.open_folder).pack(fill="x")
        tk.Button(panel, text="◀ Poprzednie", command=self.prev).pack(fill="x")
        tk.Button(panel, text="Następne ▶", command=self.next).pack(fill="x")
        tk.Button(panel, text="Zapisz", command=self.save).pack(fill="x")

        zoom_frame = tk.Frame(panel)
        zoom_frame.pack(fill="x", pady=(5, 0))
        tk.Button(zoom_frame, text="Zoom −", command=lambda: self.zoom(0.8)).pack(side="left", expand=True, fill="x")
        tk.Button(zoom_frame, text="Zoom +", command=lambda: self.zoom(1.25)).pack(side="left", expand=True, fill="x")
        tk.Button(panel, text="Dopasuj do panelu", command=self.fit_to_panel).pack(fill="x", pady=(0, 5))

        tk.Label(panel, text="Osoby na zdjęciu").pack()
        self.info = tk.Listbox(panel, height=8)
        self.info.pack(fill="both", expand=False)
        self.info.bind("<Delete>", lambda e: self.delete_selected())
        self.info.bind("<BackSpace>", lambda e: self.delete_selected())

        tk.Button(panel, text="Usuń zaznaczoną osobę", command=self.delete_selected).pack(fill="x", pady=(2, 5))

        tk.Frame(panel, height=2, bd=1, relief="sunken").pack(fill="x", pady=8)

        tk.Label(panel, text="Szukaj osoby").pack()
        self.search_entry = tk.Entry(panel)
        self.search_entry.pack(fill="x")
        self.search_entry.bind("<KeyRelease>", self.on_search)

        tk.Label(panel, text="Pasujące osoby").pack()
        self.name_listbox = tk.Listbox(panel, height=6)
        self.name_listbox.pack(fill="both", expand=False)
        self.name_listbox.bind("<<ListboxSelect>>", self.on_name_select)

        tk.Label(panel, text="Zdjęcia tej osoby (dwuklik = przejdź)").pack()
        self.photo_listbox = tk.Listbox(panel, height=8)
        self.photo_listbox.pack(fill="both", expand=True)
        self.photo_listbox.bind("<Double-Button-1>", self.on_photo_select)

    # ================= czcionka / renderowanie etykiet =================

    def load_label_font(self, size=14):
        candidates = [
            "DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "arialbd.ttf",
            "Arial Bold.ttf",
        ]
        for name in candidates:
            try:
                return ImageFont.truetype(name, size)
            except Exception:
                continue
        return ImageFont.load_default()

    def render_label_image(self, text, opacity):
        # opacity: 0-255. Renderuje tekst na przezroczystym tle z realną alfą.
        dummy = Image.new("RGBA", (1, 1))
        d = ImageDraw.Draw(dummy)
        bbox = d.textbbox((0, 0), text, font=self.label_font)
        w = (bbox[2] - bbox[0]) + 4
        h = (bbox[3] - bbox[1]) + 4

        img = Image.new("RGBA", (max(1, w), max(1, h)), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.text((2 - bbox[0], 2 - bbox[1]), text, font=self.label_font, fill=(255, 0, 0, opacity))
        return ImageTk.PhotoImage(img)

    # ================= indeks osoba -> zdjęcia =================

    def rebuild_index(self):
        self.people_index = {}
        for fname in self.photos:
            name = os.path.splitext(fname)[0]
            data_file = os.path.join(self.folder, name + "-data.txt")
            if os.path.exists(data_file):
                try:
                    with open(data_file, encoding="utf-8") as f:
                        entries = json.load(f)
                    for p in entries:
                        person = p.get("person")
                        if person:
                            self.people_index.setdefault(person, set()).add(fname)
                except (json.JSONDecodeError, OSError):
                    pass

    def update_index_for_photo(self, filename, entries):
        for person in list(self.people_index.keys()):
            self.people_index[person].discard(filename)
            if not self.people_index[person]:
                del self.people_index[person]
        for p in entries:
            person = p.get("person")
            if person:
                self.people_index.setdefault(person, set()).add(filename)

    # ================= wyszukiwarka osób =================

    def on_search(self, event=None):
        text = self.search_entry.get().strip().lower()
        self.name_listbox.delete(0, tk.END)
        self.photo_listbox.delete(0, tk.END)
        if not text:
            return
        matches = sorted(n for n in self.people_index if text in n.lower())
        for m in matches:
            self.name_listbox.insert(tk.END, m)
        exact = [n for n in self.people_index if n.lower() == text]
        if exact:
            self.show_photos_for(exact[0])

    def on_name_select(self, event=None):
        sel = self.name_listbox.curselection()
        if not sel:
            return
        self.show_photos_for(self.name_listbox.get(sel[0]))

    def show_photos_for(self, name):
        self.photo_listbox.delete(0, tk.END)
        for f in sorted(self.people_index.get(name, [])):
            self.photo_listbox.insert(tk.END, f)

    def on_photo_select(self, event=None):
        sel = self.photo_listbox.curselection()
        if not sel:
            return
        filename = self.photo_listbox.get(sel[0])
        if filename in self.photos:
            self.save()
            self.index = self.photos.index(filename)
            self.load()

    # ================= dialog z podpowiedziami =================

    def ask_person(self):
        result = {"value": None}
        all_names = sorted(self.people_index.keys())

        top = tk.Toplevel(self.root)
        top.title("Osoba")
        top.transient(self.root)
        top.grab_set()

        tk.Label(top, text="Podaj dane osoby:").pack(padx=10, pady=(10, 0))

        entry = tk.Entry(top, width=30)
        entry.pack(padx=10, pady=5)
        entry.focus_set()

        listbox = tk.Listbox(top, height=6, width=30)
        listbox.pack(padx=10, pady=(0, 10))

        def update_suggestions(event=None):
            text = entry.get().strip().lower()
            listbox.delete(0, tk.END)
            if not text:
                return
            for m in all_names:
                if text in m.lower():
                    listbox.insert(tk.END, m)

        def on_listbox_pick(event=None):
            sel = listbox.curselection()
            if sel:
                entry.delete(0, tk.END)
                entry.insert(0, listbox.get(sel[0]))
                entry.icursor(tk.END)

        def confirm(event=None):
            sel = listbox.curselection()
            if sel:
                result["value"] = listbox.get(sel[0])
            else:
                val = entry.get().strip()
                result["value"] = val if val else None
            top.destroy()

        def cancel(event=None):
            result["value"] = None
            top.destroy()

        def move(delta):
            if listbox.size() == 0:
                return
            cur = listbox.curselection()
            idx = (cur[0] + delta) if cur else 0
            idx = max(0, min(listbox.size() - 1, idx))
            listbox.selection_clear(0, tk.END)
            listbox.selection_set(idx)
            listbox.activate(idx)
            listbox.see(idx)

        entry.bind("<KeyRelease>", update_suggestions)
        entry.bind("<Return>", confirm)
        entry.bind("<Escape>", cancel)
        entry.bind("<Down>", lambda e: move(1))
        entry.bind("<Up>", lambda e: move(-1))
        listbox.bind("<ButtonRelease-1>", on_listbox_pick)
        listbox.bind("<Double-Button-1>", confirm)
        listbox.bind("<Return>", confirm)
        top.protocol("WM_DELETE_WINDOW", cancel)

        self.root.wait_window(top)
        return result["value"]

    # ================= folder / nawigacja =================

    def open_folder(self):
        self.folder = filedialog.askdirectory()
        if not self.folder:
            return

        self.photos = [
            x for x in os.listdir(self.folder)
            if x.lower().endswith((".jpg", ".jpeg", ".png"))
        ]
        self.photos.sort()
        self.index = 0
        self.rebuild_index()
        self.load()

    def load(self):
        if not self.photos:
            return

        self.data = []
        filename = self.photos[self.index]
        path = os.path.join(self.folder, filename)

        self.orig_image = Image.open(path)
        self.orig_image = ImageOps.exif_transpose(self.orig_image)

        self.load_data()
        self.fit_to_panel()
        self.update_list()

        self.root.title(f"Photo Tagger - {filename} ({self.index + 1}/{len(self.photos)})")

    def prev(self):
        self.save()
        if self.index > 0:
            self.index -= 1
            self.load()

    def next(self):
        self.save()
        if self.index < len(self.photos) - 1:
            self.index += 1
            self.load()

    # ================= zoom / render =================

    def fit_to_panel(self):
        if self.orig_image is None:
            return
        self.canvas.update_idletasks()
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw < 10 or ch < 10:
            cw, ch = 900, 700
        iw, ih = self.orig_image.size
        self.scale = min(cw / iw, ch / ih)
        self.render_image()

    def zoom(self, factor):
        # zoom z przycisków - wyśrodkowany na środku widocznego obszaru
        if self.orig_image is None:
            return
        cw = self.canvas.winfo_width() or 900
        ch = self.canvas.winfo_height() or 700
        fake_event = type("E", (), {"x": cw // 2, "y": ch // 2, "delta": 0, "num": None})()
        self.zoom_at(factor, fake_event)

    def zoom_at(self, factor, event):
        if self.orig_image is None:
            return

        old_scale = self.scale
        new_scale = max(0.05, min(old_scale * factor, 8.0))
        if new_scale == old_scale:
            return

        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        ox = cx / old_scale
        oy = cy / old_scale

        self.scale = new_scale
        self.render_image()

        iw, ih = self.orig_image.size
        dw = iw * new_scale
        dh = ih * new_scale

        new_cx = ox * new_scale
        new_cy = oy * new_scale

        frac_x = (new_cx - event.x) / dw if dw > 0 else 0
        frac_y = (new_cy - event.y) / dh if dh > 0 else 0
        frac_x = max(0, min(1, frac_x))
        frac_y = max(0, min(1, frac_y))

        self.canvas.xview_moveto(frac_x)
        self.canvas.yview_moveto(frac_y)

    def render_image(self):
        iw, ih = self.orig_image.size
        dw = max(1, int(iw * self.scale))
        dh = max(1, int(ih * self.scale))

        resized = self.orig_image.resize((dw, dh), Image.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(resized)

        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self.tk_image, anchor="nw")
        self.canvas.configure(scrollregion=(0, 0, dw, dh))

        self.draw_points()

    def on_mousewheel(self, event):
        if getattr(event, "num", None) == 4:
            self.zoom_at(1.1, event)
        elif getattr(event, "num", None) == 5:
            self.zoom_at(0.9, event)
        else:
            factor = 1.1 if event.delta > 0 else 0.9
            self.zoom_at(factor, event)

    # ================= punkty / osoby na zdjęciu =================

    def click(self, event):
        if self.orig_image is None:
            return

        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        x = cx / self.scale
        y = cy / self.scale

        iw, ih = self.orig_image.size
        if x < 0 or y < 0 or x > iw or y > ih:
            return

        name = self.ask_person()

        if name:
            self.data.append({"x": x, "y": y, "person": name})
            self.save()
            self.draw_points()
            self.update_list()

    def right_click_delete(self, event):
        if not self.data:
            return

        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        x = cx / self.scale
        y = cy / self.scale

        threshold = 15 / self.scale
        best_idx = None
        best_dist = None
        for i, p in enumerate(self.data):
            d = ((p["x"] - x) ** 2 + (p["y"] - y) ** 2) ** 0.5
            if d <= threshold and (best_dist is None or d < best_dist):
                best_dist = d
                best_idx = i

        if best_idx is not None:
            del self.data[best_idx]
            self.save()
            self.draw_points()
            self.update_list()

    def delete_selected(self):
        sel = self.info.curselection()
        if not sel:
            return
        idx = sel[0]
        del self.data[idx]
        self.save()
        self.draw_points()
        self.update_list()

    def draw_points(self):
        self.canvas.delete("point")
        self.label_images = {}

        for i, p in enumerate(self.data):
            x = p["x"] * self.scale
            y = p["y"] * self.scale
            tag = f"point_{i}"

            dot_id = self.canvas.create_oval(
                x - 6, y - 6, x + 6, y + 6,
                fill="red", outline="",
                tags=("point", "dot", tag)
            )

            half_img = self.render_label_image(p["person"], 128)   # 50%
            full_img = self.render_label_image(p["person"], 255)   # 100%
            self.label_images[tag] = (half_img, full_img)

            label_id = self.canvas.create_image(
                x + 10, y,
                image=half_img, anchor="w",
                tags=("point", "label", tag)
            )

            self.canvas.tag_bind(
                tag, "<Enter>",
                lambda e, t=tag, d=dot_id, l=label_id: self.highlight_point(t, d, l, True)
            )
            self.canvas.tag_bind(
                tag, "<Leave>",
                lambda e, t=tag, d=dot_id, l=label_id: self.highlight_point(t, d, l, False)
            )

    def highlight_point(self, tag, dot_id, label_id, on):
        self.canvas.itemconfig(dot_id, fill="green" if on else "red")
        half_img, full_img = self.label_images[tag]
        self.canvas.itemconfig(label_id, image=full_img if on else half_img)

    def update_list(self):
        self.info.delete(0, tk.END)
        for i, p in enumerate(self.data, 1):
            self.info.insert(tk.END, f"{i}. {p['person']}")

    # ================= zapis / odczyt danych zdjęcia =================

    def save(self):
        if not self.photos:
            return

        filename = self.photos[self.index]
        name = os.path.splitext(filename)[0]
        file = os.path.join(self.folder, name + "-data.txt")

        if not self.data:
            if os.path.exists(file):
                os.remove(file)
        else:
            with open(file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)

        self.update_index_for_photo(filename, self.data)

    def load_data(self):
        name = os.path.splitext(self.photos[self.index])[0]
        file = os.path.join(self.folder, name + "-data.txt")

        if os.path.exists(file):
            with open(file, encoding="utf-8") as f:
                self.data = json.load(f)


root = tk.Tk()
root.geometry("1200x800")
app = PhotoTagger(root)
root.mainloop()