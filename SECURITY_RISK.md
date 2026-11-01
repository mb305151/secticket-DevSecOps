# SecTicket — analiza podatności obrazu Docker i rejestr ryzyka

**Projekt:** SecTicket Pipeline (DevSecOps, etap 2)  
**Data analizy:** 2026-11-01  
**Analizowany przebieg CI:** [GitHub Actions #41250698152](https://github.com/mb305151/secticket-DevSecOps/actions/runs/41250698152)  
**Gałąź:** `feat/etap2-bootstrap`  
**Obraz:** `secticket:scan`, budowany z `python:3.13-slim-trixie`  
**Narzędzie:** Trivy 0.74.0, skan podatności OS i bibliotek, filtr `HIGH,CRITICAL`  
**Status dokumentu:** **Analiza techniczna z czasowym wyjątkiem CI dla wersji demonstracyjnej, do 2026-11-30.**

> **Uwaga:** ten dokument opisuje wyniki z konkretnego przebiegu CI. Nie jest certyfikatem bezpieczeństwa ani dowodem, że pozostałe podatności są niewykorzystywalne. Statusy CVE, poprawki i warunki wdrożenia należy okresowo weryfikować.

## 1. Podsumowanie wyników i dowodów

| Kontrola / obserwacja | Wynik z dotychczasowych testów |
| --- | --- |
| Testy aplikacji | **26/26 PASS** (pytest) |
| Migracje SQLite / Alembic | **PASS**, migracja do `60b02fdc0a34 (head)` |
| Healthcheck aplikacji | **HTTP 200**, `{"status":"ok"}` |
| Bandit i pip-audit | **PASS** w CI |
| Trivy — najnowszy skan | **44 wykrycia HIGH, 0 CRITICAL** w pakietach systemowych Debiana |
| Unikalne CVE widoczne w wyciągu logów | **8** (wiele wykryć dotyczy różnych pakietów z tych samych projektów źródłowych) |
| Wcześniejsze wykrycia Python | Po usunięciu `pip` z obrazu uruchomieniowego **nie występują w otrzymanym filtrowanym fragmencie raportu**; pełny raport/SBOM należy zachować do potwierdzenia |
| Stan pipeline'u | Job Trivy **FAIL**, ponieważ polityka CI przewiduje `exit-code: '1'` dla HIGH/CRITICAL — skaner działa zgodnie z konfiguracją |

**Zidentyfikowane CVE:** `CVE-2026-76642`, `CVE-2026-78408`, `CVE-2026-78409`, `CVE-2026-78410`, `CVE-2026-54369`, `CVE-2025-69720`, `CVE-2026-16742`, `CVE-2026-9538`.

**Granice analizy:** dysponujemy logiem Trivy (częściowo filtrowanym poleceniem `grep`), wynikami pytest/CI i informacjami z publicznych baz podatności. **Nie przeprowadzono** testu eksploatacji, pełnej inspekcji wykorzystywanych funkcji systemowych, oceny dostępu do hosta ani niezależnego przeglądu wszystkich zależności. Wniosek o zmniejszonym prawdopodobieństwie wykorzystania w konkretnym kontekście to **hipoteza do sprawdzenia**, a nie potwierdzony brak zagrożenia.

## 2. Kontekst zagrożeń i istniejące zabezpieczenia

SecTicket to aplikacja Flask uruchamiana przez Gunicorn w kontenerze Docker, z bazą SQLite na nazwanym wolumenie. Dockerfile uruchamia proces aplikacji jako użytkownik bez uprawnień administratora (UID 10001). Dotychczas wdrożono hashowanie haseł Argon2id, CSRF, rate limiting, kontrolę dostępu do zgłoszeń (IDOR), testy automatyczne i dziennik zdarzeń bezpieczeństwa.

**Zabezpieczenia zmniejszają powierzchnię ataku, ale nie usuwają CVE z pakietów.** Opisy części wykrytych błędów dotyczą lokalnych operacji uprzywilejowanych (`mount`, `nsenter`, `systemd-homed`, funkcje ACL). Nie wykazano, aby zwykła obsługa żądań HTTP przez Flask z nich korzystała; należy jeszcze sprawdzić obecność i uprawnienia programów, konfigurację mountów, możliwości kontenera oraz konfigurację hosta Docker.

**Uwaga o ekspozycji:** w ostatnich logach Compose port `5000` był publikowany jako `0.0.0.0:5000`. Nie możemy zatem automatycznie uznać aplikacji za dostępną wyłącznie z `localhost`; faktyczny dostęp zależy od sieci VM, zapory i przekierowań. Do demonstracji zalecamy sieć lokalną o ograniczonym dostępie, bez publicznego wystawiania usługi.

## 3. Rejestr ryzyka — analiza poszczególnych CVE

W tabeli **HIGH** oznacza klasyfikację Trivy, a nie potwierdzone wysokie ryzyko wykorzystania przeciwko SecTicket. „Otwarta” oznacza, że **szczegółowa weryfikacja techniczna pozostaje niezakończona**. Czasowy wyjątek CI nie zamyka oceny.

| ID | Pakiet źródłowy / przykład | Mechanizm i warunek wykorzystania | Wstępna ocena w SecTicket | Decyzja / następny krok | Status |
| --- | --- | --- | --- | --- | --- |
| R-01 / CVE-2026-76642 | `util-linux` (`mount`, `libmount1` itd.) | Uruchomienie uprzywilejowanych działań po nieudanym pomocniczym programie montowania; wymaga odpowiedniego lokalnego scenariusza. | **Osiągalność niepotwierdzona**; aplikacja Flask nie wykonuje standardowo uprzywilejowanych mountów. | Sprawdzić SUID `mount`, konfigurację kontenera i dostępne poprawki Debiana; utrzymać ograniczenia uprawnień. | **Otwarta** |
| R-02 / CVE-2026-78408 | `util-linux` / `nsenter` | Pozostawienie możliwości operacji na cgroups po uprzywilejowanym `nsenter --join-cgroup`. | **Osiągalność niepotwierdzona**; wymaga scenariusza uprzywilejowanego `nsenter`. | Zweryfikować, czy funkcja/narzędzie jest obecne i dostępne; nie udzielać kontenerowi dodatkowych capabilities. | **Otwarta** |
| R-03 / CVE-2026-78409 | `util-linux` / `X-mount.subdir` | Specyficzna ścieżka montowania z rozwiązywaniem symlinków. | **Możliwe błędne dopasowanie wersji**: w raporcie jest `2.41.5-0+deb13u1`, a opis Red Hat wskazuje na wprowadzenie podatnej ścieżki w `2.42`; Debian Tracker nadal oznacza Trixie jako podatne. **Nie rozstrzygamy rozbieżności na podstawie samego CVE.** | Porównać kod źródłowy pakietu Debiana i warunki eksploatacji; dopiero po udokumentowaniu można rozważyć precyzyjny wyjątek/VEX. | **Otwarta — weryfikacja dopasowania** |
| R-04 / CVE-2026-78410 | `util-linux` / ograniczone bind mounts | Przekierowanie źródła mounta przez lokalnego użytkownika, w określonej konfiguracji `/etc/fstab` i opcji `X-mount.*`. | **Osiągalność niepotwierdzona**; zależy od uprzywilejowanego montowania. | Zweryfikować `/etc/fstab`, SUID, uprawnienia i aktualizacje; nie montować dowolnych ścieżek hosta. | **Otwarta** |
| R-05 / CVE-2026-54369 | `acl` / `libacl1` | Symlink traversal w operacjach ACL wykonywanych przez uprzywilejowany proces na kontrolowanej ścieżce. | **Osiągalność niepotwierdzona**; nie wykazano wywołań podatnych funkcji z żądań HTTP. | Sprawdzić wykorzystanie ACL w obrazie i hostowej konfiguracji; monitorować poprawkę w Trixie. | **Otwarta** |
| R-06 / CVE-2025-69720 | `ncurses` / `infocmp` | Przepełnienie bufora w narzędziu CLI `infocmp` przy przetwarzaniu specyficznych danych. | **Wstępnie ograniczona ścieżka wejścia**; SecTicket nie oferuje funkcji wywołującej `infocmp`, lecz wymaga to potwierdzenia. | Sprawdzić obecność i użycie `infocmp`; zaktualizować pakiety, gdy poprawka będzie dostępna w Trixie. | **Otwarta** |
| R-07 / CVE-2026-16742 | `systemd` / `libsystemd0`, `libudev1` | Lokalna eskalacja uprawnień w `systemd-homed` dla użytkownika zarządzanego przez ten komponent. | **Wstępnie ograniczona osiągalność**: kontener aplikacji nie jest przewidziany do uruchamiania `systemd-homed`; sama obecność biblioteki nie potwierdza ścieżki ataku. | Potwierdzić brak usługi `systemd-homed`, uprawnień lokalnych i odpowiedniej konfiguracji. | **Otwarta** |
| R-08 / CVE-2026-9538 | `perl-base` / `Archive::Tar` | Zużycie pamięci przez złośliwie przygotowany nagłówek archiwum TAR od niezaufanego źródła. | **Wstępnie ograniczona osiągalność**; aplikacja nie oferuje importowania archiwów TAR. | Zweryfikować, czy w obrazie lub uruchamianych skryptach jest przetwarzanie niezaufanych TAR; monitorować poprawkę. | **Otwarta** |

**Informacja o wersjach:** w wyniku Trivy dla `util-linux` widać `2.41.5-0+deb13u1`; dla `acl` — `2.3.2-2+b1`; dla `ncurses` — `6.5+20250216-2`; dla `systemd` — `257.13-1~deb13u1`; dla `perl-base` — `5.40.1-6+deb13u1`. Wersje i klasyfikacje mogą się zmienić po odświeżeniu obrazu i baz CVE.

## 4. Plan postępowania i kryteria akceptacji

### Decyzja na dziś

1. **Kontynuujemy lokalny rozwój i testy projektu dydaktycznego**, ponieważ dotychczasowe testy funkcjonalne działają; to nie jest zezwolenie na produkcyjne wystawienie aplikacji.
2. **Nie ogłaszamy 44 wykryć jako „naprawione” ani „zaakceptowane”.** Każde CVE pozostaje otwarte do weryfikacji warunków wykorzystania i decyzji właściciela ryzyka.
3. **Zostawiamy skan Trivy i `exit-code: '1'` dla HIGH/CRITICAL.** Czerwony job jest prawidłowym sygnałem niezamkniętego ryzyka. Nie używamy globalnego `ignore-unfixed`, `continue-on-error` ani ignorowania całej grupy CVE.
4. **Nie przełączamy teraz obrazu na Alpine ani nie instalujemy pakietów z `sid`/`unstable`.** Taką zmianę można rozważyć po porównaniu skanów, kompatybilności i skutków eksploatacyjnych.

### Dalsze czynności (backlog bezpieczeństwa)

| Priorytet | Zadanie | Kryterium zamknięcia |
| --- | --- | --- |
| P1 | Potwierdzić konfigurację kontenera: UID, capabilities, SUID, `/etc/fstab`, działające usługi i uprawnienia do hosta | Zapis wyników audytu + testy regresji |
| P1 | Zweryfikować rozbieżność w CVE-2026-78409 | Źródło techniczne dla dokładnej wersji Debiana; decyzja `affected` / `not_affected` z uzasadnieniem |
| P1 | Potwierdzić, czy aplikacja jest dostępna wyłącznie w zaufanej sieci | Sprawdzenie publikacji portu 5000, reguł firewalla i sieci VM |
| P2 | Odświeżyć obraz bazowy i ponownie uruchomić Trivy | Nowy raport z datą i porównaniem unikalnych CVE oraz wykryć |
| P2 | Zweryfikować obecność poprawek w Debian Trixie; ocenić usunięcie zbędnych pakietów lub zmianę obrazu | Udokumentowany koszt, korzyści i wynik testów 26/26 + migracji |
| P2 | Utworzyć rejestr wyjątków, jeśli jakieś CVE okażą się nieosiągalne lub zostaną świadomie zaakceptowane | **Właściciel, dowód, uzasadnienie, zakres, data wygaśnięcia i zatwierdzenie** każdego wyjątku |
| P2 | Zachować pełny raport Trivy w artefaktach CI (bez sekretów) | Raport przypięty do konkretnego przebiegu/commita |

**Właściciel oceny:** zespół SecTicket (przydział konkretnej osoby do zatwierdzenia — do ustalenia).  
**Najbliższy przegląd:** 2026-11-08, a także po każdej aktualizacji obrazu lub pojawieniu się istotnych informacji o wykorzystaniu podatności.  
**Warunek wcześniejszej eskalacji:** informacja o aktywnym wykorzystywaniu (np. CISA KEV), potwierdzona osiągalność z wejścia użytkownika lub dostępna skuteczna poprawka dla istotnego ryzyka.

### Polityka wyjątków w CI (na przyszłość)

Dopuszczamy **tylko precyzyjne, udokumentowane wyjątki**, po technicznym potwierdzeniu `not affected` albo świadomym, terminowym zatwierdzeniu ryzyka. Wpis musi obejmować: CVE, konkretny obraz/wersję, przyczynę, źródła dowodowe, osobę zatwierdzającą i termin ponownego przeglądu. Wyjątek ma wygasać i nie może bezterminowo ukrywać nowych podatności.

**Na obecnym etapie nie dodajemy żadnego wyjątku do konfiguracji Trivy.**

## 5. Źródła i ślad audytowy

**Dowody z projektu**

- [Przebieg GitHub Actions #41250698152](https://github.com/mb305151/secticket-DevSecOps/actions/runs/41250698152) — raport po zmianie obrazu, **44 HIGH / 0 CRITICAL**.
- [Przebieg GitHub Actions #41250188306](https://github.com/mb305151/secticket-DevSecOps/actions/runs/41250188306) — wcześniejszy raport, z dodatkowymi wykryciami w bibliotekach Pythona.
- Lokalnie odtworzone testy: `./test.sh` (**26 passed**), `flask db upgrade`, `flask db current` (**`60b02fdc0a34 (head)`**), `GET /health` (**HTTP 200**).

**Autorytatywne opisy CVE i polityka zarządzania ryzykiem (sprawdzone 2026-11-01)**

- Debian Security Tracker: [CVE-2026-76642](https://security-tracker.debian.org/tracker/CVE-2026-76642), [CVE-2026-78408](https://security-tracker.debian.org/tracker/CVE-2026-78408), [CVE-2026-78409](https://security-tracker.debian.org/tracker/CVE-2026-78409), [CVE-2026-78410](https://security-tracker.debian.org/tracker/CVE-2026-78410).
- Debian Security Tracker: [CVE-2026-54369](https://security-tracker.debian.org/tracker/CVE-2026-54369), [CVE-2025-69720](https://security-tracker.debian.org/tracker/CVE-2025-69720), [CVE-2026-16742](https://security-tracker.debian.org/tracker/CVE-2026-16742), [CVE-2026-9538](https://security-tracker.debian.org/tracker/CVE-2026-9538).
- Red Hat, [CVE-2026-78409 — zakres podatnych wersji](https://access.redhat.com/security/cve/cve-2026-78409) — źródło opisujące rozbieżność względem klasyfikacji Debiana dla 2.41.5.
- NIST, [SP 800-40 Rev. 4 — Guide to Enterprise Patch Management Planning](https://csrc.nist.gov/pubs/sp/800/40/r4/final) — odpowiedzi na ryzyko nie ograniczają się do łatania.
- CISA, [Known Exploited Vulnerabilities Catalog](https://www.cisa.gov/known-exploited-vulnerabilities-catalog) — źródło do ustalania priorytetów, nie dowód automatycznej eksploatowalności danej instalacji.

---

**Podsumowanie decyzji:** SecTicket ma działające zabezpieczenia i testy, ale najnowszy skan kontenera wykrył **44 wystąpienia HIGH z 8 unikalnymi CVE**. Zespół świadomie **utrzymuje widoczność problemu i otwarte zadania oceny**, zamiast maskować wynik skanera. Formalna akceptacja ryzyka lub wyłączenie wykrycia wymaga kolejnych dowodów i zatwierdzenia.


## 6. Decyzja o czasowych wyjatkach CI (2026-11-01)

Ta sekcja aktualizuje wczesniejsza polityke z rozdzialu 4.

**Decyzja:** zespol SecTicket dopuszcza czasowy wyjatek CI
dla osmiu CVE wymienionych w rejestrze R-01 do R-08.

**Charakter:** warunkowa tolerancja znanego ryzyka w projekcie
dydaktycznym. Nie jest to usuniecie podatnosci ani potwierdzenie
braku mozliwosci ich wykorzystania.

**Wlasciciel decyzji:** zespol SecTicket. Wdrozenie tej zmiany
w Git wymaga zatwierdzenia przez osobe odpowiedzialna za repozytorium.

**Termin przegladu:** 2026-11-08.
**Wygasniecie wyjatkow:** 2026-11-30.

**Warunki:**
- Tylko lokalny development i demonstracje w zaufanej sieci.
- Brak zgody na publiczne wdrozenie aplikacji.
- Aplikacja uruchamiana jako uzytkownik bez uprawnien roota.
- Ograniczenie capabilities i no-new-privileges w Compose.
- Pelny raport Trivy pozostaje widoczny w GitHub Actions.
- Nowe HIGH i CRITICAL nadal blokuja pipeline.
- Wyjatki nie obejmuja automatycznie nowych identyfikatorow CVE.
- Wyniki wymagaja ponownej oceny po aktualizacji obrazu.

**Wymagane dalsze dzialania:** weryfikacja osiagnalnosci
podatnych funkcji, aktualizacji Debiana i warunkow wykorzystania.
W szczegolnosci CVE-2026-78409 wymaga wyjasnienia rozbieznosci
pomiedzy informacjami o podatnych wersjach.

**Implementacja:** `.trivyignore.yaml` oraz dwa skany w `ci.yml`:
pelny raport bez wyjatkow i blokujaca kontrola z wyjatkami.

**Status:** ryzyko warunkowo tolerowane do wskazanej daty;
ocena techniczna i zadania naprawcze pozostaja otwarte.
