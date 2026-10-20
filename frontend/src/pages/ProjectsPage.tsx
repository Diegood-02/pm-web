import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router-dom";

import { ApiError } from "../api/client";
import { api } from "../api/endpoints";
import { useAuth } from "../auth/AuthContext";
import type { Project } from "../api/types";

export function ProjectsPage() {
  const { user } = useAuth();
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [startDate, setStartDate] = useState(() => new Date().toISOString().slice(0, 10));

  const canCreate = user?.role === "admin" || user?.role === "project_manager";

  useEffect(() => {
    api
      .projects()
      .then(setProjects)
      .catch(() => setError("No se pudieron cargar los proyectos."));
  }, []);

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      const project = await api.createProject({ name, start_date: startDate });
      setProjects((current) => [...(current ?? []), project]);
      setName("");
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "No se pudo crear el proyecto.");
    }
  }

  return (
    <section aria-labelledby="titulo-proyectos">
      <h1 id="titulo-proyectos">Proyectos</h1>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}

      {projects === null && !error && <p role="status">Cargando proyectos…</p>}
      {projects?.length === 0 && <p>Todavía no perteneces a ningún proyecto.</p>}
      {projects && projects.length > 0 && (
        <ul className="project-list">
          {projects.map((project) => (
            <li key={project.id}>
              <Link to={`/proyectos/${project.id}`}>{project.name}</Link>
              <span className="muted"> · inicio {project.start_date}</span>
            </li>
          ))}
        </ul>
      )}

      {canCreate && (
        <form className="inline-form" onSubmit={handleCreate} aria-label="Nuevo proyecto">
          <h2>Nuevo proyecto</h2>
          <div className="field">
            <label htmlFor="project-name">Nombre</label>
            <input
              id="project-name"
              required
              maxLength={200}
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="project-start">Fecha de inicio</label>
            <input
              id="project-start"
              type="date"
              required
              value={startDate}
              onChange={(event) => setStartDate(event.target.value)}
            />
          </div>
          <button type="submit">Crear proyecto</button>
        </form>
      )}
    </section>
  );
}
