# Licensing

T-Sense uses a dual-license model:

- Community License: GNU Affero General Public License v3.0 only
  (`AGPL-3.0-only`).
- Commercial License: available separately from Sapientropic.

Project copyright: Copyright (c) 2026 Sapientropic.

This page explains the project policy for maintainers, users, and contributors.
It is not legal advice.

## What Changed

Starting with project versions after the relicensing change, project code is no
longer MIT-licensed by default. New project code is available under
`AGPL-3.0-only` unless Sapientropic grants a separate written commercial license.

Older copies that were already released under MIT keep the license they were
released with. The relicensing change applies to future project versions and
future contributions accepted under this policy.

Third-party dependencies, generated lockfiles, and externally licensed assets
keep their own licenses. Their package metadata may still mention MIT, Apache,
BSD, ISC, LGPL, or other licenses; those notices do not change the license of
T-Sense itself.

## Community Version

The community version is licensed under `AGPL-3.0-only`.

You can use it for personal, research, internal, and commercial work as long as
you follow the AGPL terms. In practice, this means:

- Keep copyright and license notices intact.
- Share the corresponding source when you distribute covered versions.
- If users interact with a modified version over a network, provide those users
  access to the corresponding source for that modified version, as required by
  AGPL section 13.
- Do not remove warranty disclaimers or present the project as an official
  Telegram product.

The community version is a good fit when you are comfortable with AGPL source
sharing obligations and want to keep improvements available to the community.

## Commercial License

A commercial license is intended for teams that want to use T-Sense
without AGPL obligations applying to their proprietary product or deployment.

Typical commercial-license cases include:

- Closed-source redistribution.
- Proprietary SaaS or hosted offerings.
- Private forks with modifications that should not be shared under AGPL.
- Embedding the scanner into a paid product, internal platform, or managed
  service with customer terms that conflict with AGPL.
- Enterprise support, deployment help, warranty terms, indemnity, or other
  contract-specific requirements.

Commercial license terms are not granted by this repository. They require a
separate written agreement from Sapientropic.

## Hosted Services

AGPL does not ban hosted use. It requires source availability for covered
modified versions when users interact with them over a network.

Use the community version for hosted services only if you are ready to comply
with AGPL obligations, including source access for modified versions. Choose a
commercial license if you want to operate a proprietary hosted service, keep
modifications private, or offer customer terms that are not compatible with
AGPL.

Private personal use and internal experiments usually do not need a commercial
license solely because they run on a server. The issue is whether your use,
distribution, network operation, and modifications trigger AGPL obligations that
you do not want to accept.

## Contributions

To keep the dual-license model workable, contributions must be compatible with
both the community license and commercial licensing by Sapientropic.

By submitting a contribution, you represent that:

- You have the right to submit the contribution.
- The contribution is your original work, or you have permission to contribute
  it under this policy.
- You license the contribution to the project under `AGPL-3.0-only`.
- You also grant Sapientropic the right to use, sublicense, and relicense the
  contribution as part of T-Sense under separate commercial licenses.
- You will not submit code, prompts, data, generated assets, or documentation
  copied from third-party sources unless their license is compatible with this
  policy.

For larger contributions, maintainers may ask for an explicit confirmation in
the pull request, such as:

> I confirm that I have the right to submit this contribution and that I license
> it to T-Sense under AGPL-3.0-only and to Sapientropic for separate
> commercial licensing as described in docs/licensing.md.

Contributions that do not support this dual-license model may be declined even
if the code is technically useful.

## Practical Rules For Maintainers

- Keep `LICENSE` as the authority for the community license text.
- Keep this file as the authority for policy explanations. README files should
  link here instead of duplicating the full policy.
- Do not merge third-party code unless its license is compatible with
  `AGPL-3.0-only` and commercial relicensing.
- Do not copy GPL/AGPL-incompatible code snippets into the project.
- Add SPDX identifiers to new source files when the project starts using
  per-file license headers.

## References

- [GNU Affero General Public License v3.0](https://www.gnu.org/licenses/agpl-3.0.en.html)
- [SPDX AGPL-3.0-only identifier](https://spdx.org/licenses/AGPL-3.0-only.html)
