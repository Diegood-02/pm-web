import { Link, Navigate, Route, Routes } from "react-router-dom";
import type { ReactNode } from "react";

import { useAuth } from "./auth/AuthContext";
import { LoginPage } from "./pages/LoginPage";
import { ProjectPage } from "./pages/ProjectPage";
import { ProjectsPage } from "./pages/ProjectsPage";
import { UsersPage } from "./pages/UsersPage";

function ProtectedRoute({
  children,
  adminOnly = false,
}: {
  children: ReactNode;
  adminOnly?: boolean;
}) {
  const { user, loading } = useAuth();
  if (loading) return <p role="status">Cargando sesión…</p>;
  if (!user) return <Navigate to="/login" replace />;
  if (adminOnly && user.role !== "admin") return <Navigate to="/" replace />;
  return <>{children}</>;
}

function Shell({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  return (
    <>
      <a className="skip-link" href="#contenido">
        Saltar al contenido
      </a>
      <header className="app-header">
        <Link to="/" className="brand">
          PM Web
        </Link>
        <nav aria-label="Principal">
          <Link to="/">Proyectos</Link>
          {user?.role === "admin" && <Link to="/usuarios">Usuarios</Link>}
        </nav>
        <div className="session">
          <span>{user?.full_name}</span>
          <button type="button" onClick={logout}>
            Salir
          </button>
        </div>
      </header>
      <main id="contenido" tabIndex={-1}>
        {children}
      </main>
    </>
  );
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Shell>
              <ProjectsPage />
            </Shell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/proyectos/:projectId"
        element={
          <ProtectedRoute>
            <Shell>
              <ProjectPage />
            </Shell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/usuarios"
        element={
          <ProtectedRoute adminOnly>
            <Shell>
              <UsersPage />
            </Shell>
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}
