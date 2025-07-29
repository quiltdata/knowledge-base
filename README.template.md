# Troubleshooting KBase Article Template

## Title

**Format:** Question or problem statement (mirror what user would type)  
**Examples:**  
- "Why is SSO login timing out in AWS ECS?"  
- "Data previews not rendering in Quilt"

## Tags

**Examples:**  
- `sso`, `aws`, `ecs`, `preview`, `mime`, `access`, `quilt`

## Summary

Brief description of problem and solution for use by search engines.

---

## Symptoms

- Restate the problem in more precise language, e.g. "The Quilt Catalog consistently fails to render previews for certain file types."

**Observable indicators:**  
- UI failures, error messages, degraded performance  
- Affected pages, products, data types, buckets, or roles  

**Example:**  
- Catalog fails to render `.txt` and `.png` files  
- Login hangs >30s via SSO in AWS ECS


## Likely Causes

**Concise explanation or hypotheses:**  
- Misconfiguration  
- System limitation  
- External dependency (e.g., AWS policy, MIME type handling)

## Recommendation

1. Explicit fixes or workarounds (if known)
2. Debugging steps to take
3. Logs or other inputs to collect and submit

**Example:**  
1. Add correct file extensions to uploaded files  
2. Use `t4.Package.set_meta()` to manually specify MIME types  
