import { describe, expect, it } from "vitest";
import fixture from "../../../tests/fixtures/contracts/desk_bot_gateway_status_v1.json";

import { sanitizeDeskBotGatewayStatus, sanitizeDeskBotIdentityResult } from "./sanitize";

type BotGatewayFixture = {
  bot_gateway: unknown;
  identity: unknown;
  frontend_input: {
    bot_gateway: unknown;
    identity: unknown;
  };
  denied_strings: string[];
};

function asRecord(value: unknown): Record<string, unknown> {
  expect(value).toBeTypeOf("object");
  expect(value).not.toBeNull();
  return value as Record<string, unknown>;
}

function botGatewayContract(value: unknown) {
  const record = asRecord(value);
  const background = asRecord(record.background);
  return {
    schema_version: record.schema_version,
    token_configured: record.token_configured,
    authorized_chat_count: record.authorized_chat_count,
    gateway_status: record.gateway_status,
    commands_installed: record.commands_installed,
    supported_commands: record.supported_commands,
    local_first_note: record.local_first_note,
    start_command: record.start_command,
    started_at: record.started_at,
    last_poll_at: record.last_poll_at,
    background: {
      schema_version: background.schema_version,
      backend: background.backend,
      available: background.available,
      installed: background.installed,
      status: background.status,
      can_install: background.can_install,
      can_remove: background.can_remove,
      detail: background.detail,
      next_action: background.next_action,
      checked_at: background.checked_at,
    },
  };
}

function identityContract(value: unknown) {
  const record = asRecord(value);
  return {
    schema_version: record.schema_version,
    name: record.name,
    description_updated: record.description_updated,
    short_description_updated: record.short_description_updated,
    commands_installed: record.commands_installed,
    profile_photo_updated: record.profile_photo_updated,
  };
}

describe("Bot Gateway contract fixtures", () => {
  it("sanitizes gateway status and identity without surfacing private transport fields", () => {
    const contract = fixture as BotGatewayFixture;
    const status = sanitizeDeskBotGatewayStatus(contract.frontend_input.bot_gateway);
    const identity = sanitizeDeskBotIdentityResult(contract.frontend_input.identity);
    const surfaced = JSON.stringify({ status, identity });

    expect(botGatewayContract(status)).toEqual(botGatewayContract(contract.bot_gateway));
    expect(identityContract(identity)).toEqual(identityContract(contract.identity));
    for (const denied of contract.denied_strings) {
      expect(surfaced).not.toContain(denied);
    }
  });
});
