# Quilt Platform Release Notes

This directory contains the source Markdown and HubSpot coded-email templates for Quilt Platform release announcements.

## File naming

Use the full three-part release version in both source filenames:

```text
<version>-release-notes.md
<version>-release-notes.html
```

For example, Quilt Platform 26.7.0 uses:

```text
26-7-0-release-notes.md
26-7-0-release-notes.html
```

Platform versions are date-based beginning with 26.7: `26.7` is July 2026, and the third number identifies patch releases such as `26.7.1`.

## Authoring workflow

1. Write and review the release in Markdown using [TEMPLATE.md](TEMPLATE.md).
2. Create the matching HTML file from [TEMPLATE.html](TEMPLATE.html).
3. Keep the title, introductory summary, feature descriptions, version numbers, and links synchronized between the Markdown and HTML files.
4. Replace every `[[PLACEHOLDER]]` in the generated HTML. The square-bracket form is intentional: `{{ ... }}` is reserved for HubL.
5. Run the local checks before uploading:

   ```bash
   hs cms lint release-notes/<version>-release-notes.html
   git diff --check -- \
     release-notes/<version>-release-notes.md \
     release-notes/<version>-release-notes.html
   ```

The introductory summary should mention the most important Platform and QuiltSync changes. Do not let a major companion-product release appear only in a later section.

## HubSpot template requirements

`TEMPLATE.html` is an HTML + HubL coded email template. Preserve these elements in every generated release template:

- `templateType: email`
- `isAvailableForNewContent: true`
- A dynamic HubSpot email title
- The `hs-inline-css` style block
- The editable `preview_text` module
- The editable `@hubspot/email_body` module
- The optional browser-view link
- Company address fields from `site_settings`
- Subscription-preference and global-unsubscribe links

### Deployment personalization fields

The **Your CloudFormation Template** section must retain these account-specific HubSpot personalization tokens:

| Display field | HubSpot property | Fallback |
| --- | --- | --- |
| Catalog URL | `p24310949_deployments.quilt_stack_url` | `No URL Found` |
| Template URL | `p24310949_deployments.template_variant_url` | `No Template Variant Found` |
| Deployment Style | `p24310949_deployments.cf_tf` | `CF` |
| Network Version | `p24310949_deployments.network_version` | `2` |

Use the full HubL expression, not the fallback as static text. For example:

```html
{{ personalization_token('p24310949_deployments.quilt_stack_url', 'No URL Found') }}
```

These tokens were recovered from the live 1.71 marketing email. They are not ordinary contact properties and must not be replaced with generic `[[PLACEHOLDER]]` values or sanitized fallbacks.

Keep these expressions at template scope. Do not place them inside the `@hubspot/email_body` rich-text module or a `module_attribute "html"` block: nested HubL is treated as rich-text content and recipients will see the literal `{{ personalization_token(...) }}` expression instead of the resolved value.

Passing `hs cms lint` only proves that the file is valid HubL. It does **not** create a marketing email or prove that all campaign metadata is present.

## Upload the coded template

The HubSpot CLI is configured with the `quilt-data` account alias for account `24310949`.

Upload to draft first, then publish after HubSpot accepts it:

```bash
hs cms upload \
  --account=quilt-data \
  --cms-publish-mode=draft \
  release-notes/<version>-release-notes.html \
  release-notes/<version>-release-notes.html

hs cms upload \
  --account=quilt-data \
  --cms-publish-mode=publish \
  release-notes/<version>-release-notes.html \
  release-notes/<version>-release-notes.html
```

Confirm the remote asset exists:

```bash
hs cms ls --account=quilt-data release-notes
```

The uploaded file is a Design Manager asset. It appears under:

```text
https://app.hubspot.com/design-manager/24310949
```

It will **not** appear in the Marketing Email list until a marketing-email record is created from it.

## Create the marketing email

### Recommended: clone the previous release

Clone the previous release email when the new email should inherit detailed metadata such as sender settings, subscription type, campaign, access, graymail behavior, and email mode. HubSpot provides a dedicated clone endpoint:

```bash
POST /marketing/emails/2026-03/clone
```

Request body:

```json
{
  "id": "<previous-email-id>",
  "cloneName": "Variant Release Email - <version> <month>, <year>",
  "language": "en"
}
```

After cloning, patch the clone with the new subject, preview text, coded-template path, web-version details, and any metadata that intentionally differs from the previous release.

Cloning does not attach a draft to the previous email's workflow. For a workflow email, configure the clone's sending method as **Through an automation**, complete HubSpot's review, and publish the automated email. Only then can it be selected in a workflow's **Send email** action. Adding or replacing that workflow action is a separate, potentially live change and requires explicit approval.

### Minimal creation

The Marketing Email API can also create a new draft, but the result contains only minimal defaults:

```bash
POST /marketing/emails/2026-03
```

```json
{
  "name": "Quilt Platform Release <version>",
  "subject": "Quilt Platform Release <version>"
}
```

When using this path, set the coded template using the nested update field:

```json
{
  "content": {
    "templatePath": "release-notes/<version>-release-notes.html"
  }
}
```

Do not rely on `templatePath` at the top level of the create request. HubSpot may silently create the draft with `@hubspot/email/dnd/plain_text.html` instead. Always fetch the resulting record and verify `content.templatePath`.

## Required marketing-email metadata

Use the previous release as the source of truth, then confirm every value. Current Quilt defaults include:

| Field | Expected value |
| --- | --- |
| From name | `Quilt Support` |
| From/reply-to address | `support@quilt.bio` |
| Subscription | `Quilt Stack Updates` |
| Subscription ID | `220905832` |
| Office location ID | `108352087860` |
| Web-version domain | `www.quilt.bio` |
| Language | `en` |

Also set and verify:

- Internal email name
- Personalized subject line, when required
- Persisted preview text, not only the template's default preview text
- Campaign ID for the current release
- Low-engagement/graymail suppression behavior
- Browser-version slug and meta description
- Email type: regular/batch or automated
- Recipient lists for regular emails, or the **Through an automation** sending method for automated-email drafts
- User and team access restrictions

Campaigns change over time. Do not blindly reuse the previous campaign ID simply because it exists on the prior email.

### Preview text

For coded templates, persist preview text in the email record as well as supplying a template default:

```json
{
  "content": {
    "widgets": {
      "preview_text": {
        "body": {
          "value": "<preview text>"
        }
      }
    }
  }
}
```

### Lifecycle fields

The following details cannot be prefilled as ordinary metadata:

- Published status
- Publishing user and publication date
- Workflow history
- Delivery, open, click, and reply statistics

These fields appear only after the corresponding HubSpot lifecycle action. Do not publish, attach a workflow, select recipients, or send merely to make the details panel look complete.

## Verify before handoff

Fetch the created email and confirm at least:

- `state` is still a draft
- `content.templatePath` is the intended release template
- Subject and preview text are correct
- Sender and reply-to are populated
- Subscription and office location are populated
- Campaign is appropriate for this release
- Web version is configured as intended
- Graymail behavior matches the release-email policy
- Regular-email recipient lists are intentionally configured, or an automated-email draft is ready to be reviewed and published before workflow selection

Marketing emails are listed at:

```text
https://app.hubspot.com/email/24310949/manage/state/all
```

An email editor URL has the form:

```text
https://app.hubspot.com/email/24310949/edit/<email-id>
```

## Credentials and safety

The repository `.env` may define `HUBSPOT_ACCESS_TOKEN`. The token needs the following scopes for the workflow above:

- `content`
- `marketing.email.read`
- `marketing.email.write`

Important rules:

- Never print, log, paste, or commit access-token values.
- Never run `set -x` while a token is loaded.
- Do not inspect `.env` by printing entire lines. Extract variable names with a parser that understands optional `export` prefixes.
- Load the token only for the command that needs it.
- Filter API responses to the non-sensitive fields required for verification.
- Rotate a credential immediately if it appears in terminal or tool output.
- Creating or updating a draft is not authorization to publish, attach live automation, choose recipients, or send.

The CLI credential in `~/.hscli/config.yml` and the token in `.env` may have different scopes. A successful Design Manager upload does not prove that the same credential can create or update marketing emails.
