# BACKLOG – SecTicket Pipeline

Lista zadań wpisana w GitHub Projects (tablica w repozytorium) i przypisana do osób.

**Podział ról:**
- **Mateusz Bennek** – DevOps (CI/CD, Docker)
- **Oskar Sobolewski** – aplikacja i testy
- **Michał Dyrka** – bezpieczeństwo i dokumentacja

| ID | Zadanie | Osoba |
|---|---|---|
| B-01 | Założyć **publiczne** repozytorium GitHub (branche `main` i `vulnerable`; publiczne, bo ochrona gałęzi w darmowym planie działa tylko tam) | Mateusz Bennek |
| B-02 | Napisać README.md i REQUIREMENTS.md | Michał Dyrka |
| B-03 | Przygotować diagram działania aplikacji | Michał Dyrka |
| B-04 | Założyć tablicę GitHub Projects i wpisać backlog | Mateusz Bennek |
| B-05 | Aplikacja Flask + SQLite: rejestracja i logowanie (wersja bezpieczna na `main`) | Oskar Sobolewski |
| B-06 | Zgłoszenia: dodawanie, lista, wyszukiwanie, edycja, usuwanie | Oskar Sobolewski |
| B-07 | Komentarze, zmiana statusu, rola Technik, logowanie zdarzeń bezpieczeństwa | Oskar Sobolewski |
| B-08 | Testy pytest, w tym testy bezpieczeństwa (IDOR, SQLi, XSS) | Oskar Sobolewski |
| B-09 | Gałąź `vulnerable`: wprowadzić 5 podatności z modelu zagrożeń | Michał Dyrka |
| B-10 | GitHub Actions: Gitleaks, Semgrep, pip-audit, pytest | Mateusz Bennek |
| B-11 | Dockerfile (użytkownik non-root), docker-compose, skan Trivy | Mateusz Bennek |
| B-12 | OWASP ZAP (baseline) na działającej aplikacji | Michał Dyrka |
| B-13 | Job „bramka" zbierający wyniki skanów + ochrona gałęzi `main` | Mateusz Bennek |
| B-14 | Raport „vulnerable vs main" (wyniki skanów przed i po) i prezentacja | Wszyscy |
