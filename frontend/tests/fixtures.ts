import type { Project, Schedule, Task, User } from "../src/api/types";

export const adminUser: User = {
  id: 1,
  email: "admin@ejemplo.com",
  full_name: "Ada Admin",
  role: "admin",
  is_active: true,
};

export const memberUser: User = {
  id: 2,
  email: "miembro@ejemplo.com",
  full_name: "Mario Miembro",
  role: "miembro",
  is_active: true,
};

export const project: Project = {
  id: 5,
  name: "Migración ERP",
  description: "",
  timezone: "America/Mexico_City",
  start_date: "2026-01-05",
  working_weekdays: [0, 1, 2, 3, 4],
  hours_per_day: 8,
  holidays: [],
  extra_working_days: [],
  version: 1,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

export const tasks: Task[] = [
  {
    id: 10,
    parent_id: null,
    wbs: "1",
    position: 0,
    name: "Diseño",
    duration_days: 3,
    is_milestone: false,
    version: 2,
  },
  {
    id: 11,
    parent_id: null,
    wbs: "2",
    position: 1,
    name: "Construcción",
    duration_days: 4,
    is_milestone: false,
    version: 1,
  },
];

export const schedule: Schedule = {
  project_id: 5,
  project_start: "2026-01-05",
  project_finish: "2026-01-14",
  duration_days: 7,
  critical_path: [10, 11],
  tasks: [
    {
      task_id: 10,
      wbs: "1",
      name: "Diseño",
      is_milestone: false,
      duration_days: 3,
      early_start: 0,
      early_finish: 3,
      late_start: 0,
      late_finish: 3,
      total_float: 0,
      free_float: 0,
      is_critical: true,
      start_date: "2026-01-05",
      finish_date: "2026-01-07",
    },
    {
      task_id: 11,
      wbs: "2",
      name: "Construcción",
      is_milestone: false,
      duration_days: 4,
      early_start: 3,
      early_finish: 7,
      late_start: 3,
      late_finish: 7,
      total_float: 0,
      free_float: 0,
      is_critical: true,
      start_date: "2026-01-08",
      finish_date: "2026-01-14",
    },
  ],
};
