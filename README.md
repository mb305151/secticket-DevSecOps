# SecTicket Pipeline

Projekt zespołowy na zajęcia projektowe z przedmiotu **Projektowanie, Bezpieczeństwo i Operacje (DevSecOps)**, Politechnika Śląska, Wydział Automatyki, Elektroniki i Informatyki.

## Zespół

- **Mateusz Bennek** – DevOps (repozytorium, tablica zadań, GitHub Actions, Docker, Trivy, bramka)
- **Oskar Sobolewski** – aplikacja i testy (Flask, baza danych, funkcje, pytest)
- **Michał Dyrka** – bezpieczeństwo i dokumentacja (podatności, ZAP, diagram, README i REQUIREMENTS)

## Język i technologie

- **Język i framework:** Python 3 + Flask
- **Baza danych:** SQLite
- **Kontenery:** Docker, Docker Compose
- **Repozytorium i CI/CD:** GitHub + GitHub Actions
- **Narzędzia bezpieczeństwa:** Gitleaks (sekrety), Semgrep (analiza kodu), pip-audit (zależności), Trivy (obraz Dockera), OWASP ZAP (skan działającej aplikacji)
- **Testy:** pytest
- **Zarządzanie zadaniami:** GitHub Projects

## Krótki opis

**SecTicket** to prosta aplikacja webowa do zgłaszania usterek (np. w akademiku lub biurze).

- **Jaki problem rozwiązuje?** Zgłoszenia usterek są rozproszone (wiadomości, maile, kartki). Aplikacja zbiera je w jednym miejscu.
- **Kto z niej korzysta?** Użytkownicy zgłaszający usterki oraz technicy, którzy je obsługują.
- **Dlaczego jest potrzebna?** Daje porządek w zgłoszeniach, a każdy użytkownik widzi tylko własne dane.
- **Jaką podstawową czynność umożliwia?** Po zalogowaniu użytkownik dodaje zgłoszenie, komentuje je i śledzi jego status.

Głównym celem projektu jest **pipeline DevSecOps**: automatyczne skany bezpieczeństwa w GitHub Actions, które blokują wdrożenie niebezpiecznego kodu.

## Gałęzie

| Gałąź | Opis |
|---|---|
| `main` | wersja bezpieczna; pipeline musi być zielony |
| `vulnerable` | wersja celowo podatna (IDOR, SQL Injection, XSS, sekret w repo, przestarzała zależność); służy do pokazania, że pipeline wykrywa błędy; nigdy nie jest scalana do `main` ani wystawiana publicznie |

## Dokumenty etapu 1

- `README.md` – ten plik
- `REQUIREMENTS.md` – cel, użytkownicy, wymagania, model zagrożeń
- diagram działania aplikacji
- `BACKLOG.md` – lista zadań przypisanych do osób
