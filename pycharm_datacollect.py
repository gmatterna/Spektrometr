import asyncio
from bleak import BleakClient
import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import interp1d

adres_urzadzenia = "50:33:8B:26:EC:9B"
uuid_charakterystyki = "0000ffe1-0000-1000-8000-00805f9b34fb"

dlugosci_fali = [405, 470, 505, 525, 590, 605, 637]
napiecia_szumu = []
napiecia_referencyjne = []
napiecia_probki = []
tryb_pomiaru = None
sredni_szum = 0


async def wyslij_komende(klient, komenda):
    await klient.write_gatt_char(uuid_charakterystyki, komenda.encode())
    print(f"Wysłano komendę: {komenda}")


def obsluga_powiadomienia(nadawca, dane):
    global napiecia_szumu, napiecia_referencyjne, napiecia_probki, tryb_pomiaru
    try:
        zdekodowane_dane = dane.decode("utf-8").strip()
        print(f"Odebrane dane: {zdekodowane_dane}")

        if tryb_pomiaru == "S":
            try:
                napiecie = float(zdekodowane_dane)
                napiecia_szumu.append(napiecie)
            except ValueError:
                print(f"Ignorowane dane: {zdekodowane_dane}")
        else:
            if "," in zdekodowane_dane:
                try:
                    indeks, napiecie = zdekodowane_dane.split(",")
                    indeks = int(indeks)
                    napiecie = float(napiecie)

                    if tryb_pomiaru == "R":
                        napiecia_referencyjne.append((dlugosci_fali[indeks], napiecie))
                    elif tryb_pomiaru == "P":
                        napiecia_probki.append((dlugosci_fali[indeks], napiecie))
                except ValueError:
                    print(f"Ignorowane dane: {zdekodowane_dane}")
    except Exception as e:
        print(f"Błąd dekodowania danych: {e}")


async def wykonaj_pomiar_szumu(klient):
    global tryb_pomiaru, sredni_szum, napiecia_szumu
    tryb_pomiaru = "S"
    napiecia_szumu.clear()
    print("Rozpoczynam pomiar szumu...")

    await wyslij_komende(klient, "S")

    await asyncio.sleep(3)

    if napiecia_szumu:
        sredni_szum = np.mean(napiecia_szumu)
        print(f"\nPomiar szumu zakończony. Średnia wartość szumu: {sredni_szum:.3f} V")
    else:
        print("\nBrak danych dla szumu.")


async def wykonaj_pomiar(klient, tryb):
    global tryb_pomiaru
    tryb_pomiaru = tryb

    if tryb == "R":
        napiecia_referencyjne.clear()
        print("Rozpoczynam pomiar referencji...")
    elif tryb == "P":
        napiecia_probki.clear()
        print("Rozpoczynam pomiar próbki właściwej...")

    await wyslij_komende(klient, tryb)

    await asyncio.sleep(10)

    if tryb == "R":
        if napiecia_referencyjne:
            print("\nWyniki pomiaru referencji:")
            for dlugosc, napiecie in napiecia_referencyjne:
                print(f"Długość fali: {dlugosc} nm - {napiecie:.3f} V")
        else:
            print("\nBrak danych dla referencji.")
    elif tryb == "P":
        if napiecia_probki:
            print("\nWyniki pomiaru próbki właściwej:")
            for dlugosc, napiecie in napiecia_probki:
                print(f"Długość fali: {dlugosc} nm - {napiecie:.3f} V")
        else:
            print("\nBrak danych dla próbki właściwej.")


def oblicz_reflektancje():
    if not napiecia_referencyjne or not napiecia_probki:
        print("\nBłąd: Brak danych dla referencji lub próbki właściwej.")
        return None

    referencja_skorygowana = [(dl, ref - sredni_szum) for dl, ref in napiecia_referencyjne]
    probka_skorygowana = [(dl, prob - sredni_szum) for dl, prob in napiecia_probki]

    reflektancja = [
        (dl, 100 * prob / ref if ref != 0 else 0)
        for (dl, ref), (_, prob) in zip(referencja_skorygowana, probka_skorygowana)
    ]

    print("\nWyniki pomiarów reflektancji:")
    for dl, refl in reflektancja:
        print(f"Długość fali: {dl} nm, Reflektancja: {refl:.2f}%")

    return reflektancja


def wykres_reflektancji(reflektancja):
    if not reflektancja:
        print("\nBrak danych do wyświetlenia wykresu reflektancji.")
        return

    dlugosci, wartosci_reflektancji = zip(*reflektancja)

    interpolowane_dlugosci = np.linspace(min(dlugosci), max(dlugosci), 1000)
    funkcja_interpolacji = interp1d(dlugosci, wartosci_reflektancji, kind='cubic')
    interpolowane_reflektancje = funkcja_interpolacji(interpolowane_dlugosci)

    plt.figure(figsize=(12, 6))
    plt.plot(interpolowane_dlugosci, interpolowane_reflektancje, linestyle='-', color='g', label='Interpolowana krzywa')
    plt.scatter(dlugosci, wartosci_reflektancji, color='r', label='Dane oryginalne')
    plt.xlabel("Długość fali (nm)")
    plt.ylabel("Reflektancja (%)")
    plt.title("Reflektancja w funkcji długości fali")
    plt.xticks(np.arange(min(dlugosci), max(dlugosci) + 1, 10), rotation=45)
    plt.legend()
    plt.grid(which='both', linestyle='--', linewidth=0.5)
    plt.minorticks_on()
    plt.show()


async def main():
    global klient

    while True:
        async with BleakClient(adres_urzadzenia) as klient:
            print("Połączono z urządzeniem Bluetooth.")

            await klient.start_notify(uuid_charakterystyki, obsluga_powiadomienia)

            if input("Czy chcesz wykonać pomiar szumu? (tak/nie): ").strip().lower() == "tak":
                await wykonaj_pomiar_szumu(klient)

            if input("Czy chcesz wykonać pomiar referencji? (tak/nie): ").strip().lower() == "tak":
                await wykonaj_pomiar(klient, "R")

            if input("Czy chcesz wykonać pomiar próbki właściwej? (tak/nie): ").strip().lower() == "tak":
                await wykonaj_pomiar(klient, "P")

            reflektancja = oblicz_reflektancje()
            if reflektancja:
                wykres_reflektancji(reflektancja)

            if input("Czy chcesz powtórzyć pomiary? (tak/nie): ").strip().lower() != "tak":
                print("Zakończono działanie programu.")
                break


asyncio.run(main())
