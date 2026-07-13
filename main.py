import os
import json
import tkinter as tk
from tkinter import filedialog, simpledialog
from PIL import Image, ImageTk, ImageOps


class PhotoTagger:
    def __init__(self, root):
        self.root = root
        self.root.title("Photo Tagger")

        self.folder = ""
        self.photos = []
        self.index = 0
        self.data = []
        self.points = []

        self.canvas = tk.Canvas(root, width=900, height=700)
        self.canvas.pack(side="left", fill="both", expand=True)

        panel = tk.Frame(root, width=250)
        panel.pack(side="right", fill="y")

        tk.Button(panel, text="Otwórz folder", command=self.open_folder).pack(fill="x")
        tk.Button(panel, text="◀ Poprzednie", command=self.prev).pack(fill="x")
        tk.Button(panel, text="Następne ▶", command=self.next).pack(fill="x")
        tk.Button(panel, text="Zapisz", command=self.save).pack(fill="x")

        tk.Label(panel, text="Osoby na zdjęciu").pack()

        self.info = tk.Listbox(panel)
        self.info.pack(fill="both", expand=True)

        self.canvas.bind("<Button-1>", self.click)

        self.image = None
        self.tk_image = None

    def update_list(self):
        self.info.delete(0, tk.END)
        for i, p in enumerate(self.data, 1):
            self.info.insert(tk.END, f"{i}. {p['person']}")

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
        self.load()

    def load(self):
        if not self.photos:
            return

        self.data = []
        self.points = []

        filename = self.photos[self.index]
        path = os.path.join(self.folder, filename)

        self.image = Image.open(path)
        self.image = ImageOps.exif_transpose(self.image)
        self.image.thumbnail((900, 700))

        self.tk_image = ImageTk.PhotoImage(self.image)

        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self.tk_image, anchor="nw")

        self.load_data()
        self.draw_points()
        self.update_list()

    def click(self, event):
        x, y = event.x, event.y

        name = simpledialog.askstring(
            "Osoba",
            "Podaj dane osoby:"
        )

        if name:
            self.data.append({
                "x": x,
                "y": y,
                "person": name
            })

            self.save()
            self.draw_points()

    def draw_points(self):
        for p in self.data:
            x = p["x"]
            y = p["y"]

            self.canvas.create_oval(
                x-5, y-5,
                x+5, y+5,
                outline="red",
                width=2
            )

            self.canvas.create_text(
                x + 10,
                y,
                text=p["person"],
                anchor="w",
                fill="red",
                font=("Arial", 10, "bold")
            )

    def save(self):
        if not self.photos:
            return

        name = os.path.splitext(self.photos[self.index])[0]
        file = os.path.join(self.folder, name + "-data.txt")

        if not self.data:
            if os.path.exists(file):
                os.remove(file)
            return

        with open(file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def load_data(self):
        name = os.path.splitext(self.photos[self.index])[0]

        file = os.path.join(
            self.folder,
            name + "-data.txt"
        )

        if os.path.exists(file):
            with open(file, encoding="utf-8") as f:
                self.data = json.load(f)

    def prev(self):
        self.save()

        if self.index > 0:
            self.index -= 1
            self.load()

    def next(self):
        self.save()

        if self.index < len(self.photos)-1:
            self.index += 1
            self.load()


root = tk.Tk()
app = PhotoTagger(root)
root.mainloop()