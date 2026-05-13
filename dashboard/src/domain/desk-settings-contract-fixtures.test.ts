import { describe, expect, it } from "vitest";
import fixture from "../../../tests/fixtures/contracts/desk_settings_status_v1.json";

import { sanitizeDeskAiSettingsStatus, sanitizeDeskNotificationTokenStatus } from "./sanitize";

type DeskSettingsFixture = {
  notification_token: unknown;
  ai_settings: unknown;
  frontend_input: {
    notification_token: unknown;
    ai_settings: unknown;
  };
  denied_strings: string[];
};

function asRecord(value: unknown): Record<string, unknown> {
  expect(value).toBeTypeOf("object");
  expect(value).not.toBeNull();
  return value as Record<string, unknown>;
}

function tokenStatusContract(value: unknown) {
  const record = asRecord(value);
  return {
    schema_version: record.schema_version,
    configured: record.configured,
    source: record.source,
    updated_at: record.updated_at,
    env_configured: record.env_configured,
    local_store_supported: record.local_store_supported,
    local_store_configured: record.local_store_configured,
    local_store_backend: record.local_store_backend,
    local_store_label: record.local_store_label,
    can_save: record.can_save,
    can_clear: record.can_clear,
    platform: record.platform,
  };
}

function aiSettingsContract(value: unknown) {
  const record = asRecord(value);
  const providers = Array.isArray(record.providers) ? record.providers : [];
  return {
    schema_version: record.schema_version,
    configured_count: record.configured_count,
    local_store_supported: record.local_store_supported,
    local_store_backend: record.local_store_backend,
    local_store_label: record.local_store_label,
    platform: record.platform,
    providers: providers.map(aiProviderContract),
  };
}

function aiProviderContract(value: unknown) {
  const record = asRecord(value);
  return {
    provider: record.provider,
    label: record.label,
    env_name: record.env_name,
    configured: record.configured,
    source: record.source,
    env_configured: record.env_configured,
    local_store_configured: record.local_store_configured,
    local_store_backend: record.local_store_backend,
    local_store_label: record.local_store_label,
    can_save: record.can_save,
    can_clear: record.can_clear,
    updated_at: record.updated_at,
  };
}

function expectDetail(value: unknown) {
  const record = asRecord(value);
  expect(record.detail).toBeTypeOf("string");
  expect(String(record.detail).trim()).not.toHaveLength(0);
}

describe("Desk settings status contract fixtures", () => {
  it("sanitizes notification token and AI settings without surfacing secrets", () => {
    const contract = fixture as DeskSettingsFixture;
    const notification = sanitizeDeskNotificationTokenStatus(contract.frontend_input.notification_token);
    const aiSettings = sanitizeDeskAiSettingsStatus(contract.frontend_input.ai_settings);
    const surfaced = JSON.stringify({ notification, aiSettings });

    expect(tokenStatusContract(notification)).toEqual(tokenStatusContract(contract.notification_token));
    expect(aiSettingsContract(aiSettings)).toEqual(aiSettingsContract(contract.ai_settings));
    expectDetail(notification);
    expectDetail(aiSettings);
    for (const provider of asRecord(aiSettings).providers as unknown[]) {
      expectDetail(provider);
    }
    for (const denied of contract.denied_strings) {
      expect(surfaced).not.toContain(denied);
    }
  });
});
