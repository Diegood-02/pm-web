import { request } from "./client";
import type {
  Assignment,
  BaselineSummary,
  CostReport,
  BaselineVariance,
  Dependency,
  DependencyType,
  Member,
  Project,
  ProjectRole,
  Resource,
  Role,
  Schedule,
  Task,
  TokenPair,
  User,
} from "./types";

export const api = {
  login: (email: string, password: string) =>
    request<TokenPair>("/auth/login", { method: "POST", body: { email, password }, auth: false }),
  me: () => request<User>("/auth/me"),

  users: () => request<User[]>("/users?limit=200"),
  createUser: (body: { email: string; full_name: string; password: string; role: Role }) =>
    request<User>("/users", { method: "POST", body }),
  updateUser: (id: number, body: { role?: Role; is_active?: boolean }) =>
    request<User>(`/users/${id}`, { method: "PATCH", body }),

  projects: () => request<Project[]>("/projects"),
  createProject: (body: { name: string; start_date: string }) =>
    request<Project>("/projects", { method: "POST", body }),
  project: (id: number) => request<Project>(`/projects/${id}`),

  members: (projectId: number) => request<Member[]>(`/projects/${projectId}/members`),
  addMember: (projectId: number, userId: number, role: ProjectRole) =>
    request<Member>(`/projects/${projectId}/members`, {
      method: "POST",
      body: { user_id: userId, role },
    }),

  tasks: (projectId: number) => request<Task[]>(`/projects/${projectId}/tasks`),
  createTask: (
    projectId: number,
    body: { name: string; duration_days: number; is_milestone: boolean; parent_id: number | null },
  ) => request<Task>(`/projects/${projectId}/tasks`, { method: "POST", body }),
  updateTask: (
    projectId: number,
    taskId: number,
    body: {
      version: number;
      name?: string;
      duration_days?: number;
      is_milestone?: boolean;
      fixed_cost?: number;
      actual_cost?: number;
      percent_complete?: number;
    },
  ) => request<Task>(`/projects/${projectId}/tasks/${taskId}`, { method: "PATCH", body }),
  moveTask: (
    projectId: number,
    taskId: number,
    body: { version: number; parent_id: number | null; position: number },
  ) => request<Task>(`/projects/${projectId}/tasks/${taskId}/move`, { method: "POST", body }),
  deleteTask: (projectId: number, taskId: number) =>
    request<void>(`/projects/${projectId}/tasks/${taskId}`, { method: "DELETE" }),

  dependencies: (projectId: number) => request<Dependency[]>(`/projects/${projectId}/dependencies`),
  createDependency: (
    projectId: number,
    body: {
      predecessor_id: number;
      successor_id: number;
      type: DependencyType;
      lag_days: number;
    },
  ) => request<Dependency>(`/projects/${projectId}/dependencies`, { method: "POST", body }),
  deleteDependency: (projectId: number, dependencyId: number) =>
    request<void>(`/projects/${projectId}/dependencies/${dependencyId}`, { method: "DELETE" }),

  resources: (projectId: number) => request<Resource[]>(`/projects/${projectId}/resources`),
  createResource: (
    projectId: number,
    body: { name: string; max_units: number; hourly_rate: number },
  ) => request<Resource>(`/projects/${projectId}/resources`, { method: "POST", body }),
  updateResource: (projectId: number, resourceId: number, body: { hourly_rate: number }) =>
    request<Resource>(`/projects/${projectId}/resources/${resourceId}`, { method: "PATCH", body }),
  deleteResource: (projectId: number, resourceId: number) =>
    request<void>(`/projects/${projectId}/resources/${resourceId}`, { method: "DELETE" }),

  assignments: (projectId: number) => request<Assignment[]>(`/projects/${projectId}/assignments`),
  assignResource: (
    projectId: number,
    taskId: number,
    body: { resource_id: number; units_percent: number },
  ) =>
    request<Assignment>(`/projects/${projectId}/tasks/${taskId}/assignments`, {
      method: "POST",
      body,
    }),
  deleteAssignment: (projectId: number, assignmentId: number) =>
    request<void>(`/projects/${projectId}/assignments/${assignmentId}`, { method: "DELETE" }),

  schedule: (projectId: number) => request<Schedule>(`/projects/${projectId}/schedule`),
  costs: (projectId: number, statusDate: string) =>
    request<CostReport>(`/projects/${projectId}/costs?status_date=${statusDate}`),

  baselines: (projectId: number) => request<BaselineSummary[]>(`/projects/${projectId}/baselines`),
  createBaseline: (projectId: number, name: string) =>
    request<BaselineSummary>(`/projects/${projectId}/baselines`, {
      method: "POST",
      body: { name },
    }),
  baselineComparison: (projectId: number, baselineId: number) =>
    request<BaselineVariance[]>(`/projects/${projectId}/baselines/${baselineId}/comparison`),
};
