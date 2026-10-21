# Security reports

This helper displays a question and returns a status. It does not perform the
destructive action, authenticate the user, or provide a security boundary.
Callers remain responsible for authorization, argument handling, and acting
only after a successful confirmation. Never run an action after a failed prompt.

For sensitive vulnerabilities, use
[GitHub's private reporting form](https://github.com/kris004/destructive-confirm/security/advisories/new).
If that is unavailable, request a private reporting channel
without posting exploit details or secrets in a public issue. Do not include
private paths, credentials, or real destructive targets in reproductions.

Fixes are developed on the default branch and the latest published release.
There are no promised long-term-support or older-release branches.
