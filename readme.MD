# TL;DR AWS ACCOUNT HARDENING

## Table of contents

1. [Initial settings to harden your account security](#initial)
2. [Additional measures that will be helpful](#additional)
3. [What to do if your account has been compromised](#compromised)
4. [Periodically](#periodically)


## Initial settings to harden your account security<a name="initial"></a>:

- Enable multi-factor authentication (MFA) on the root user (https://docs.aws.amazon.com/IAM/latest/UserGuide/id_root-user.html#id_root-user_manage_mfa) and any IAM users (https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_mfa.html) with console access. Enabling MFA can help you to secure the accounts and prevent unauthorized users from logging in to accounts without a security token.

- Delete all programmatic IAM keys from the root account, you shouldn’t use those, at all. If somehow those access keys are leaked in the future, they have unrestricted access to do anything: https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html#lock-away-credentials

- The root account only needs to be used for very specific account tasks, for every other action we recommend that you use an IAM user with appropriate permissions to perform tasks and access AWS resources. Only use the root account when you need to do some of these tasks:
https://docs.aws.amazon.com/IAM/latest/UserGuide/root-user-tasks.html

- Enable AWS CloudTrail logging services: https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-create-and-update-a-trail.html - Create a new trail, only for writes, and enable trail insights. This will generate a mere 50 cents monthly cost, but it will help detecting and preventing security incidents.
<p align="center">
<img src="https://github.com/sercasti/aws-hardening/raw/main/images/cloudtrail.png" width=70% height=70%>
</p>

- Activate AWS Cost Anomaly Detection (it's free): https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/getting-started-ad.html#create-ad-alerts
<p align="center">
<img src="https://github.com/sercasti/aws-hardening/raw/main/images/costAnomaly.png" width=80% height=80%>
</p>

- Don't share IAM credentials among several people, create individual IAM users for each person on your team (it's free): https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html#create-iam-users

- Use the "Least Privileged Principle" for your IAM Roles, grant least privilege for each user/role: https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html#grant-least-privilege

- Set a password policy for IAM users: https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_passwords_account-policy.html

- Setup Alternate contacts on your account preferences: https://console.aws.amazon.com/billing/home?#/account

Additional info: https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html

---

## Additional measures that will be helpful<a name="additional"></a>:

- Create a CloudWatch billing alarm to avoid runaways: https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/monitor_estimated_charges_with_cloudwatch.html

- Enable GuardDuty (https://aws.amazon.com/guardduty/), it will not only help on the reactive side of incidents, but it will also prevent them. GuardDuty will alert you when there are unsafe settings, attack surfaces or known vulnerabilities on your AWS resources or instances. This service has a 30 days free trial that you can use to validate your accounts.

- Group workloads based on business purpose and ownership using different AWS accounts (they are free), by separating your workloads on different accounts you reduce blast radius, force logical isolation of your resources, avoid dependencies and conflicts, constrain access to sensitive data, and limit scope of impact. Think of it as a logical grouping, whatever fits your scenario best, for example, by environment (dev, prod, test), or by application.  
This will also help with service quotas and cost management.   
https://docs.aws.amazon.com/whitepapers/latest/organizing-your-aws-environment/benefits-of-using-multiple-aws-accounts.html  
You can set up an AWS organization (it's free) to centralize billing on a payer account, and create SCPs (secure control policies) to restrict things that you know for sure should never happen on any of those accounts, for example, regions that should never be used, or instance types that should never be run. 
<p align="center"><img src="https://github.com/sercasti/aws-hardening/raw/main/images/createOrg.png" width=30% height=30%></p>
<p align="center"><img src="https://github.com/sercasti/aws-hardening/raw/main/images/scpscreated.png" width=60% height=60%></p>
Don't forget to apply the policy to the account after creating it. https://aws.amazon.com/blogs/security/how-to-use-service-control-policies-to-set-permission-guardrails-across-accounts-in-your-aws-organization/

You will find some SCP examples on the /scps folder in this repository, and you can find more here: https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps_examples.html

Recommended SCP's to reduce risk surface: 
- Disable Regions your business should never use (https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps_examples_general.html#example-scp-deny-region)
- Disable instance types your business should never use (https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps_examples_ec2.html)
- Disable the root user of the member accounts of your organization (https://asecure.cloud/a/scp_root_account/)

---

## What to do if your account has been compromised<a name="compromised"></a>:

Step 1: Sign in as the AWS account root user (https://docs.aws.amazon.com/IAM/latest/UserGuide/id_root-user.html) (not your IAM user). Delete the exposed AWS Access Key: https://aws.amazon.com/premiumsupport/knowledge-center/delete-access-key/ and delete any Root account programmatic Access keys that could have been created during the breach.

Step 2: Inside IAM on your console, you'll find a menu item called "**Credential report**", download the credentials report, and use it to rotate (https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_access-keys.html#Using_RotateAccessKey) and delete (https://aws.amazon.com/premiumsupport/knowledge-center/delete-access-key/) all root and AWS Identity and Access Management (IAM) access keys. To secure your account please delete any unauthorized IAM users, roles, and policies, and revoke any temporary credentials, delete any potentially unauthorized IAM users, and then change the password (https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_passwords_admin-change-user.html) for all other IAM users. 

Step 3: Verify that your account information and alternate contacts is correct on account preferences: https://console.aws.amazon.com/billing/home?#/account

Step 4: Check your CloudTrail log for unsanctioned activity such as creation of unauthorized IAM users, policies, roles or temporary security credentials. Use the search capabilities to track down what was done with the compromised credentials, and revert each action one by one. If these credentials were used to create new users or credentials, you need to repeat that analysis for each one, to undo everything that has been done during the incident. Even if you didn't have any trails created for your account, "Event history" shows you the last 90 days of management events (and those cannot be deleted). Try to track down the very beginning of the incident, find the first API call to unrecognized "ConsoleLogin" operations, or "CreateAccount" event names, or any kind of activity that's suspicious, try different filters (Event name, AWS access key, resource type, user name) to find where it all started, and then track it down from there, to follow any ramifications of the incident. Notice that cloudtrail entries include IP address and User Agent, that can help when trying to relate different API calls.

Step 5: Review your AWS account for any unauthorized AWS usage, such as unauthorized EC2 instances, Lambda functions or EC2 Spot bids. To check usage, please log into your AWS Management Console and review each service page. Delete any resources on your account that you didn't create, such as Amazon Elastic Compute Cloud (Amazon EC2) instances and AMIs (https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/terminating-instances.html), Amazon Elastic Block Store (Amazon EBS) volumes (https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ebs-deleting-volume.html) and snapshots (https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ebs-deleting-snapshot.html), and IAM users (https://docs.aws.amazon.com/IAM/latest/UserGuide/id_users_manage.html#id_users_deleting).

Step 6: Check all public buckets for leaked credentials or outdated libraries that could be exposing environment variables

Step 7: Check all code repositories to make sure IAM credentials were not pushed to them.

Step 8: Respond to the notifications that you received from AWS Support through the AWS Support Center (https://console.aws.amazon.com/support/). If you can't sign in, use the Contact Form: https://pages.awscloud.com/contact-us-account-support.html If you have any questions or concerns, create a new AWS Support case in the AWS Support Center: https://console.aws.amazon.com/support/

Step 9: Check your bill (https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/invoice.html). Your bill can help you identify resources that you didn't create.

Step 10: Use IAM Access analyzer (https://docs.aws.amazon.com/IAM/latest/UserGuide/what-is-access-analyzer.html) to check for any remaining resources created by the attacker that could be used as backdoors. This is a free service, and it will detect any resource shares outside the account (https://console.aws.amazon.com/access-analyzer/)

Step 11: Review the recommendations at the beginning of this document, to harden your account security

Additional info: 
https://aws.amazon.com/es/premiumsupport/knowledge-center/potential-account-compromise/

---

## Periodically<a name="periodically"></a>:

- Check Trusted advisor, it is a free service that will cover some data points on your accounts and raise red flags on security issues

- Remember to deactivate AWS credentials for people who are leaving the company, before they do.

- Use roles for applications that run on Amazon EC2 instances, instead of access keys: https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_switch-role-ec2.html

- Rotate credentials regularly: https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_access-keys.html#Using_RotateAccessKey

- Remove unnecessary credentials: https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_finding-unused.html

These recommendations are derived from the first phase of the security maturity model from AWS, as they are quick wins to safely start your cloud journey. If you wish to go deeper into this model, fee free to visit https://maturitymodel.security.aws.dev/

If you want to go all in, and run a tool to evaluate your security on aws, try Prowler.
Prowler is a security tool to perform AWS security best practices assessments, audits, incident response, continuous monitoring, hardening and forensics readiness. https://github.com/toniblyx/prowler
