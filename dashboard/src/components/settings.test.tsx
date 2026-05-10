import { describe, expect, it } from "vitest";

import { filterDeskSourcesByQuery, sourceTopicsEditState } from "./settings";
import type { DeskSource } from "../domain/types";

function source(overrides: Partial<DeskSource>): DeskSource {
  return {
    source_id: "telegram:remote_jobs",
    label: "remote_jobs",
    channel: "remote_jobs",
    enabled: true,
    topics: ["jobs"],
    priority: "normal",
    scan_window_hours: 24,
    ...overrides,
  };
}

describe("Settings source topic editor", () => {
  it("normalizes and validates source topic edits", () => {
    expect(sourceTopicsEditState(["jobs"], "jobs")).toMatchObject({ canSave: false, topics: ["jobs"] });
    expect(sourceTopicsEditState(["jobs"], " Remote-Work, jobs, remote-work ")).toMatchObject({
      canSave: true,
      topics: ["remote-work", "jobs"],
    });
    expect(sourceTopicsEditState(["jobs"], "jobs\nremote-work")).toMatchObject({
      canSave: true,
      topics: ["jobs", "remote-work"],
    });
    expect(sourceTopicsEditState(["jobs"], " ")).toMatchObject({ canSave: false, topics: [] });
    expect(sourceTopicsEditState(["jobs"], "../private")).toMatchObject({ canSave: false });
    expect(sourceTopicsEditState(["jobs"], "x")).toMatchObject({ canSave: false });
    expect(sourceTopicsEditState(["jobs"], "-jobs")).toMatchObject({ canSave: false });
    expect(sourceTopicsEditState(["jobs"], "_jobs")).toMatchObject({ canSave: false });
    expect(sourceTopicsEditState(["jobs"], "工作")).toMatchObject({ canSave: false });
    expect(sourceTopicsEditState(["jobs"], `a${"b".repeat(41)}`)).toMatchObject({ canSave: false });
    expect(sourceTopicsEditState(["jobs"], "jobs, 123")).toMatchObject({ canSave: true, topics: ["jobs", "123"] });
  });

  it("limits topic count", () => {
    const text = Array.from({ length: 9 }, (_, index) => `topic${index}`).join(", ");

    expect(sourceTopicsEditState(["jobs"], text)).toMatchObject({ canSave: false });
  });

  it("filters saved sources by topic chips or search text", () => {
    const sources = [
      source({ source_id: "telegram:remote_jobs", label: "Remote Jobs", topics: ["jobs", "remote-work"] }),
      source({ source_id: "telegram:market_news", label: "Market News", channel: "market_news", topics: ["jobs", "market-news"] }),
    ];

    expect(filterDeskSourcesByQuery(sources, "", "remote-work").map((item) => item.source_id)).toEqual([
      "telegram:remote_jobs",
    ]);
    expect(filterDeskSourcesByQuery(sources, "market").map((item) => item.source_id)).toEqual([
      "telegram:market_news",
    ]);
    expect(filterDeskSourcesByQuery(sources, "news", "jobs").map((item) => item.source_id)).toEqual([
      "telegram:market_news",
    ]);
    expect(filterDeskSourcesByQuery(sources, "rem", "jobs").map((item) => item.source_id)).toEqual([
      "telegram:remote_jobs",
    ]);
    expect(filterDeskSourcesByQuery(sources, " ", " ").map((item) => item.source_id)).toEqual([
      "telegram:remote_jobs",
      "telegram:market_news",
    ]);
  });
});
