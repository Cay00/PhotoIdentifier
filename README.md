# PhotoIdentifier

Prosta aplikacja do oznaczania osób na zdjęciach.

Pozwala otworzyć folder z fotografiami, zaznaczać osoby na konkretnej ilustracji, zapisywać dane do plików obok zdjęć i łatwo przeszukiwać osoby w całym zbiorze.

## Funkcje

- otwieranie katalogu z zdjęciami
- przechodzenie pomiędzy zdjęciami
- dodawanie i usuwanie osób z zaznaczenia na obrazie
- zapis danych dla każdego zdjęcia w osobnym pliku `.txt`
- wyszukiwanie osób po nazwie
- podgląd zdjęć przypisanych do danej osoby
- zoom i przesuwanie obrazka

## Wymagania

- Python 3.9+
- biblioteka Pillow
- Tkinter (zwykle dołączony do instalacji Pythona)

## Instalacja

1. Sklonuj repozytorium:

```bash
git clone https://github.com/Cay00/PhotoIdentifier.git
cd PhotoIdentifier
```

2. Zainstaluj zależności:

```bash
pip install pillow
```

## Uruchomienie

```bash
python main.py
```

## Jak używać

1. Kliknij `Otwórz folder` i wybierz katalog ze zdjęciami.
2. Kliknij obrazek, aby dodać osobę.
3. Wpisz nazwę osoby w oknie dialogowym.
4. Kliknij prawym przyciskiem myszy na punkt, aby usunąć zaznaczenie.
5. Użyj przycisków `Poprzednie` i `Następne`, aby przechodzić między zdjęciami.
6. Zapis odbywa się automatycznie po dodaniu/usunięciu etykiety.

