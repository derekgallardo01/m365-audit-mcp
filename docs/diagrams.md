# Diagrams

Beyond the inline ones in [architecture.md](architecture.md).

## 1. Class-ish model — data shapes the tools work with

```mermaid
classDiagram
    class TenantConfig {
      +str id
      +str displayName
      +str defaultDomain
      +dict dataLocation
    }
    class PrivacyConfigItem {
      +bool verified
      +str evidence
      +str reason
      +str action_required
    }
    class Document {
      +str id
      +str name
      +str siteUrl
      +str owner
      +str lastModified
      +str lastAccessed
      +str sensitivityLabel
    }
    class CAPolicy {
      +str id
      +str displayName
      +str state
      +dict conditions
      +list grantControls
    }
    class DLPPolicy {
      +str id
      +str displayName
      +str state
      +list locations
      +list sensitiveTypes
    }
    class CopilotUsage {
      +str displayName
      +int activeUsers
      +int totalUsers
      +int promptsLast30Days
      +list topPrompts
    }
    class Backend {
      +TenantConfig TENANT
      +dict PRIVACY_CONFIG
      +list DOCUMENTS
      +list CONDITIONAL_ACCESS_POLICIES
      +list DLP_POLICIES
      +dict COPILOT_USAGE
      +days_since(iso_ts) int
    }

    Backend --> TenantConfig
    Backend --> PrivacyConfigItem
    Backend --> Document
    Backend --> CAPolicy
    Backend --> DLPPolicy
    Backend --> CopilotUsage
```

Both `mock_data` and a real Microsoft Graph backend must expose the same
interface — the audit functions read these attributes by name.

## 2. Sequence — multi-tool conversation in Claude Desktop

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant C as Claude
    participant S as m365-audit-mcp

    U->>C: "Show me where Copilot rollout is stalling, then for the<br/>worst team, summarize their top prompts."
    C->>S: summarize_copilot_usage()
    S-->>C: {by_team: [...sorted by adoption asc...]}
    C->>C: parses - lowest adoption is "team-clinical"
    C->>S: summarize_copilot_usage(team_id="team-clinical")
    S-->>C: {team_id: "team-clinical", topPrompts: [...]}
    C-->>U: "Clinical Operations is at 26.7% adoption (12 of 45<br/>licensed users). Their top prompts are about patient intake<br/>forms and follow-up emails - which fits the workflow but<br/>suggests the broader team hasn't been onboarded."
```

The orchestration is the LLM's; the server stays stateless.

## 3. Sequence — privacy audit produces a sign-off doc

```mermaid
sequenceDiagram
    autonumber
    participant U as Compliance owner
    participant C as Claude
    participant S as m365-audit-mcp

    U->>C: "Walk our M365 privacy posture. Format as a sign-off doc."
    C->>S: check_tenant_privacy_config()
    S-->>C: {tenant, summary, items}
    C->>C: items_outstanding > 0 -> need to flag follow-up
    C-->>U: """## Privacy posture - Acme Manufacturing (2026-06-28)<br/>**3 of 4 items verified.**<br/><br/>### Verified<br/>- Data residency (US, evidence: 2026-06-20)<br/>- Copilot no public-model training (DPA + Learn 2026-06-20)<br/>- BAA in scope (signed 2024-03, renewed 2026-03)<br/><br/>### Outstanding<br/>- Azure OpenAI no-retention NOT YET requested -<br/>  **action:** submit request via Microsoft account team."""
```

## 4. Decision tree — which tool does Claude pick

```mermaid
flowchart TB
    Q["User question"] --> P{"About privacy /<br/>compliance config?"}
    P -- "yes" --> T1["check_tenant_privacy_config"]
    P -- "no" --> D{"About documents?"}
    D -- "yes" --> T2["find_orphaned_documents"]
    D -- "no" --> CA{"About access control?"}
    CA -- "yes" --> T3["audit_conditional_access_policies"]
    CA -- "no" --> DLP{"About DLP / sensitivity?"}
    DLP -- "yes" --> T4["list_dlp_policies"]
    DLP -- "no" --> CU{"About Copilot usage?"}
    CU -- "yes" --> T5["summarize_copilot_usage"]
    CU -- "no" --> NA["No matching tool -<br/>Claude answers from prior context only"]
```

The LLM does this routing implicitly from tool docstrings. Good docstrings
beat any "select_tool" router function for an MCP server with this few tools.

## 5. State — backend swap (mock → Graph)

```mermaid
stateDiagram-v2
    [*] --> Mocked: pip install -e .
    Mocked --> DevelopingGraph: write GraphBackend class
    DevelopingGraph --> DevelopingGraph: implement the<br/>attributes one by one
    DevelopingGraph --> SwappedBackend: BACKEND = GraphBackend()<br/>in audit_tools.py
    SwappedBackend --> Production: deploy with Entra app reg<br/>+ minimum scopes
    Production --> CachingPattern: add cache layer<br/>(Graph quotas are real)
    CachingPattern --> Production: 5-15 min TTL per tool
```

The state diagram makes the production-readiness checklist concrete: the
swap is one edit; the caching layer is the work that follows.
