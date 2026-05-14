import type { DeskSource, SourceStat } from "../../domain/types";

export const SOURCE_LIBRARY_PAGE_SIZE = 8;

export function filterDeskSourcesByQuery(sources: DeskSource[], query: string, selectedTopic = "") {
  const normalizedQuery = query.trim().toLowerCase();
  const normalizedTopic = selectedTopic.trim().toLowerCase();
  if (!normalizedQuery && !normalizedTopic) {
    return sources;
  }
  return sources.filter((source) => {
    const matchesTopic = normalizedTopic
      ? source.topics.some((topic) => topic.trim().toLowerCase() === normalizedTopic)
      : true;
    if (!matchesTopic) {
      return false;
    }
    if (!normalizedQuery) {
      return true;
    }
    return [source.label, source.channel, source.priority, ...source.topics]
      .join(" ")
      .toLowerCase()
      .includes(normalizedQuery);
  });
}

export function paginatedDeskSources(sources: DeskSource[], visibleCount = SOURCE_LIBRARY_PAGE_SIZE) {
  return sources.slice(0, Math.max(0, visibleCount));
}

export function sourceLibraryCountLabel(visibleCount: number, filteredCount: number, hasFilters: boolean) {
  const visible = Math.max(0, visibleCount);
  const filtered = Math.max(0, filteredCount);
  if (hasFilters) {
    if (!filtered) {
      return "No matching sources";
    }
    return visible >= filtered ? `${filtered} matching shown` : `${visible} of ${filtered} matching shown`;
  }
  if (!filtered) {
    return "No saved sources";
  }
  return visible >= filtered ? `Showing all ${filtered}` : `Showing first ${visible} of ${filtered}`;
}

export function sourceLibraryActivityLabel(sources: SourceStat[]) {
  if (!sources.length) {
    return "";
  }
  const latestCards = sources.reduce((sum, source) => sum + Math.max(0, source.latest_card_count ?? 0), 0);
  const alerts = sources.reduce((sum, source) => sum + Math.max(0, source.alert_count ?? 0), 0);
  const risk = sources.filter((source) => source.scan_failure || source.scan_incomplete).length;
  const parts = [
    latestCards ? `${latestCards} latest card${latestCards === 1 ? "" : "s"}` : "No latest cards",
    alerts ? `${alerts} alert${alerts === 1 ? "" : "s"}` : "",
    `${sources.length} tracked`,
    risk ? `${risk} risk` : "",
  ].filter(Boolean);
  return parts.join(" · ");
}

export function sourceTopicsEditState(currentTopics: string[], text: string) {
  const rawTopics = text
    .split(/[,\n]/)
    .map((topic) => topic.trim().toLowerCase())
    .filter(Boolean);
  const topics = Array.from(new Set(rawTopics));
  const invalid = topics.find((topic) => !/^[a-z0-9][a-z0-9_-]{1,40}$/.test(topic));
  const normalizedCurrent = currentTopics.map((topic) => topic.trim().toLowerCase()).filter(Boolean);
  const unchanged = topics.join("\0") === normalizedCurrent.join("\0");
  if (invalid) {
    return { canSave: false, topics, message: "Use short tags like jobs or remote-work." };
  }
  if (!topics.length) {
    return { canSave: false, topics, message: "Add at least one topic tag." };
  }
  if (topics.length > 8) {
    return { canSave: false, topics, message: "Use fewer topic tags." };
  }
  if (unchanged) {
    return { canSave: false, topics, message: "Topics are unchanged." };
  }
  return { canSave: true, topics, message: "Comma-separated tags. These tags only organize your sources." };
}
