# PhotoIdentifier

A simple desktop application for tagging people in photos.

PhotoIdentifier lets you open a folder of photos, mark people directly on images, save annotations alongside each photo, and easily search for people across your entire photo collection.

## Features

- Open folders containing photos
- Navigate between images
- Add and remove person markers directly on images
- Save annotations for each photo in a separate `.txt` file
- Search for people by name
- Browse photos associated with a specific person
- Zoom in and out and pan across images

## Requirements

- Python 3.9+
- Pillow
- Tkinter (usually included with Python)

## Installation

1. Clone the repository:

```bash
git clone https://github.com/Cay00/PhotoIdentifier.git
cd PhotoIdentifier
```

2. Install the required dependency:

```bash
pip install pillow
```

## Running the Application

```bash
python main.py
```

## How to Use

1. Click `Open Folder` and select a directory containing your photos.
2. Click on an image to add a person marker.
3. Enter the person's name in the dialog box.
4. Right-click an existing marker to remove it.
5. Use the `Previous` and `Next` buttons to navigate between photos.
6. Annotations are saved automatically whenever a marker is added or removed.
