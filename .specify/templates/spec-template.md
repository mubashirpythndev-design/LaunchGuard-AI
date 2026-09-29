# Feature Specification: [FEATURE NAME]

**Feature Branch**: `[###-feature-name]`  
**Created**: [DATE]  
**Status**: Draft  
**Input**: User description: "$ARGUMENTS"

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.
  
  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

<!--
  CONSTITUTION 2.IV — Honest Uncertainty: acceptance scenarios that describe what the system
  "sees" or "detects" MUST be written in hedged language ("appears", "possible") and MUST NOT
  assert certainty or certification that the CV pipeline does not produce. The disclaimer
  "Decision-support tool. Not a replacement for certified range safety." MUST be an explicit
  acceptance condition on every story that surfaces a verdict.
-->

### User Story 1 - [Brief Title] (Priority: P1)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently - e.g., "Can be fully tested by [specific action] and delivers [specific value]"]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]
2. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

### User Story 2 - [Brief Title] (Priority: P2)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

### User Story 3 - [Brief Title] (Priority: P3)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

[Add more user stories as needed, each with an assigned priority]

### Edge Cases

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right edge cases.
-->

- What happens when [boundary condition]?
- How does system handle [error scenario]?

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

- **FR-001**: System MUST [specific capability, e.g., "allow users to create accounts"]
- **FR-002**: System MUST [specific capability, e.g., "validate email addresses"]  
- **FR-003**: Users MUST be able to [key interaction, e.g., "reset their password"]
- **FR-004**: System MUST [data requirement, e.g., "persist user preferences"]
- **FR-005**: System MUST [behavior, e.g., "log all security events"]

*Example of marking unclear requirements:*

- **FR-006**: System MUST authenticate users via [NEEDS CLARIFICATION: auth method not specified - email/password, SSO, OAuth?]
- **FR-007**: System MUST retain user data for [NEEDS CLARIFICATION: retention period not specified]

### Constitution Alignment *(mandatory)*

<!--
  Every spec MUST answer these. They are derived from `.specify/memory/constitution.md` and a spec
  that leaves them blank is incomplete. Reference the governing principle in brackets, e.g.
  (Constitution 2.II). The term "bracket" is avoided in the answers themselves — cite principles
  as "(Constitution 2.II)".
-->

- **Verdict source**: Which requirements produce a GO / HOLD / NO-GO verdict, and how is the
  rule engine separated from the LLM explanation path? (Constitution 2.I)
- **Failure behaviour**: What severity is emitted when a module errors, times out, or returns
  low confidence — and which checklist inputs are mandatory such that their absence forces HOLD?
  (Constitution 2.II)
- **Finding fields**: Which findings carry annotation overlays, and which carry only metrics?
  (Constitution 2.III)
- **Uncertainty wording**: What user-facing copy in this feature uses hedged language, and where
  is the disclaimer rendered? (Constitution 2.IV)
- **Measurement provenance**: How does every number shown in this feature trace back to a CV tool
  result rather than to the agent? (Constitution 2.V)
- **Contract impact**: Does this feature change the OpenAPI document, and therefore require
  regenerating `packages/contract`? (Constitution 3.I)
- **Scope check**: Does this feature stay within the 3 modes and 3 demo scenarios? List any
  thermal, drone, telemetry, or digital-twin work as explicitly deferred. (Constitution 6.I–6.II)

### Key Entities *(include if feature involves data)*

- **[Entity 1]**: [What it represents, key attributes without implementation]
- **[Entity 2]**: [What it represents, relationships to other entities]

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: [Measurable metric, e.g., "Users can complete account creation in under 2 minutes"]
- **SC-002**: [Measurable metric, e.g., "System handles 1000 concurrent users without degradation"]
- **SC-003**: [User satisfaction metric, e.g., "90% of users successfully complete primary task on first attempt"]
- **SC-004**: [Business metric, e.g., "Reduce support tickets related to [X] by 50%"]

### Safety & Honesty Outcomes *(mandatory for safety-critical features)*

- **SH-001**: [Verdict correctness, e.g., "All 3 demo scenarios reproduce the expected GO / HOLD / NO-GO verdict from the fixture images"]
- **SH-002**: [Fail-safe coverage, e.g., "Every CV module returns severity warning, never ok, when it errors or times out"]
- **SH-003**: [Explainability, e.g., "100% of findings render module, check id, severity, message, confidence, and metrics"]
- **SH-004**: [Uncertainty, e.g., "No user-facing string asserts certification, and the disclaimer is present on every verdict surface"]
- **SH-005**: [Test obligations met, e.g., "Every CV module has a passing and a failing fixture test, and each demo scenario has a Playwright spec"]
