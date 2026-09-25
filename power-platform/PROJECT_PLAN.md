# MCPD Sentinel Power Platform — Project Plan

## Master tracker

https://github.com/robertrichards45/MCPD/issues/62

## Repository

- Repository: `robertrichards45/MCPD`
- Working branch: `power-platform-rebuild`
- Project root: `power-platform/`

## Project objective

Deliver a production-ready Microsoft Power Platform implementation of the full original MCPD Portal plus original MCPD Sentinel features and the complete digital FTO program, using the approved dark-blue Sentinel interface.

## Phase plan

| Phase | GitHub Issue | Primary outcome |
|---|---|---|
| 1 | #54 | Complete normalized Dataverse data model |
| 2 | #55 | Complete identity/security/role model |
| 3 | #56 | Approved responsive Sentinel app shell |
| 4 | #57 | Reports/forms/law/orders/reference systems |
| 5 | #58 | Training/FTO/DOR/Scenario Lab |
| 6 | #59 | Watch/Assistant Ops/specialized operations |
| 7 | #60 | Analytics/AI/admin/import-export/testing |
| 8 | #61 | Microsoft tenant build and government deployment |

## Working method

1. Keep architecture, specifications, seed data, scripts, and tests in GitHub.
2. Complete as much pre-tenant work as possible before Power Platform access.
3. Use synthetic test records in development.
4. Build tenant-specific items only when a Microsoft environment is available.
5. Export a managed production solution for government import.
6. Treat government deployment as import/reconnect/assign/test rather than rebuild.

## Current phase

**Phase 1 — Normalize architecture and complete Dataverse schema**

The current schema is strongest around Sentinel/FTO/Reports/Watch. Phase 1 expands it across every original module and removes unresolved data-model gaps.

## Definition of project done

The project is complete when:

- all original portal/Sentinel modules are present;
- role-based Dataverse security is validated;
- desktop/mobile interfaces match the approved visual design;
- Digital FTO and Scenario Lab workflows pass acceptance tests;
- Power Automate and Power BI components are working;
- the solution passes source/security/functional validation;
- a managed `MCPDSentinel` solution is exported;
- the government environment can import, reconnect, assign roles, test, and publish without rebuilding the application.
