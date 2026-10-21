// Tipos que reflejan los esquemas de la API (backend/app/schemas.py).

export type Role = "admin" | "project_manager" | "miembro" | "lector";
export type ProjectRole = Exclude<Role, "admin">;
export type DependencyType = "FS" | "SS" | "FF" | "SF";

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface Project {
  id: number;
  name: string;
  description: string;
  timezone: string;
  start_date: string;
  working_weekdays: number[];
  hours_per_day: number;
  holidays: string[];
  extra_working_days: string[];
  version: number;
  created_at: string;
  updated_at: string;
}

export interface Member {
  user_id: number;
  email: string;
  full_name: string;
  role: ProjectRole;
}

export interface Task {
  id: number;
  parent_id: number | null;
  wbs: string;
  position: number;
  name: string;
  duration_days: number;
  is_milestone: boolean;
  fixed_cost: number;
  actual_cost: number;
  percent_complete: number;
  version: number;
}

export interface Dependency {
  id: number;
  predecessor_id: number;
  successor_id: number;
  type: DependencyType;
  lag_days: number;
}

export interface Resource {
  id: number;
  name: string;
  max_units: number;
  hourly_rate: number;
}

export interface Assignment {
  id: number;
  task_id: number;
  resource_id: number;
  units_percent: number;
}

export interface ScheduleTask {
  task_id: number;
  wbs: string;
  name: string;
  is_milestone: boolean;
  duration_days: number;
  early_start: number;
  early_finish: number;
  late_start: number;
  late_finish: number;
  total_float: number;
  free_float: number;
  is_critical: boolean;
  start_date: string;
  finish_date: string;
}

export interface Schedule {
  project_id: number;
  project_start: string;
  project_finish: string;
  duration_days: number;
  critical_path: number[];
  tasks: ScheduleTask[];
}

export interface BaselineSummary {
  id: number;
  name: string;
  created_at: string;
  project_finish: string;
  duration_days: number;
}

export interface BaselineVariance {
  task_id: number | null;
  wbs: string;
  name: string;
  baseline_start: string;
  baseline_finish: string;
  current_start: string | null;
  current_finish: string | null;
  start_variance_days: number | null;
  finish_variance_days: number | null;
}

export interface CostTask {
  task_id: number;
  wbs: string;
  name: string;
  budget: number;
  percent_complete: number;
  fixed_cost: number;
  planned_value: number;
  earned_value: number;
  actual_cost: number;
}

export interface CostSummary {
  bac: number;
  pv: number;
  ev: number;
  ac: number;
  cv: number;
  sv: number;
  cpi: number | null;
  spi: number | null;
  threshold: number;
  cpi_alert: boolean;
  spi_alert: boolean;
}

export interface CostReport {
  project_id: number;
  status_date: string;
  summary: CostSummary;
  tasks: CostTask[];
}
