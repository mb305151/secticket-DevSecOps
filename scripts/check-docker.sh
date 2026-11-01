#!/usr/bin/env bash
# Wspolna kontrola wymagan dla start.sh i test.sh.
secticket_check_docker() {
    local require_compose="${1:-no}"

    if ! command -v docker >/dev/null 2>&1; then
        echo '[SecTicket] BLAD: Docker nie jest zainstalowany (brak polecenia docker).' >&2
        echo '[SecTicket] Ubuntu: sudo apt update && sudo apt install docker.io docker-compose-v2' >&2
        echo '[SecTicket] Instrukcja: https://docs.docker.com/engine/install/ubuntu/' >&2
        return 1
    fi

    if ! docker info --format '{{.ServerVersion}}' >/dev/null 2>&1; then
        echo '[SecTicket] BLAD: Docker Engine nie odpowiada lub brak uprawnien.' >&2
        echo '[SecTicket] Sprawdz: sudo systemctl status docker' >&2
        echo '[SecTicket] Jesli usluga jest zatrzymana: sudo systemctl start docker' >&2
        echo '[SecTicket] Jesli sudo docker info dziala, ale docker info nie: sprawdz uprawnienia uzytkownika.' >&2
        echo '[SecTicket] Instrukcja: https://docs.docker.com/engine/install/linux-postinstall/' >&2
        return 1
    fi

    if [[ "$require_compose" == yes ]] && ! docker compose version >/dev/null 2>&1; then
        echo '[SecTicket] BLAD: Brakuje Docker Compose v2 (polecenie docker compose).' >&2
        echo '[SecTicket] Ubuntu: sudo apt install docker-compose-v2' >&2
        return 1
    fi
}
