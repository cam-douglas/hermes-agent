## Handover v4 Implementation Overview

### Summary
This document summarizes the implementation and changes made in the Handover v4 for the Hermes Agent.

### Existing Features Before Implementation
1. Basic model routing through OpenRouter.
2. Initial spend governance configurations.
3. Basic profile management.

### New Features Implemented
1. Adaptive routing:
   - Configuration for enabling/disabling adaptive routing.
   - New routing model feature with fallback for emergency scenarios.
2. Spend governance:
   - Added caps tracking for individual turns and overall sessions with persistence in SQLite.
3. Profile routing:
   - Support for ephemeral profiles and garbage collection of expired profiles.
4. Organizational escalation:
   - New gating features to require approval for consultant model invocation and event callbacks for escalated statuses.
5. Added stripping of `MEDIA:` tags in CLI output.