import { useRef } from "react";
import type { KeyboardEvent } from "react";

export interface TabDefinition {
  id: string;
  label: string;
}

interface TabListProps {
  tabs: TabDefinition[];
  selected: string;
  onSelect: (id: string) => void;
}

/**
 * Pestañas con navegación de teclado según el patrón WAI-ARIA:
 * flechas izquierda/derecha para moverse, Inicio y Fin para saltar a los extremos.
 */
export function TabList({ tabs, selected, onSelect }: TabListProps) {
  const buttons = useRef<Map<string, HTMLButtonElement>>(new Map());

  function focusTab(index: number) {
    const tab = tabs[index];
    onSelect(tab.id);
    buttons.current.get(tab.id)?.focus();
  }

  function handleKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    const last = tabs.length - 1;
    switch (event.key) {
      case "ArrowRight":
        focusTab(index === last ? 0 : index + 1);
        break;
      case "ArrowLeft":
        focusTab(index === 0 ? last : index - 1);
        break;
      case "Home":
        focusTab(0);
        break;
      case "End":
        focusTab(last);
        break;
      default:
        return;
    }
    event.preventDefault();
  }

  return (
    <div role="tablist" aria-label="Secciones del proyecto" className="tablist">
      {tabs.map((tab, index) => {
        const isSelected = tab.id === selected;
        return (
          <button
            key={tab.id}
            type="button"
            role="tab"
            id={`tab-${tab.id}`}
            aria-selected={isSelected}
            aria-controls={`panel-${tab.id}`}
            tabIndex={isSelected ? 0 : -1}
            ref={(element) => {
              if (element) buttons.current.set(tab.id, element);
              else buttons.current.delete(tab.id);
            }}
            onClick={() => onSelect(tab.id)}
            onKeyDown={(event) => handleKeyDown(event, index)}
            className={isSelected ? "tab selected" : "tab"}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}
