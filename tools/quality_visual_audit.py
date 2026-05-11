from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import TypedDict

from playwright.sync_api import sync_playwright


class Viewport(TypedDict):
    name: str
    width: int
    height: int


def _parse_tabs(raw: str) -> list[str]:
    return [tab.strip() for tab in raw.split(",") if tab.strip()]


def _parse_viewports(raw: str) -> list[Viewport]:
    viewports: list[Viewport] = []
    for chunk in raw.split(","):
        item = chunk.strip()
        if not item:
            continue
        try:
            name, size = item.split(":", 1)
            width_text, height_text = size.lower().split("x", 1)
            width = int(width_text.strip())
            height = int(height_text.strip())
        except ValueError as exc:
            raise SystemExit(
                "TGCS_DASHBOARD_VIEWPORTS must use comma-separated name:WIDTHxHEIGHT entries, "
                "for example desktop:1440x1000,mobile:390x844"
            ) from exc
        if not name.strip() or width <= 0 or height <= 0:
            raise SystemExit("TGCS_DASHBOARD_VIEWPORTS entries must have a name and positive dimensions.")
        viewports.append({"name": name.strip(), "width": width, "height": height})
    if not viewports:
        raise SystemExit("At least one dashboard viewport is required.")
    return viewports


def main() -> int:
    base_url = os.environ.get("TGCS_DASHBOARD_URL", "http://127.0.0.1:5173/")
    out_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "output/quality-review/latest")
    tabs = _parse_tabs(os.environ.get("TGCS_DASHBOARD_TABS", "Start,Review,Profiles,Runs,Settings"))
    viewports = _parse_viewports(
        os.environ.get(
            "TGCS_DASHBOARD_VIEWPORTS",
            "desktop:1440x1000,desktop-1360:1360x900,tablet-1024:1024x768,mobile:390x844,mobile-375:375x812",
        )
    )
    if os.environ.get("TGCS_DASHBOARD_INCLUDE_PRESSURE") == "1":
        viewports.append({"name": "mobile-320", "width": 320, "height": 812})
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
                    tab_button = page.locator(".tab", has_text=tab).first
                    tab_button.click()
                    page.wait_for_timeout(250)
                    page.screenshot(path=out_dir / f"{viewport['name']}-{tab.lower()}.png", full_page=False)
                    metrics = page.evaluate(
                        """
                        () => {
                          const doc = document.documentElement;
                          const nav = document.querySelector(".nav-rail")?.getBoundingClientRect();
                          const activeTab = document.querySelector(".tab.active")?.textContent?.trim().replace(/\\s+/g, " ") || "";
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
                            activeTab,
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
