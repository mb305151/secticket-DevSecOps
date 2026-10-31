from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import select

from .extensions import db
from .models import Ticket


tickets_bp = Blueprint(
    "tickets", __name__, url_prefix="/tickets"
)

PRIORITIES = {"low", "medium", "high"}


def get_ticket(ticket_id, owner_only=False):
    statement = select(Ticket).where(Ticket.id == ticket_id)

    if owner_only or current_user.role != "technician":
        statement = statement.where(
            Ticket.user_id == current_user.id
        )

    return db.first_or_404(statement)


def form_values(ticket=None):
    if request.method == "POST":
        return {
            "title": request.form.get("title", "").strip(),
            "description": request.form.get(
                "description", ""
            ).strip(),
            "priority": request.form.get(
                "priority", ""
            ),
        }

    return {
        "title": ticket.title if ticket else "",
        "description": ticket.description if ticket else "",
        "priority": ticket.priority if ticket else "medium",
    }


def validate_ticket(values):
    errors = []

    if not 3 <= len(values["title"]) <= 200:
        errors.append(
            "Tytul musi miec od 3 do 200 znakow."
        )

    if not 10 <= len(values["description"]) <= 5000:
        errors.append(
            "Opis musi miec od 10 do 5000 znakow."
        )

    if values["priority"] not in PRIORITIES:
        errors.append("Niepoprawny priorytet.")

    return errors


@tickets_bp.get("/")
@login_required
def list_tickets():
    query = request.args.get("q", "").strip()[:100]
    page = max(1, request.args.get("page", 1, type=int))

    statement = select(Ticket)

    if current_user.role != "technician":
        statement = statement.where(
            Ticket.user_id == current_user.id
        )

    if query:
        statement = statement.where(
            Ticket.title.icontains(query, autoescape=True)
        )

    statement = statement.order_by(
        Ticket.created_at.desc(),
        Ticket.id.desc(),
    )

    tickets = db.paginate(
        statement,
        page=page,
        per_page=10,
        error_out=False,
    )

    return render_template(
        "tickets/list.html",
        tickets=tickets,
        query=query,
    )


@tickets_bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    values = form_values()

    if request.method == "POST":
        errors = validate_ticket(values)

        if not errors:
            ticket = Ticket(
                user_id=current_user.id,
                title=values["title"],
                description=values["description"],
                priority=values["priority"],
                status="open",
            )

            db.session.add(ticket)
            db.session.commit()

            flash("Zgloszenie zostalo dodane.", "success")

            return redirect(
                url_for("tickets.detail", ticket_id=ticket.id),
                code=303,
            )

        for error in errors:
            flash(error, "error")

    return render_template(
        "tickets/form.html",
        heading="Nowe zgloszenie",
        action=url_for("tickets.create"),
        values=values,
    ), 422 if request.method == "POST" else 200


@tickets_bp.get("/<int:ticket_id>")
@login_required
def detail(ticket_id):
    ticket = get_ticket(ticket_id)

    return render_template(
        "tickets/detail.html",
        ticket=ticket,
    )


@tickets_bp.route(
    "/<int:ticket_id>/edit",
    methods=["GET", "POST"],
)
@login_required
def edit(ticket_id):
    ticket = get_ticket(ticket_id, owner_only=True)
    values = form_values(ticket)

    if request.method == "POST":
        errors = validate_ticket(values)

        if not errors:
            ticket.title = values["title"]
            ticket.description = values["description"]
            ticket.priority = values["priority"]

            db.session.commit()

            flash("Zgloszenie zaktualizowane.", "success")

            return redirect(
                url_for("tickets.detail", ticket_id=ticket.id),
                code=303,
            )

        for error in errors:
            flash(error, "error")

    return render_template(
        "tickets/form.html",
        heading="Edytuj zgloszenie",
        action=url_for("tickets.edit", ticket_id=ticket.id),
        values=values,
    ), 422 if request.method == "POST" else 200


@tickets_bp.post("/<int:ticket_id>/delete")
@login_required
def delete(ticket_id):
    ticket = get_ticket(ticket_id, owner_only=True)

    db.session.delete(ticket)
    db.session.commit()

    flash("Zgloszenie usuniete.", "success")

    return redirect(
        url_for("tickets.list_tickets"),
        code=303,
    )
