# Features

Feature-specific documentation, implementation guides, and troubleshooting.

**Tags:** #features #implementation #troubleshooting

## Feature Catalog

### Admin Dashboard
- **[[ADMIN_DASHBOARD]]** - Admin panel features, user management, and analytics
- Related: [[ADMIN_TROUBLESHOOTING]] for issues

### Training Examples & Case Studies

(Legacy industry examples archived in [[Cleanup/archived|../Cleanup/archived/index.md]])

Note: SalesTrainer Pro uses the universal C.O.R.E. Selling System (Connect, Observe, Recommend, Execute) and is domain-agnostic. See [[PRODUCT_REQUIREMENTS|../Architecture & Design/PRODUCT_REQUIREMENTS.md]] for current framework.

### Troubleshooting
- **[[ADMIN_TROUBLESHOOTING]]** - Common issues, debugging, and solutions
  - WebSocket connection failures
  - Auth/token problems
  - Quota and rate limiting
  - Session timeout handling

## Feature Development Checklist

When adding a new feature:

1. **Update [[PRODUCT_REQUIREMENTS|../Architecture%20&%20Design/PRODUCT_REQUIREMENTS.md]]** - Add to product spec
2. **Update [[AGENT_FLOW|../Architecture%20&%20Design/AGENT_FLOW.md]]** if affects conversation logic
3. **Update [[DATABASE_SCHEMA|../Architecture%20&%20Design/DATABASE_SCHEMA.md]]** if new data model
4. **Update [[API_SPECIFICATION|../API%20Documentation/API_SPECIFICATION.md]]** if new endpoints
5. **Add feature doc here** - Link from [[Features/index.md]]

## Related Sections

- **[[AGENT_FLOW|../Architecture%20&%20Design/AGENT_FLOW.md]]** - How agents interact
- **[[API_SPECIFICATION|../API%20Documentation/API_SPECIFICATION.md]]** - Endpoint contracts
- **[[DATABASE_SCHEMA|../Architecture%20&%20Design/DATABASE_SCHEMA.md]]** - Data models

---

**Found a bug?** Check [[ADMIN_TROUBLESHOOTING]] first, then file an issue.

---

**Last updated:** 2026-07-13
