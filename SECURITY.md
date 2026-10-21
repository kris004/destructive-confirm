# Security reports

This helper displays a question and returns a status. It does not perform the
destructive action, authenticate the user, or provide a security boundary.
Callers remain responsible for authorization, argument handling, and acting
only after a successful confirmation. Never run an action after a failed prompt.

For sensitive vulnerabilities, use the hosting platform's private vulnerability
reporting feature if enabled. Otherwise, request a private reporting channel
without posting exploit details or secrets in a public issue. Do not include
private paths, credentials, or real destructive targets in reproductions.

Fixes are developed on the default branch. There are currently no versioned
releases or promised long-term-support branches.
