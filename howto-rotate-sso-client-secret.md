# Why do SSO sign-ins still fail after I update the SSO client secret?

## Tags

`sso`, `azure`, `entra`, `okta`, `onelogin`, `google`, `cloudformation`, `terraform`, `ecs`, `registry`

## Summary

From Quilt 26.9.6, the stack keeps SSO client secrets in AWS Secrets Manager, and the registry reads them when its ECS tasks start. A stack update that changes only the client secret parameter updates the secret but does not restart the running tasks, so they keep the old value. After rotating an SSO client secret, force a new deployment of the registry service.

---

## Symptoms

- You rotated the client secret of the catalog's app registration in your identity provider (Microsoft Entra ID, Okta, OneLogin or Google) and updated the stack's client secret parameter.
- The stack update completed, but SSO sign-ins fail once the old secret expires or is deleted at the identity provider.
- Users who were already signed in are affected too, once their identity provider access token expires: their session ends, and signing in again fails.

## Root Cause

On stacks running Quilt 26.9.6 or later, each SSO client secret parameter (`AzureClientSecret`, `GoogleClientSecret`, `OktaClientSecret`, `OneLoginClientSecret` or `SingleSignOnClientSecret`) seeds a Secrets Manager secret, and the registry's ECS task definition references that secret instead of holding the value itself. ECS reads a secret only when a task starts and does not pick up later changes ([AWS documentation](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/secrets-envvar-secrets-manager.html)).

A stack update that changes only the secret's parameter leaves the task definition unchanged, so ECS does not replace the running registry tasks. Forcing a new deployment when the tasks have already restarted is harmless, so do it after any change to the client secret.

## Recommendation

If sign-ins already fail, force the redeploy (step 3) now.

Rotate the secret with both values valid at the identity provider for a while, so sign-in keeps working until the registry has restarted:

1. If your identity provider can hold two client secrets at once, create the new one alongside the old one; if it replaces the secret immediately, do steps 2 and 3 right away: sign-ins fail until the deployment has finished.
2. Update the stack's client secret parameter with the new value: in CloudFormation, or, for a stack deployed with Terraform, in the module's `parameters` followed by `terraform apply`, and wait until the stack update has completed.
3. Force a new deployment of the registry service, as below.
4. Wait until the deployment has finished, as below, then confirm that SSO sign-in works and delete the old secret at the identity provider.

### AWS Console

1. Open the Amazon ECS console in the stack's region.
2. Open the cluster named after the stack.
3. Select the service `<stack-name>-registry` and choose **Update**.
4. Select **Force new deployment** and choose **Update**.
5. On the service's **Deployments** tab, wait until the new deployment is completed and no tasks of the previous one remain.

### AWS CLI

```bash
aws ecs update-service \
  --cluster <stack-name> \
  --service <stack-name>-registry \
  --force-new-deployment \
  --region <region>
```

```bash
aws ecs wait services-stable \
  --cluster <stack-name> \
  --services <stack-name>-registry \
  --region <region>
```

The wait also returns without an error if the deployment fails and ECS rolls the registry back to its previous tasks, which keep the old secret. Before deleting the old secret, check on the service's **Deployments** tab in the ECS console that the new deployment completed and was not rolled back.

If it was rolled back, keep the old secret, find the cause in the service's events, and force the deployment again once it is fixed.

If the wait times out, run it again.

ECS replaces the registry tasks with a rolling deployment; the new tasks read the current secret.
