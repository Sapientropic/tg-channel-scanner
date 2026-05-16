import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { ConsoleHeader } from "./shell";

describe("ConsoleHeader", () => {
  it("uses the header action for a new scan instead of manual state refresh", () => {
    const html = renderToStaticMarkup(
      <ConsoleHeader
        busy={false}
        primaryActionLabel="Demo report"
        primaryActionTitle="Generate a local sample report"
        onNewScan={vi.fn()}
        onOpenUpdates={vi.fn()}
        updateAvailableCount={0}
      />,
    );

    expect(html).toContain("Demo report");
    expect(html).toContain("Open settings");
    expect(html).toContain("Generate a local sample report");
    expect(html).not.toContain("New scan");
    expect(html).not.toContain("Open updates");
    expect(html).not.toContain("Refresh");
    expect(html).not.toContain("Refresh state");
  });
});
