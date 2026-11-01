# SecTicket Pipeline

**SecTicket** to aplikacja webowa do obsługi zgłoszeń usterek, przygotowana w ramach zajęć „Projektowanie, Bezpieczeństwo i Operacje (DevSecOps)”. Użytkownicy mogą zgłaszać problemy i śledzić ich realizację, a technicy obsługują zgłoszenia. Aplikacja ma również panel administracyjny do zarządzania profilami użytkowników.

Projekt koncentruje się na uruchamianiu w kontenerze Docker, walidacji i kontroli dostępu, testach oraz automatycznym sprawdzaniu bezpieczeństwa w GitHub Actions.

## Zespół

| Osoba | Obszar odpowiedzialności |
| --- | --- |
| Mateusz Bennek | DevOps: Docker, uruchamianie, GitHub Actions |
| Oskar Sobolewski | Aplikacja Flask, baza danych i testy |
| Michał Dyrka | Bezpieczeństwo i dokumentacja |

Podział obszarów odpowiada założeniom projektu. Faktyczne autorstwo zmian można sprawdzić w historii commitów repozytorium.

## Technologie

- **Backend:** Python 3.13, Flask, Gunicorn, SQLAlchemy i Alembic.
- **Baza danych:** SQLite w trwałym wolumenie Dockera.
- **Frontend:** Jinja2, Tailwind CSS v4 i JavaScript.
- **Konteneryzacja:** Docker oraz Docker Compose.
- **Testy:** pytest.
- **CI / bezpieczeństwo:** GitHub Actions, Bandit, pip-audit i Trivy.

## Wymagania środowiskowe

- Linux (testowano na Ubuntu); na innych systemach wymagane jest działające środowisko Docker.
- Zainstalowane i uruchomione **Docker Engine** oraz **Docker Compose v2** (polecenie `docker compose`).
- **Git** do pobrania repozytorium.
- Połączenie z internetem przy pierwszym uruchomieniu (pobranie obrazów i zależności).
- Wolny port **5000** na komputerze, na którym działa aplikacja.

Nie trzeba lokalnie instalować Pythona, Flaska, SQLite ani Node.js — zależności aplikacji i budowanie stylów realizowane są w Dockerze.

## Instalacja i uruchomienie — jedna komenda

Pobierz aktualną gałąź projektu:

```bash
git clone --branch feat/etap2-bootstrap https://github.com/mb305151/secticket-DevSecOps.git
cd secticket-DevSecOps
```

Uruchom aplikację:

```bash
./start.sh
```

Skrypt przygotowuje lokalny plik konfiguracyjny `.env` (jeżeli go nie ma), buduje obraz, uruchamia kontener i wykonuje migracje bazy danych. Tabele są tworzone **automatycznie**; nie trzeba ręcznie zakładać bazy ani uruchamiać SQL.

Przy kolejnych uruchomieniach użyj ponownie `./start.sh`. Dane zgłoszeń i kont pozostają w wolumenie Dockera.

**Uwaga:** jeśli użytkownik systemu nie ma uprawnień do Dockera, należy skonfigurować dostęp zgodnie z instrukcją instalacji Dockera. Nie zapisuj hasła ani sekretów w repozytorium.

## Adresy aplikacji i najważniejsze widoki

| Adres | Opis | Dostęp |
| --- | --- | --- |
| `http://localhost:5000/` | Strona powitalna | Publiczny |
| `http://localhost:5000/dashboard` | Pulpit i statystyki zgłoszeń | Po zalogowaniu |
| `http://localhost:5000/tickets` | Lista i wyszukiwanie zgłoszeń | Po zalogowaniu |
| `http://localhost:5000/profile` | Edycja własnego profilu i danych kontaktowych | Po zalogowaniu |
| `http://localhost:5000/profile/password` | Zmiana własnego hasła | Po zalogowaniu |
| `http://localhost:5000/users` | Administracja użytkownikami | Tylko administrator |
| `http://localhost:5000/health` | Kontrola stanu aplikacji | Publiczny |

Po pierwszym uruchomieniu wejdź na stronę główną i utwórz konto przez formularz rejestracji.

## Funkcjonalności i role

- **Użytkownik:** rejestracja, logowanie, zarządzanie własnymi zgłoszeniami (tworzenie, przeglądanie, edycja, usuwanie), komentarze, edycja profilu i zmiana hasła.
- **Technik:** przeglądanie zgłoszeń wszystkich użytkowników, dodawanie komentarzy i aktualizowanie statusów, bez prawa do edycji lub usuwania cudzych zgłoszeń.
- **Administrator:** zarządzanie profilami innych użytkowników i reset ich haseł na tymczasowe; uprawnienie nadawane wyłącznie w zaufanym terminalu.

Przykładowe operacje administracyjne wykonywane na już działającym kontenerze:

```bash
# Nadanie roli technika istniejącemu użytkownikowi:
docker compose exec app flask --app 'app:create_app()' grant-technician NAZWA_UZYTKOWNIKA

# Nadanie uprawnień administratora istniejącemu użytkownikowi:
docker compose exec app flask --app 'app:create_app()' grant-admin NAZWA_UZYTKOWNIKA
```

Po zmianie uprawnień użytkownik powinien zalogować się ponownie. **Nie udostępniaj komend administracyjnych niezaufanym osobom.**

## Endpoint `/health` i przykładowe żądania HTTP

Aplikacja udostępnia publiczny endpoint `GET /health`, niewymagający logowania.

**Żądanie:**

```bash
curl -i http://localhost:5000/health
```

**Oczekiwany kod odpowiedzi:** `HTTP 200 OK`.

**Oczekiwany JSON:**

```json
{"status":"ok"}
```

Inne przykłady żądań:

```bash
# Pobranie publicznej strony głównej:
curl -i http://localhost:5000/

# Pobranie samego JSON ze stanem aplikacji:
curl -s http://localhost:5000/health

# Przykład żądania do strony wymagającej logowania:
curl -i http://localhost:5000/dashboard
```

Dla niezalogowanego klienta dostęp do chronionych widoków jest ograniczony; aplikacja korzysta z logowania sesyjnego i ochrony CSRF dla formularzy.

## Baza danych

Baza SQLite powstaje automatycznie przy uruchamianiu aplikacji. Schemat aktualizują migracje **Alembic**. Dane kont, profili, zgłoszeń, komentarzy i zdarzeń bezpieczeństwa są przechowywane w trwałym wolumenie Dockera.

Nie wykonuj `docker compose down -v`, jeśli chcesz zachować istniejące dane — opcja `-v` usuwa wolumeny.

## Testy i kontrola uruchomienia

Uruchom wszystkie testy w odizolowanym kontenerze:

```bash
./test.sh
```

Sprawdź działanie aplikacji:

```bash
docker compose ps
curl -i http://localhost:5000/health
```

Zatrzymanie aplikacji bez usuwania bazy:

```bash
docker compose stop
```

Ponowne uruchomienie: `./start.sh`.

## Bezpieczeństwo i GitHub Actions

Zastosowane mechanizmy obejmują m.in. hashowanie haseł **Argon2id**, kontrolę uprawnień po stronie serwera, CSRF, walidację danych, escapowanie treści HTML, limity prób logowania, zdarzenia audytowe i uruchamianie aplikacji w kontenerze jako użytkownik bez uprawnień roota.

Workflow `.github/workflows/ci.yml` uruchamia testy i kontrolę migracji, skan kodu **Bandit**, audyt zależności **pip-audit** oraz skan obrazu Dockera **Trivy**.

**Polityka CVE:** Trivy generuje pełny raport wykryć. Osobny krok blokuje niezaakceptowane podatności HIGH/CRITICAL. Wybrane, wcześniej ocenione CVE mają czasowe wyjątki zapisane w `.trivyignore.yaml`, z uzasadnieniem i terminem wygaśnięcia **30 listopada 2026 r.** Nie oznacza to usunięcia tych podatności ani dopuszczenia aplikacji do produkcyjnego wdrożenia w internecie. Nowe CVE spoza wyjątków nadal blokują pipeline. Założenia wyjątków wymagają ponownego przeglądu po zmianie obrazu lub funkcji aplikacji.

**Ograniczenia wersji demonstracyjnej:** aplikacja działa lokalnie przez HTTP; zarządzanie adresami e-mail nie obejmuje potwierdzania ich własności ani wysyłania poczty. Przed publikacją internetową konieczne byłyby dodatkowa konfiguracja HTTPS, przegląd bezpieczeństwa i polityka wdrożenia.

## Struktura repozytorium

```text
app/                  kod Flask, szablony Jinja i zasoby frontendu
migrations/           migracje Alembic
tests/                testy aplikacji i bezpieczeństwa
.github/workflows/    GitHub Actions CI
Dockerfile            obraz aplikacji i etap testowy
compose.yaml          uruchamianie usługi i wolumen bazy
requirements.txt      zależności uruchomieniowe Pythona
requirements-dev.txt  zależności testowe
package.json          zależności frontendu Tailwind CSS
start.sh              uruchomienie aplikacji
test.sh               uruchomienie testów
.trivyignore.yaml     czasowe wyjątki CVE
```

## Materiały do oddania — etap 2

Zgodnie z wymaganiami zajęć należy dołączyć na PZE aktualny `README.md`, zrzut podziału zadań, zrzut historii commitów wszystkich członków zespołu, zrzut działającej aplikacji oraz link do repozytorium. Prowadzący wymaga także co najmniej **dwóch commitów tygodniowo na osobę** (liczy się autor commita, a nie podpis w opisie).
