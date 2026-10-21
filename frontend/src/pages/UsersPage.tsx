import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import { ApiError } from "../api/client";
import { api } from "../api/endpoints";
import type { Role, User } from "../api/types";

const ROLE_LABELS: Record<Role, string> = {
  admin: "Administrador",
  project_manager: "Project manager",
  miembro: "Miembro",
  lector: "Lector",
};

export function UsersPage() {
  const [users, setUsers] = useState<User[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    email: "",
    full_name: "",
    password: "",
    role: "miembro" as Role,
  });

  useEffect(() => {
    api
      .users()
      .then(setUsers)
      .catch(() => setError("No se pudieron cargar los usuarios."));
  }, []);

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      const created = await api.createUser(form);
      setUsers((current) => [...(current ?? []), created]);
      setForm({ email: "", full_name: "", password: "", role: "miembro" });
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "No se pudo crear el usuario.");
    }
  }

  async function changeRole(target: User, role: Role) {
    try {
      const updated = await api.updateUser(target.id, { role });
      setUsers((current) => current?.map((u) => (u.id === updated.id ? updated : u)) ?? null);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "No se pudo cambiar el rol.");
    }
  }

  async function toggleActive(target: User) {
    try {
      const updated = await api.updateUser(target.id, { is_active: !target.is_active });
      setUsers((current) => current?.map((u) => (u.id === updated.id ? updated : u)) ?? null);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "No se pudo cambiar el estado.");
    }
  }

  return (
    <section aria-labelledby="titulo-usuarios">
      <h1 id="titulo-usuarios">Usuarios</h1>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}

      {users && (
        <table>
          <caption className="sr-only">Usuarios del sistema</caption>
          <thead>
            <tr>
              <th scope="col">Nombre</th>
              <th scope="col">Correo</th>
              <th scope="col">Rol</th>
              <th scope="col">Activo</th>
              <th scope="col">Acción</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td>{u.full_name}</td>
                <td>{u.email}</td>
                <td>
                  <label className="sr-only" htmlFor={`role-${u.id}`}>
                    Rol de {u.full_name}
                  </label>
                  <select
                    id={`role-${u.id}`}
                    value={u.role}
                    onChange={(event) => changeRole(u, event.target.value as Role)}
                  >
                    {(Object.keys(ROLE_LABELS) as Role[]).map((role) => (
                      <option key={role} value={role}>
                        {ROLE_LABELS[role]}
                      </option>
                    ))}
                  </select>
                </td>
                <td>{u.is_active ? "Sí" : "No"}</td>
                <td>
                  <button type="button" onClick={() => toggleActive(u)}>
                    {u.is_active ? `Desactivar a ${u.full_name}` : `Activar a ${u.full_name}`}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <form className="inline-form" onSubmit={handleCreate} aria-label="Nuevo usuario">
        <h2>Invitar usuario</h2>
        <div className="field">
          <label htmlFor="new-email">Correo</label>
          <input
            id="new-email"
            type="email"
            required
            value={form.email}
            onChange={(event) => setForm({ ...form, email: event.target.value })}
          />
        </div>
        <div className="field">
          <label htmlFor="new-name">Nombre completo</label>
          <input
            id="new-name"
            required
            value={form.full_name}
            onChange={(event) => setForm({ ...form, full_name: event.target.value })}
          />
        </div>
        <div className="field">
          <label htmlFor="new-password">Contraseña temporal (mínimo 12 caracteres)</label>
          <input
            id="new-password"
            type="password"
            required
            minLength={12}
            autoComplete="new-password"
            value={form.password}
            onChange={(event) => setForm({ ...form, password: event.target.value })}
          />
        </div>
        <div className="field">
          <label htmlFor="new-role">Rol</label>
          <select
            id="new-role"
            value={form.role}
            onChange={(event) => setForm({ ...form, role: event.target.value as Role })}
          >
            {(Object.keys(ROLE_LABELS) as Role[]).map((role) => (
              <option key={role} value={role}>
                {ROLE_LABELS[role]}
              </option>
            ))}
          </select>
        </div>
        <button type="submit">Crear usuario</button>
      </form>
    </section>
  );
}
