# REQUIREMENTS – SecTicket Pipeline

## 1. Cel aplikacji

SecTicket pozwala zarejestrować się, zalogować, dodawać zgłoszenia usterek, komentować je i śledzić ich status. Dane są w bazie SQLite, a zarządzanie zgłoszeniami jest dostępne tylko po zalogowaniu.

Drugi cel to pipeline CI/CD, który automatycznie skanuje kod i blokuje merge do `main`, gdy wykryje poważny problem bezpieczeństwa.

## 2. Użytkownicy

| Rola | Możliwości |
|---|---|
| Użytkownik | rejestruje się i loguje; dodaje, edytuje, usuwa i komentuje **własne** zgłoszenia |
| Technik | widzi wszystkie zgłoszenia, zmienia ich status i komentuje |

## 3. Wymagania funkcjonalne

| ID | Wymaganie |
|---|---|
| FR-01 | Rejestracja użytkownika (login, e-mail, hasło). |
| FR-02 | Logowanie i wylogowanie. |
| FR-03 | Dodawanie zgłoszenia (tytuł, opis, priorytet). |
| FR-04 | Lista własnych zgłoszeń z wyszukiwaniem po tytule. |
| FR-05 | Podgląd, edycja i usuwanie własnego zgłoszenia. |
| FR-06 | Komentowanie zgłoszeń. |
| FR-07 | Technik widzi wszystkie zgłoszenia i zmienia ich status. |

Po zalogowaniu dostępne są FR-03 do FR-07. Dane są przechowywane w SQLite.

## 4. Wymagania bezpieczeństwa

| ID | Wymaganie |
|---|---|
| SR-01 | Hasła są hashowane (bcrypt lub argon2), nigdy jawnie. |
| SR-02 | Zapytania do bazy są parametryzowane (brak SQL składanego z danych użytkownika). |
| SR-03 | Kontrola dostępu po stronie serwera: zgłoszenie widzi tylko jego właściciel lub technik (inaczej 403/404). |
| SR-04 | Dane wejściowe są walidowane, a wyjście escapowane (ochrona przed XSS). |
| SR-05 | Limit nieudanych prób logowania i minimalna długość hasła (min. 12 znaków). |
| SR-06 | Sekrety są w zmiennych środowiskowych (nie w repozytorium), tryb debug jest wyłączony. |
| SR-07 | Cookie sesji ma flagi HttpOnly, Secure i SameSite; docelowo ruch idzie przez HTTPS (lokalnie dopuszczalne HTTP). |
| SR-08 | Pipeline CI/CD skanuje sekrety, kod, zależności, obraz i działającą aplikację; poważne wyniki blokują merge do `main`. |

## 5. Wrażliwe elementy

Hasła użytkowników, sesje (cookie), treść zgłoszeń i komentarzy, plik bazy SQLite, sekrety (`SECRET_KEY`, tokeny CI/CD).

## 6. Model zagrożeń

Wszystkie poniższe zagrożenia są celowo wprowadzone w gałęzi `vulnerable`.

| ID | Zagrożenie | Czego dotyczy | Możliwe konsekwencje | Planowana kontrola / działanie |
|---|---|---|---|---|
| T-01 | Broken Access Control (IDOR): zmiana ID w adresie | zgłoszenia innych użytkowników | odczyt lub usunięcie cudzych danych | SR-03; testy pytest |
| T-02 | SQL Injection | wyszukiwarka, logowanie | wyciek lub modyfikacja bazy, obejście logowania | SR-02; Semgrep, testy pytest |
| T-03 | Stored XSS | tytuły i komentarze zgłoszeń | kradzież sesji, podszycie się pod użytkownika | SR-04, SR-07; testy pytest, ZAP (nagłówki, cookies) |
| T-04 | Wyciek sekretu do repozytorium | `SECRET_KEY`, tokeny | podrobienie sesji, przejęcie pipeline'u | SR-06; Gitleaks |
| T-05 | Podatna zależność | `requirements.txt`, obraz Dockera | skutki zależne od CVE (np. zdalne wykonanie kodu) | SR-08; pip-audit, Trivy |
