from collections.abc import Callable

from fastapi.testclient import TestClient

from app.models import Role
from tests.conftest import API, PASSWORD, Headers


def test_login_devuelve_tokens_y_me_responde_el_perfil(
    client: TestClient, make_user: Callable[..., int], login: Callable[[str], Headers]
) -> None:
    make_user("ana@ejemplo.com", Role.MEMBER)

    response = client.post(
        f"{API}/auth/login", json={"email": "ana@ejemplo.com", "password": PASSWORD}
    )
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"

    me = client.get(f"{API}/auth/me", headers=login("ana@ejemplo.com"))
    assert me.status_code == 200
    assert me.json()["email"] == "ana@ejemplo.com"
    assert me.json()["role"] == "miembro"
    assert "password_hash" not in me.json()


def test_login_con_contrasena_incorrecta_responde_401(
    client: TestClient, make_user: Callable[..., int]
) -> None:
    make_user("ana@ejemplo.com")

    response = client.post(
        f"{API}/auth/login", json={"email": "ana@ejemplo.com", "password": "otra-clave-larga"}
    )

    assert response.status_code == 401


def test_usuario_inactivo_no_puede_entrar(
    client: TestClient, make_user: Callable[..., int]
) -> None:
    make_user("baja@ejemplo.com", active=False)

    response = client.post(
        f"{API}/auth/login", json={"email": "baja@ejemplo.com", "password": PASSWORD}
    )

    assert response.status_code == 401


def test_endpoint_protegido_sin_token_responde_401(client: TestClient) -> None:
    assert client.get(f"{API}/auth/me").status_code == 401
    assert (
        client.get(f"{API}/auth/me", headers={"Authorization": "Bearer basura"}).status_code == 401
    )


def test_refresh_emite_nuevo_par_y_rechaza_el_token_de_acceso(
    client: TestClient, make_user: Callable[..., int]
) -> None:
    make_user("ana@ejemplo.com")
    tokens = client.post(
        f"{API}/auth/login", json={"email": "ana@ejemplo.com", "password": PASSWORD}
    ).json()

    refreshed = client.post(f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"]

    wrong_kind = client.post(f"{API}/auth/refresh", json={"refresh_token": tokens["access_token"]})
    assert wrong_kind.status_code == 401


def test_admin_crea_usuario_y_correo_repetido_da_409(
    client: TestClient, make_user: Callable[..., int], login: Callable[[str], Headers]
) -> None:
    make_user("admin@ejemplo.com", Role.ADMIN)
    headers = login("admin@ejemplo.com")
    body = {
        "email": "nuevo@ejemplo.com",
        "full_name": "Nuevo",
        "password": PASSWORD,
        "role": "lector",
    }

    created = client.post(f"{API}/users", json=body, headers=headers)
    assert created.status_code == 201
    assert created.json()["role"] == "lector"

    repeated = client.post(f"{API}/users", json=body, headers=headers)
    assert repeated.status_code == 409


def test_no_admin_no_puede_gestionar_usuarios(
    client: TestClient, make_user: Callable[..., int], login: Callable[[str], Headers]
) -> None:
    make_user("pm@ejemplo.com", Role.PROJECT_MANAGER)

    response = client.get(f"{API}/users", headers=login("pm@ejemplo.com"))

    assert response.status_code == 403


def test_admin_no_puede_desactivarse_a_si_mismo(
    client: TestClient, make_user: Callable[..., int], login: Callable[[str], Headers]
) -> None:
    admin_id = make_user("admin@ejemplo.com", Role.ADMIN)

    response = client.patch(
        f"{API}/users/{admin_id}", json={"is_active": False}, headers=login("admin@ejemplo.com")
    )

    assert response.status_code == 400
