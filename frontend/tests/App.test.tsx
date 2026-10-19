import { render, screen } from "@testing-library/react";

import { App } from "../src/App";

describe("App", () => {
  it("muestra el título de la aplicación", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: "PM Web" })).toBeInTheDocument();
  });
});
