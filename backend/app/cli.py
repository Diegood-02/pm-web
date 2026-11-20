"""Comandos de administración.

Ejemplo: python -m app.cli create-admin --email tu@correo.com --name "Tu nombre"

La contraseña se pide por consola (no se escribe en argumentos ni en el historial).
"""

import argparse
import getpass
import sys

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Role, User
from app.security import hash_password
from app.seed import seed_demo_project


def create_admin(email: str, full_name: str, password: str) -> int:
    with SessionLocal() as session:
        if session.scalar(select(User).where(User.email == email.lower())) is not None:
            print("Ya existe un usuario con ese correo.", file=sys.stderr)
            return 1
        session.add(
            User(
                email=email.lower(),
                full_name=full_name,
                password_hash=hash_password(password),
                role=Role.ADMIN,
            )
        )
        session.commit()
    print(f"Administrador creado: {email.lower()}")
    return 0


def seed_demo(email: str) -> int:
    with SessionLocal() as session:
        owner = session.scalar(select(User).where(User.email == email.lower()))
        if owner is None:
            print("No existe un usuario con ese correo.", file=sys.stderr)
            return 1
        project = seed_demo_project(session, owner)
        print(f"Proyecto de ejemplo creado con id {project.id}: {project.name}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="app.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)
    admin = subparsers.add_parser("create-admin", help="Crea el primer usuario administrador")
    admin.add_argument("--email", required=True)
    admin.add_argument("--name", required=True, dest="full_name")
    demo = subparsers.add_parser("seed-demo", help="Crea el proyecto de ejemplo de 40 tareas")
    demo.add_argument(
        "--email", required=True, help="Correo del project manager que será dueño del proyecto"
    )
    args = parser.parse_args()

    if args.command == "seed-demo":
        return seed_demo(args.email)

    if args.command == "create-admin":
        password = getpass.getpass("Contraseña (mínimo 12 caracteres): ")
        if len(password) < 12:
            print("La contraseña debe tener al menos 12 caracteres.", file=sys.stderr)
            return 1
        return create_admin(args.email, args.full_name, password)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
