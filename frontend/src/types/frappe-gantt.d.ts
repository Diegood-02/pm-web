// La librería frappe-gantt 1.x no incluye tipos TypeScript. Declaramos solo lo que usamos.
declare module "frappe-gantt" {
  export interface GanttTask {
    id: string;
    name: string;
    start: string;
    end: string;
    progress?: number;
    dependencies?: string;
    custom_class?: string;
  }

  export interface GanttOptions {
    view_mode?: "Quarter Day" | "Half Day" | "Day" | "Week" | "Month" | "Year";
    bar_height?: number;
    padding?: number;
    readonly?: boolean;
  }

  export default class Gantt {
    constructor(element: HTMLElement, tasks: GanttTask[], options?: GanttOptions);
    change_view_mode(mode: NonNullable<GanttOptions["view_mode"]>): void;
  }
}
