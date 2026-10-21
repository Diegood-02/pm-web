import { useEffect, useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import { Link } from "react-router-dom";

import { ApiError } from "../api/client";
import { api } from "../api/endpoints";
import { useAuth } from "../auth/AuthContext";
import type { Project } from "../api/types";

/** Lee un archivo como texto. Usa FileReader porque es compatible con todos los navegadores. */
function readFileText(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(reader.error);
    reader.readAsText(file);
  });
}

export function ProjectsPage() {
  const { user } = useAuth();
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [startDate, setStartDate] = useState(() => new Date().toISOString().slice(0, 10));

  const canCreate = user?.role === "admin" || user?.role === "project_manager";

  useEffect(() => {
    api
      .projects()
      .then(setProjects)
      .catch(() => setError("No se pudieron cargar los proyectos."));
  }, []);

  async function handleImport(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setError(null);
    setNotice(null);
    let payload: unknown;
    try {
      payload = JSON.parse(await readFileText(file));
    } catch {
      setError("El archivo no es JSON válido.");
      return;
    }
    try {
      const project = await api.importProject(payload);
      setProjects((current) => [...(current ?? []), project]);
      setNotice(`Proyecto importado: ${project.name}.`);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "No se pudo importar el proyecto.");
    }
  }

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
      {notice && (
        <p role="status" className="notice">
          {notice}
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
        <div className="inline-form">
          <h2>Importar proyecto</h2>
          <div className="field">
            <label htmlFor="project-import">Archivo JSON exportado desde PM Web</label>
            <input
              id="project-import"
              type="file"
              accept="application/json,.json"
              onChange={handleImport}
            />
          </div>
        </div>
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
