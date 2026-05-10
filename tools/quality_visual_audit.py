from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


def main() -> int:
    base_url = os.environ.get("TGCS_DASHBOARD_URL", "http://127.0.0.1:5173/")
    out_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "output/quality-review/latest")
    tabs = [
        tab.strip()
        for tab in os.environ.get("TGCS_DASHBOARD_TABS", "Start,Review,Runs,Settings").split(",")
        if tab.strip()
    ]
    viewports = [
        {"name": "desktop", "width": 1440, "height": 1000},
        {"name": "mobile", "width": 390, "height": 844},
    ]
    out_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, object]] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            for viewport in viewports:
                page = browser.new_page(viewport={"width": viewport["width"], "height": viewport["height"]})
                page.goto(base_url, wait_until="networkidle")
                page.wait_for_selector("[data-testid='tgcs-dashboard']", timeout=15_000)

                for tab in tabs:
                    page.locator(".tab", has_text=tab).first.click()
                    page.wait_for_timeout(250)
                    page.screenshot(path=out_dir / f"{viewport['name']}-{tab.lower()}.png", full_page=False)
                    metrics = page.evaluate(
                        """
                        () => {
                          const doc = document.documentElement;
                          const nav = document.querySelector(".nav-rail")?.getBoundingClientRect();
                          const smallTargets = Array.from(document.querySelectorAll("button, a, input, textarea, select"))
                            .map((item) => {
                              const rawRect = item.getBoundingClientRect();
                              const parentLabel = item.matches("input[type='checkbox'], input[type='radio']")
                                ? item.closest("label")?.getBoundingClientRect()
                                : null;
                              const rect = parentLabel && parentLabel.width > rawRect.width && parentLabel.height > rawRect.height
                                ? parentLabel
                                : rawRect;
                              const label =
                                item.getAttribute("aria-label") ||
                                item.getAttribute("title") ||
                                item.textContent?.trim().replace(/\\s+/g, " ") ||
                                item.getAttribute("placeholder") ||
                                item.tagName.toLowerCase();
                              return {
                                label,
                                width: Math.round(rect.width),
                                height: Math.round(rect.height),
                                visible: rect.width > 0 && rect.height > 0,
                              };
                            })
                            .filter((item) => item.visible && (item.width < 44 || item.height < 44));
                          return {
                            title: document.querySelector(".workbench-title, h2, h3")?.textContent?.trim() || "",
                            scrollHeight: doc.scrollHeight,
                            clientHeight: doc.clientHeight,
                            horizontalOverflow: doc.scrollWidth > doc.clientWidth + 1,
                            nav: nav
                              ? {
                                  top: Math.round(nav.top),
                                  bottom: Math.round(nav.bottom),
                                  height: Math.round(nav.height),
                                }
                              : null,
                            smallTargets: smallTargets.slice(0, 16),
                            smallTargetCount: smallTargets.length,
                          };
                        }
                        """
                    )
                    results.append({"viewport": viewport["name"], "tab": tab, **metrics})

                page.close()
        finally:
            browser.close()

    (out_dir / "visual-audit.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"outDir": str(out_dir), "results": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
