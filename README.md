# Działdowo Waste Pickup AI

Integracja Home Assistanta do rocznych harmonogramów odbioru odpadów w **Gminie Działdowo**.
Zdjęcie tabeli jest analizowane przez OpenAI tylko po ręcznym kliknięciu skanu, a odczytane dane
można poprawić przed zapisaniem ich do kalendarza HA.

To nie jest uniwersalna integracja dla dowolnej gminy. Jest przygotowana pod tabelaryczne harmonogramy
używane lokalnie w Gminie Działdowo.

## Najważniejsze

- Skan zdjęcia JPG, PNG albo WebP z panelu **Odpady Działdowo**.
- Edytowalna tabela weryfikacji przed zapisaniem harmonogramu.
- Przycisk **Nadpisz kalendarz** zapisuje tabelę jako nowy `calendar.waste_pickups` i usuwa poprzednie terminy.
- Powiadomienia dzień wcześniej rano i wieczorem, z pominięciem kategorii `Popiół`.
- Sensory najbliższego odbioru oraz sensory per kategoria do użycia na dashboardzie HA.
- Przypomnienie 1 stycznia o zeskanowaniu nowego harmonogramu.

## Instalacja przez HACS

[![Dodaj repozytorium w HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=migotom&repository=waste-pickup-ai&category=integration)

1. HACS -> menu -> **Custom repositories**.
2. Dodaj repozytorium `https://github.com/migotom/waste-pickup-ai`.
3. Wybierz typ **Integration**.
4. Zainstaluj **Działdowo Waste Pickup AI**.
5. Zrestartuj Home Assistanta.
6. Dodaj integrację w **Settings -> Devices & services** i podaj klucz OpenAI API.

## Użycie

1. Otwórz panel **Odpady Działdowo**.
2. Wgraj zdjęcie rocznego harmonogramu i kliknij **Skanuj**.
3. Sprawdź tabelę **Weryfikacja** i popraw dni w edytowalnych polach.
4. Kliknij **Nadpisz kalendarz**, aby zastąpić obecny `calendar.waste_pickups` poprawionymi terminami.
5. W panelu możesz też zmienić odbiorców powiadomień i godziny przypomnień.

## Encje

- `calendar.waste_pickups` - aktywne terminy odbioru.
- `sensor.waste_next_pickup` - najbliższy odbiór.
- `sensor.waste_category_pickups` - zbiorcze dane per kategoria.
- Sensory per kategoria, np. `Odpady: Papier`, z liczbą dni do najbliższego odbioru.
  Można dodać je na ekran główny HA jako kafelki informujące, za ile dni będzie odbiór danej frakcji.
- `sensor.waste_schedule_status` - status harmonogramu.

## Wymagania i prywatność

- Home Assistant `2025.5.0` lub nowszy.
- Klucz OpenAI API zapisany w konfiguracji HA.
- Obraz jest wysyłany do OpenAI tylko podczas ręcznego skanu; integracja nie wykonuje OCR w tle.
- Licencja: MIT.

## Development

Dokumentacja techniczna: [docs/development.md](docs/development.md) i [docs/publishing.md](docs/publishing.md).
