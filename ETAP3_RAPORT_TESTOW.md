# SecTicket — raport testów, etap 3

- Projekt: SecTicket (DevSecOps)
- Zespół: Michał Dyrka, Mateusz Bennek, Oskar Sobolewski
- Gałąź: `feat/etap2-bootstrap`
- Data: 14.11.2026

## Środowisko i wykonanie

- Ubuntu Desktop na VMware; Docker i Python 3.13.
- Framework: pytest; aplikacja: Flask i SQLite.
- Polecenie: `./test.sh` (osobny obraz `secticket:test`).
- Wynik wykonania 14.11.2026: **49 passed w 2,68 s**, 0 błędów.

## Testy jednostkowe (13)

Funkcje z `app/security.py`, bez żądań HTTP i dostępu do bazy.
Plik: `tests/test_security_unit.py`.

| ID | Przypadek | Oczekiwany rezultat | Wynik |
| --- | --- | --- | --- |
| J01 | Hasło o długości 12 | Akceptacja dolnej granicy | PASS |
| J02 | Hasło o długości 128 | Akceptacja górnej granicy | PASS |
| J03 | Hasło o długości 11 | Odrzucenie | PASS |
| J04 | Hasło o długości 129 | Odrzucenie | PASS |
| J05 | Brak małej litery | Walidacja odrzuca | PASS |
| J06 | Brak wielkiej litery | Walidacja odrzuca | PASS |
| J07 | Brak cyfry | Walidacja odrzuca | PASS |
| J08 | Brak znaku specjalnego | Walidacja odrzuca | PASS |
| J09 | Znaki Unicode | Prawidłowa klasyfikacja kategorii | PASS |
| J10 | Hashowanie złego hasła | Wyjątek `ValueError` | PASS |
| J11 | Poprawne hasło | Hash Argon2id i pozytywna weryfikacja | PASS |
| J12 | Błędne hasło | Weryfikacja zwraca `False` | PASS |
| J13 | Niepoprawny hash | Weryfikacja zwraca `False` | PASS |

## Testy integracyjne (5 wybranych)

| ID | Test w repozytorium | Oczekiwany rezultat | Wynik |
| --- | --- | --- | --- |
| I01 | `test_registration_login_logout` | Poprawny cykl rejestracji i sesji | PASS |
| I02 | `test_owner_can_create_edit_delete` | Właściciel zarządza zgłoszeniem | PASS |
| I03 | `test_technician_can_change_status_and_comment` | Technik zmienia status i komentuje | PASS |
| I04 | `test_owner_edits_contact_but_must_confirm_email` | Walidacja danych i potwierdzenia pola e-mail | PASS |
| I05 | `test_admin_resets_others_password_once_with_forced_rotation` | Reset wymusza zmianę hasła | PASS |

## Scenariusze bezpieczeństwa (3)

| ID | Test w repozytorium | Oczekiwany rezultat | Wynik |
| --- | --- | --- | --- |
| S01 | `test_idor_blocks_other_user` | Brak dostępu do cudzego zgłoszenia | PASS |
| S02 | `test_csrf_protection` | Odrzucenie żądania bez tokenu CSRF | PASS |
| S03 | `test_ticket_content_is_escaped` | Bezpieczne escapowanie HTML | PASS |

## Test dostępności aplikacji (1)

| ID | Test | Oczekiwany rezultat | Wynik |
| --- | --- | --- | --- |
| H01 | `test_health_is_public` | GET /health: HTTP 200 i JSON `{"status":"ok"}` | PASS |

## Powtarzalność i ograniczenia

- Zestaw uruchamia się automatycznie jedną komendą `./test.sh`.
- Testy jednostkowe nie wymagają bazy, sieci ani klienta Flask.
- Testy integracyjne sprawdzają współdziałanie aplikacji i bazy testowej.
- Wynik 49/49 obejmuje także pozostałe testy regresyjne.
- Testy nie zastępują testów obciążeniowych ani pełnego audytu bezpieczeństwa.

## Materiały do PZE

- Aktualny `README.md` i niniejszy raport.
- Zrzut terminala z wynikiem `49 passed`.
- Link do repozytorium; pozostałe załączniki według ogłoszenia PZE.
