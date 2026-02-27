# Google Ads Analyzer for Claude Code

A Claude Code skill + MCP server setup for expert-level Google Ads campaign analysis. Includes GAQL query templates, Quality Score diagnostics, Smart Bidding evaluation, Performance Max deep dives, and 12 reference documents.

## What It Does

When installed, Claude Code can:

- Query your Google Ads accounts directly using GAQL (Google Ads Query Language)
- Analyze campaign, ad group, keyword, and search term performance
- Diagnose Quality Score issues at the component level (expected CTR, ad relevance, landing page)
- Evaluate Impression Share to identify budget vs rank opportunities
- Assess Smart Bidding performance and learning status
- Deep dive Performance Max campaigns (asset groups, ad strength, cannibalization)
- Review search term reports and identify negative keyword gaps
- Generate structured analysis reports with prioritized recommendations

## Components

| Component | What it does |
|---|---|
| **Skill** (`skill/`) | Analysis framework with 12 reference docs that Claude loads as context |
| **MCP Server** | Google's official [`google-ads-mcp`](https://github.com/googleads/google-ads-mcp) — connects Claude Code to the Google Ads API |
| **Scripts** (`scripts/`) | OAuth setup helper |

## Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed
- [Python](https://www.python.org/) 3.8+
- [uv](https://docs.astral.sh/uv/) (Python package manager — the MCP server runs via `uvx`)
- A Google Ads account (with a Developer Token)
- A Google Cloud project with the Google Ads API enabled

## Installation

### Step 1: Install the Skill

Copy the `skill/` folder into your Claude Code project:

```bash
# From your Claude Code project root
mkdir -p .claude/skills/google-ads-analyzer
cp -r skill/* .claude/skills/google-ads-analyzer/
```

The skill is now active. Claude will automatically use it when you ask about Google Ads analysis.

### Step 2: Set Up a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or use an existing one)
3. Enable the **Google Ads API**:
   - Go to APIs & Services → Library
   - Search for "Google Ads API"
   - Click Enable
4. Create an **OAuth 2.0 Client ID**:
   - Go to APIs & Services → Credentials
   - Click "Create Credentials" → OAuth Client ID
   - Application type: **Desktop app**
   - Download the JSON file

### Step 3: Get a Developer Token

This is required to access the Google Ads API. It's separate from OAuth credentials.

1. Sign in to your Google Ads **manager account** (MCC)
2. Go to Tools & Settings → Setup → API Center
3. Your Developer Token is shown there
4. If you don't have one, apply for access (test accounts get instant approval)

**Token access levels:**
- **Test Account:** Instant approval, only works with test ad accounts
- **Basic Access:** Requires application review, works with real accounts
- **Standard Access:** Higher rate limits, requires additional review

For most use cases, Basic Access is sufficient. The review process takes a few business days.

### Step 4: Run the Setup Script

```bash
cd scripts/

# Place your downloaded OAuth client JSON in this folder
# (or point to it when prompted)

python3 setup.py
```

The script will:
1. Ask for your OAuth client JSON path
2. Ask for your Developer Token
3. Ask for your Login Customer ID (MCC ID, optional)
4. Open a browser for Google OAuth authorization
5. Generate `credentials.json` and `.env.google-ads`
6. Configure `.mcp.json` for Claude Code
7. Test the connection

### Step 5: Verify

Restart Claude Code, then ask:

> "List my Google Ads accounts"

Claude should connect to your account and show available accounts.

## Usage Examples

Once installed, you can ask Claude things like:

- "Analyze my Google Ads campaigns from the last 30 days"
- "What's my Quality Score distribution across keywords?"
- "Show me Impression Share breakdown — am I losing to budget or rank?"
- "Review my search terms and suggest negative keywords"
- "Is my Smart Bidding strategy performing within target?"
- "Deep dive into my Performance Max campaign"
- "Compare this month vs last month across all campaigns"
- "Which campaigns have the highest wasted spend?"

You can also share screenshots or exported data from the Google Ads UI — the skill works with any data format.

## What's in the Reference Docs

| Document | Covers |
|---|---|
| `core_concepts.md` | Ad Rank, Quality Score, Smart Bidding, PMax, GAQL overview |
| `gaql_queries.md` | Ready-to-use GAQL queries for each analysis step |
| `quality_score.md` | 3 components, diagnosis by component, prioritization |
| `impression_share.md` | IS lost by budget vs rank, auction insights |
| `smart_bidding.md` | tCPA, tROAS, learning period, when to intervene |
| `performance_max.md` | Asset groups, signals, feed quality, cannibalization |
| `conversion_tracking.md` | Types, DDA, conversion lag, primary vs secondary |
| `account_structure.md` | MCC hierarchy, naming, brand vs non-brand |
| `search_terms_negatives.md` | Search term report, match types, negative keywords |
| `ad_copy_rsa.md` | RSA headlines, descriptions, ad strength, asset labels |
| `segmentation.md` | GAQL segments: device, geo, day_of_week, audiences |
| `performance_fluctuations.md` | Normal vs concerning changes, conversion lag trap |

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `UNAUTHENTICATED` | Refresh token revoked or expired | Run `python3 scripts/setup.py` again |
| `PERMISSION_DENIED` | Developer token not approved or wrong account | Check token status in API Center; verify Login Customer ID |
| `DEVELOPER_TOKEN_NOT_APPROVED` | Token still in test mode | Apply for Basic Access in API Center |
| `INVALID_CUSTOMER_ID` | Wrong customer ID format | Use 10-digit ID without dashes |
| MCP not connecting | Config or credentials issue | Verify `.mcp.json` paths are correct; restart Claude Code |
| No data returned | Wrong date range or no active campaigns | Check `campaign.status = 'ENABLED'`; adjust date range |

## License

MIT
