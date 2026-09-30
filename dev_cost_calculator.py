"""
Development Cost Calculator for Claims Copilot
Generates an Excel file estimating the cost to BUILD the system (production-grade).
Covers team roles, required skills, seniority, phased effort allocation, and rate ranges.

Scope basis: Agentic AI fraud-detection platform
  - Python/FastAPI backend + LangGraph multi-agent orchestration + Bedrock integration
  - React/TypeScript frontend with real-time WebSocket chat
  - Entity graph, vision document analysis, rules/risk engine
  - AWS deployment (ECS/Fargate, RDS, Redis, S3, IaC, CI/CD, monitoring)
"""

import openpyxl
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment

def create_dev_cost_calculator():
    wb = openpyxl.Workbook()

    # ---- Shared styles ----
    header_font = Font(bold=True, size=14, color="FFFFFF")
    header_fill = PatternFill(start_color="2F5496", end_color="2F5496", fill_type="solid")
    sub_fill = PatternFill(start_color="D9E2F3", end_color="D9E2F3", fill_type="solid")
    input_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
    calc_fill = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
    total_fill = PatternFill(start_color="DDEBF7", end_color="DDEBF7", fill_type="solid")
    alt_fill = PatternFill(start_color="E2F0D9", end_color="E2F0D9", fill_type="solid")
    thin = Side(style='thin')
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    money = '"$"#,##0'
    money2 = '"$"#,##0.00'
    pct = '0%'

    # ==================================================================
    # SHEET 1: TEAM & SKILLS
    # ==================================================================
    ws = wb.active
    ws.title = "Team & Skills"
    widths = {'A': 26, 'B': 16, 'C': 14, 'D': 55, 'E': 40}
    for c, w in widths.items():
        ws.column_dimensions[c].width = w

    ws.merge_cells('A1:E1')
    ws['A1'] = "Claims Copilot - Development Team & Required Skills"
    ws['A1'].font = Font(bold=True, size=18, color="2F5496")

    row = 3
    ws.merge_cells(f'A{row}:E{row}')
    ws[f'A{row}'] = "TEAM ROSTER, SENIORITY & SKILLS"
    ws[f'A{row}'].font = header_font
    ws[f'A{row}'].fill = header_fill
    row += 1

    headers = ["Role", "Seniority", "Count", "Key Skills Required", "Why Needed on This Project"]
    for i, h in enumerate(headers):
        col = chr(65 + i)
        ws[f'{col}{row}'] = h
        ws[f'{col}{row}'].font = Font(bold=True)
        ws[f'{col}{row}'].fill = sub_fill
        ws[f'{col}{row}'].border = border
    row += 1

    team = [
        ("Product Owner", "Senior", 1,
         "Insurance/claims domain, backlog mgmt, stakeholder alignment, fraud SME",
         "Owns vision, prioritizes fraud rules & examiner workflows, sign-off authority"),
        ("Project Manager", "Senior", 1,
         "Delivery mgmt, budgeting, risk/RAID, vendor & AWS coordination",
         "Runs schedule/budget, manages Prudential + AWS dependencies"),
        ("Scrum Master", "Mid-Senior", 1,
         "Agile/Scrum facilitation, impediment removal, ceremony management",
         "Keeps multi-discipline team in cadence; can be shared/part-time"),
        ("Tech Architect", "Principal", 1,
         "AWS solution architecture, GenAI/LLM patterns, LangGraph, security/HIPAA, system design",
         "Designs agent orchestration, Bedrock integration, data model, HA topology"),
        ("Backend Engineer (Hybrid)", "Senior", 2,
         "Python, FastAPI, async, LangGraph/LangChain, Bedrock/Converse API, PostgreSQL, NetworkX, Data/ML (scikit-learn, feature eng, EDI/837 ingestion)",
         "Hybrid build+data/ML: agents, tools, rules/risk engine, APIs, entity graph, vision pipeline, data pipelines & model tuning"),
        ("Backend Engineer", "Mid", 1,
         "Python, FastAPI, SQL, REST, unit testing",
         "Supports CRUD, integrations, data plumbing, test coverage"),
        ("Frontend Engineer", "Senior", 1,
         "React 19, TypeScript, WebSocket, state mgmt, Tailwind, data viz",
         "Builds examiner console, real-time chat, dossier & queue UIs"),
        ("Frontend Engineer", "Mid", 1,
         "React, TypeScript, component libraries, responsive UI",
         "Implements screens, forms, dashboards, accessibility"),
        ("DevOps + Security", "Senior", 1,
         "AWS (ECS/Fargate, RDS, ElastiCache, IAM, VPC), Terraform/CDK, CI/CD, CloudWatch, KMS, threat modeling, HIPAA/SOC2 controls, pen-test coordination",
         "Hybrid DevSecOps: IaC, pipelines, secrets, observability, security guardrails & compliance tooling"),
        ("QA Engineer", "Senior", 1,
         "Test strategy, Playwright/Pytest, API testing, LLM output eval, security testing",
         "Validates rules, agent behavior, regression, non-deterministic AI eval"),
        ("QA Engineer", "Mid", 1,
         "Manual + automated testing, test case design, defect tracking",
         "Executes UAT support, exploratory & regression testing"),
        ("Tech Doc Writer", "Mid", 1,
         "Technical writing, API docs, runbooks, diagrams, examiner user guides",
         "Produces architecture docs, ops runbooks, examiner training material"),
        ("Business Analyst", "SME (P/T)", 1,
         "Requirements, process mapping, rule documentation, examiner workflow analysis",
         "Front-loaded; translates fraud rules & workflows into specs while keeping day job"),
        ("Compliance Advisor", "SME (P/T)", 1,
         "Insurance regulation, model risk, explainability, HIPAA/DOI, adverse-action rules",
         "Embedded part-time; sign-off at Discovery & UAT gates alongside current role"),
        ("Fraud Analyst (SME)", "SME (P/T)", 1,
         "Fraud typologies, risk-model tuning, false-positive review, SIU outcomes",
         "Validates rules/risk model against real fraud; works alongside current role"),
        ("Fraud Examiner (SIU)", "SME (P/T)", 1,
         "Hands-on claims investigation, examiner workflow, edge-case judgement",
         "Client/internal SME; validates AI investigations during UAT, embedded part-time"),
    ]

    team_start = row
    for r in team:
        name, sen, cnt, skills, why = r
        ws[f'A{row}'] = name
        ws[f'B{row}'] = sen
        ws[f'C{row}'] = cnt
        ws[f'C{row}'].alignment = Alignment(horizontal='center')
        ws[f'D{row}'] = skills
        ws[f'D{row}'].alignment = Alignment(wrap_text=True, vertical='top')
        ws[f'E{row}'] = why
        ws[f'E{row}'].alignment = Alignment(wrap_text=True, vertical='top')
        for col in ['A', 'B', 'C', 'D', 'E']:
            ws[f'{col}{row}'].border = border
        row += 1

    # headcount total
    ws[f'A{row}'] = "TOTAL HEADCOUNT"
    ws[f'A{row}'].font = Font(bold=True)
    ws[f'C{row}'] = f'=SUM(C{team_start}:C{row-1})'
    ws[f'C{row}'].font = Font(bold=True)
    ws[f'C{row}'].alignment = Alignment(horizontal='center')
    for col in ['A', 'B', 'C', 'D', 'E']:
        ws[f'{col}{row}'].fill = total_fill
        ws[f'{col}{row}'].border = border
    row += 2

    ws.merge_cells(f'A{row}:E{row}')
    ws[f'A{row}'] = "NOTES ON TEAM COMPOSITION"
    ws[f'A{row}'].font = header_font
    ws[f'A{row}'].fill = header_fill
    row += 1
    notes = [
        "• Hybrid model: Senior Backend engineers also cover Data/ML (feature eng, EDI ingestion, model tuning) - no separate Data/ML hire.",
        "• DevOps is hybrid DevSecOps - absorbs security engineering, threat modeling and compliance tooling.",
        "• The 2x Senior Backend + Architect are the critical GenAI+Data skill set - hardest to hire, highest risk.",
        "• LangGraph / agentic orchestration experience is rare; budget for ramp-up or a specialist premium.",
        "• QA needs LLM-output evaluation skills (non-deterministic testing), not just traditional automation.",
        "• SMEs (BA, Compliance, Fraud Analyst, Fraud Examiner) are front-loaded and part-time, contributing alongside",
        "  their existing roles - heaviest in Discovery/Foundation, tapering to sign-off/UAT (Accenture embedded-SME model).",
    ]
    for n in notes:
        ws.merge_cells(f'A{row}:E{row}')
        ws[f'A{row}'] = n
        ws[f'A{row}'].alignment = Alignment(wrap_text=True)
        row += 1

    # ==================================================================
    # SHEET 2: RATES & ASSUMPTIONS
    # ==================================================================
    ws2 = wb.create_sheet("Rates & Assumptions")
    for c, w in {'A': 28, 'B': 18, 'C': 18, 'D': 18, 'E': 40}.items():
        ws2.column_dimensions[c].width = w

    ws2.merge_cells('A1:E1')
    ws2['A1'] = "Blended Monthly Rates by Role & Region"
    ws2['A1'].font = Font(bold=True, size=18, color="2F5496")

    row = 3
    ws2.merge_cells(f'A{row}:E{row}')
    ws2[f'A{row}'] = "MONTHLY FULLY-LOADED RATES (edit yellow cells to match your market)"
    ws2[f'A{row}'].font = header_font
    ws2[f'A{row}'].fill = header_fill
    row += 1

    rate_headers = ["Role", "Offshore ($/mo)", "Nearshore ($/mo)", "Onshore US ($/mo)", "Notes"]
    for i, h in enumerate(rate_headers):
        col = chr(65 + i)
        ws2[f'{col}{row}'] = h
        ws2[f'{col}{row}'].font = Font(bold=True)
        ws2[f'{col}{row}'].fill = sub_fill
        ws2[f'{col}{row}'].border = border
    row += 1

    # Fully-loaded monthly rates (USD). Realistic 2026 blended ranges.
    rates = [
        ("Product Owner",       6000, 11000, 20000, "Domain-heavy; often client-side"),
        ("Project Manager",     5500, 10000, 18000, "Delivery & budget owner"),
        ("Scrum Master",        4500,  8000, 15000, "Often part-time / shared"),
        ("Tech Architect",      9000, 16000, 28000, "Principal GenAI+AWS; premium & scarce"),
        ("Backend Sr (GenAI+Data)", 7000, 13000, 24000, "LangGraph/Bedrock + Data/ML hybrid"),
        ("Backend Mid",         4500,  8500, 16000, "General Python/FastAPI"),
        ("Frontend Sr",         6000, 11000, 21000, "React19/TS/WebSocket"),
        ("Frontend Mid",        4000,  7500, 15000, "React/TS implementer"),
        ("DevSecOps Sr",        6500, 12000, 22000, "AWS/IaC/CI-CD + security"),
        ("QA Sr",               5000,  9000, 17000, "Automation + LLM eval"),
        ("QA Mid",              3500,  6500, 13000, "Manual + automation"),
        ("Tech Doc Writer",     3000,  5500, 11000, "Part-time typical"),
        ("Business Analyst",    4500,  8000, 15000, "Front-loaded; embedded part-time"),
        ("Compliance Advisor",  6000, 10000, 19000, "Regulated sign-off; fractional"),
        ("Fraud Analyst (SME)", 5000,  8500, 16000, "Rules validation; alongside day job"),
        ("Fraud Examiner SIU",  4000,  7000, 13000, "UAT validation; client/internal SME"),
    ]

    rate_start = row
    for r in rates:
        name, off, near, on, note = r
        ws2[f'A{row}'] = name
        ws2[f'B{row}'] = off
        ws2[f'C{row}'] = near
        ws2[f'D{row}'] = on
        for col in ['B', 'C', 'D']:
            ws2[f'{col}{row}'].number_format = money
            ws2[f'{col}{row}'].fill = input_fill
        ws2[f'E{row}'] = note
        for col in ['A', 'B', 'C', 'D', 'E']:
            ws2[f'{col}{row}'].border = border
        row += 1
    rate_end = row - 1

    row += 1
    ws2.merge_cells(f'A{row}:E{row}')
    ws2[f'A{row}'] = "GLOBAL ASSUMPTIONS (edit yellow cells)"
    ws2[f'A{row}'].font = header_font
    ws2[f'A{row}'].fill = header_fill
    row += 1

    assumptions = [
        ("Delivery region", "Nearshore", "Offshore / Nearshore / Onshore US"),
        ("Project duration (months)", 7, "Post-POC production build"),
        ("Contingency buffer (%)", 15, "Risk reserve on labor"),
        ("Overhead & tooling (%)", 8, "Licenses, SaaS, laptops, PM tools"),
    ]
    assum_start = row
    for label, val, note in assumptions:
        ws2[f'A{row}'] = label
        ws2[f'B{row}'] = val
        ws2[f'B{row}'].fill = input_fill
        ws2[f'B{row}'].border = border
        ws2[f'A{row}'].border = border
        ws2[f'C{row}'] = note
        ws2.merge_cells(f'C{row}:E{row}')
        row += 1

    REGION = f'B{assum_start}'
    DURATION = f'B{assum_start+1}'
    CONTINGENCY = f'B{assum_start+2}'
    OVERHEAD = f'B{assum_start+3}'

    # Helper: which rate column to use based on region choice
    # Offshore=B, Nearshore=C, Onshore=D
    def rate_lookup(role_row):
        return (f'IF({REGION}="Offshore",B{role_row},'
                f'IF({REGION}="Onshore",D{role_row},C{role_row}))')

    # ==================================================================
    # SHEET 3: EFFORT ALLOCATION (role x phase, in person-months)
    # ==================================================================
    ws3 = wb.create_sheet("Effort Allocation")
    for c, w in {'A': 24, 'B': 12, 'C': 12, 'D': 12, 'E': 12, 'F': 12, 'G': 12, 'H': 14}.items():
        ws3.column_dimensions[c].width = w

    ws3.merge_cells('A1:H1')
    ws3['A1'] = "Effort Allocation (Person-Months by Phase)"
    ws3['A1'].font = Font(bold=True, size=18, color="2F5496")

    row = 3
    ws3.merge_cells(f'A{row}:H{row}')
    ws3[f'A{row}'] = "PHASES (weeks): Discovery 4 | Foundation 4 | Core Build 12 | Integration 4 | UAT/Harden 4 | Deploy 2"
    ws3[f'A{row}'].font = header_font
    ws3[f'A{row}'].fill = header_fill
    row += 1

    phase_headers = ["Role", "Discovery", "Foundation", "Core Build", "Integration", "UAT/Harden", "Deploy", "Total PM"]
    for i, h in enumerate(phase_headers):
        col = chr(65 + i)
        ws3[f'{col}{row}'] = h
        ws3[f'{col}{row}'].font = Font(bold=True)
        ws3[f'{col}{row}'].fill = sub_fill
        ws3[f'{col}{row}'].border = border
    row += 1

    # Person-months per role per phase.
    # Phase lengths in months: 1, 1, 3, 1, 1, 0.5  (total 7.5 calendar; effort overlaps)
    # Values = FTE fraction * phase months.
    # Order MUST match the rate rows for cost linkage.
    # (role_label, rate_row_offset, [disc, found, core, integ, uat, deploy])
    effort = [
        ("Product Owner",      0, [1.0, 0.5, 1.5, 0.5, 0.5, 0.25]),
        ("Project Manager",    1, [1.0, 1.0, 3.0, 1.0, 1.0, 0.5]),
        ("Scrum Master",       2, [0.5, 0.5, 1.5, 0.5, 0.5, 0.25]),
        ("Tech Architect",     3, [1.0, 1.0, 2.0, 0.75, 0.5, 0.25]),
        ("Backend Sr (GenAI+Data)", 4, [1.0, 1.5, 6.0, 1.5, 1.0, 0.5]),   # 2 people * fractions
        ("Backend Mid",        5, [0.0, 0.5, 3.0, 1.0, 0.5, 0.25]),
        ("Frontend Sr",        6, [0.5, 0.5, 3.0, 1.0, 0.5, 0.25]),
        ("Frontend Mid",       7, [0.0, 0.5, 3.0, 1.0, 0.5, 0.25]),
        ("DevSecOps Sr",       8, [0.5, 1.0, 2.0, 1.0, 0.75, 0.5]),
        ("QA Sr",              9, [0.25, 0.5, 2.5, 1.0, 1.0, 0.25]),
        ("QA Mid",            10, [0.0, 0.0, 2.0, 1.0, 1.0, 0.25]),
        ("Tech Doc Writer",   11, [0.25, 0.25, 1.0, 0.5, 0.75, 0.5]),
        ("Business Analyst",  12, [0.5, 0.5, 0.5, 0.25, 0.25, 0.0]),     # front-loaded, part-time
        ("Compliance Advisor",13, [0.25, 0.25, 0.1, 0.1, 0.25, 0.1]),    # gates: discovery + UAT
        ("Fraud Analyst (SME)",14,[0.5, 0.25, 0.5, 0.25, 0.25, 0.0]),    # rules + validation
        ("Fraud Examiner SIU",15, [0.25, 0.1, 0.25, 0.25, 0.5, 0.0]),    # UAT-heavy validation
    ]

    effort_start = row
    role_rate_map = {}  # role_label -> (effort_total_cell, rate_row_in_sheet2)
    for label, rr_off, vals in effort:
        ws3[f'A{row}'] = label
        cols = ['B', 'C', 'D', 'E', 'F', 'G']
        for ci, v in enumerate(vals):
            ws3[f'{cols[ci]}{row}'] = v
            ws3[f'{cols[ci]}{row}'].number_format = '0.00'
            ws3[f'{cols[ci]}{row}'].fill = input_fill
        ws3[f'H{row}'] = f'=SUM(B{row}:G{row})'
        ws3[f'H{row}'].number_format = '0.00'
        ws3[f'H{row}'].font = Font(bold=True)
        for col in phase_headers and ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']:
            ws3[f'{col}{row}'].border = border
        role_rate_map[label] = (f'H{row}', rate_start + rr_off)
        row += 1

    # Column totals
    ws3[f'A{row}'] = "TOTAL PERSON-MONTHS"
    ws3[f'A{row}'].font = Font(bold=True)
    for col in ['B', 'C', 'D', 'E', 'F', 'G', 'H']:
        ws3[f'{col}{row}'] = f'=SUM({col}{effort_start}:{col}{row-1})'
        ws3[f'{col}{row}'].number_format = '0.00'
        ws3[f'{col}{row}'].font = Font(bold=True)
        ws3[f'{col}{row}'].fill = total_fill
        ws3[f'{col}{row}'].border = border
    ws3[f'A{row}'].fill = total_fill
    ws3[f'A{row}'].border = border
    row += 2

    ws3.merge_cells(f'A{row}:H{row}')
    ws3[f'A{row}'] = "Person-Months (PM) = FTE fraction x months in phase. Edit yellow cells to reflect your plan."
    ws3[f'A{row}'].alignment = Alignment(wrap_text=True)

    # ==================================================================
    # SHEET 4: COST SUMMARY
    # ==================================================================
    ws4 = wb.create_sheet("Cost Summary")
    for c, w in {'A': 26, 'B': 16, 'C': 16, 'D': 16, 'E': 34}.items():
        ws4.column_dimensions[c].width = w

    ws4.merge_cells('A1:E1')
    ws4['A1'] = "Development Cost Summary"
    ws4['A1'].font = Font(bold=True, size=18, color="2F5496")

    row = 3
    ws4.merge_cells(f'A{row}:E{row}')
    ws4[f'A{row}'] = "LABOR COST BY ROLE (region-driven from Rates sheet)"
    ws4[f'A{row}'].font = header_font
    ws4[f'A{row}'].fill = header_fill
    row += 1

    cs_headers = ["Role", "Person-Months", "Monthly Rate", "Labor Cost", "Notes"]
    for i, h in enumerate(cs_headers):
        col = chr(65 + i)
        ws4[f'{col}{row}'] = h
        ws4[f'{col}{row}'].font = Font(bold=True)
        ws4[f'{col}{row}'].fill = sub_fill
        ws4[f'{col}{row}'].border = border
    row += 1

    labor_start = row
    for label, rr_off, vals in effort:
        effort_cell, rate_row = role_rate_map[label]
        ws4[f'A{row}'] = label
        ws4[f'B{row}'] = f"='Effort Allocation'!{effort_cell}"
        ws4[f'B{row}'].number_format = '0.00'
        ws4[f'C{row}'] = f"='Rates & Assumptions'!{rate_lookup(rate_row)}"
        ws4[f'C{row}'].number_format = money
        ws4[f'D{row}'] = f'=B{row}*C{row}'
        ws4[f'D{row}'].number_format = money
        for col in ['A', 'B', 'C', 'D', 'E']:
            ws4[f'{col}{row}'].border = border
        row += 1
    labor_end = row - 1

    # Subtotal labor
    ws4[f'A{row}'] = "SUBTOTAL - LABOR"
    ws4[f'A{row}'].font = Font(bold=True)
    ws4[f'D{row}'] = f'=SUM(D{labor_start}:D{labor_end})'
    ws4[f'D{row}'].number_format = money
    ws4[f'D{row}'].font = Font(bold=True)
    for col in ['A', 'B', 'C', 'D', 'E']:
        ws4[f'{col}{row}'].fill = calc_fill
        ws4[f'{col}{row}'].border = border
    SUBTOTAL_LABOR = f'D{row}'
    row += 2

    # Additional costs
    ws4.merge_cells(f'A{row}:E{row}')
    ws4[f'A{row}'] = "ADDITIONAL COSTS"
    ws4[f'A{row}'].font = header_font
    ws4[f'A{row}'].fill = header_fill
    row += 1

    ws4[f'A{row}'] = "Overhead & tooling"
    ws4[f'D{row}'] = f"={SUBTOTAL_LABOR}*'Rates & Assumptions'!{OVERHEAD}/100"
    ws4[f'D{row}'].number_format = money
    ws4[f'E{row}'] = "Licenses, SaaS, hardware, PM tools"
    for col in ['A', 'B', 'C', 'D', 'E']:
        ws4[f'{col}{row}'].border = border
    OVERHEAD_COST = f'D{row}'
    row += 1

    ws4[f'A{row}'] = "Contingency buffer"
    ws4[f'D{row}'] = f"={SUBTOTAL_LABOR}*'Rates & Assumptions'!{CONTINGENCY}/100"
    ws4[f'D{row}'].number_format = money
    ws4[f'E{row}'] = "Risk reserve (scope/hiring/GenAI unknowns)"
    for col in ['A', 'B', 'C', 'D', 'E']:
        ws4[f'{col}{row}'].border = border
    CONTINGENCY_COST = f'D{row}'
    row += 2

    # Grand totals
    ws4.merge_cells(f'A{row}:E{row}')
    ws4[f'A{row}'] = "TOTAL DEVELOPMENT COST"
    ws4[f'A{row}'].font = header_font
    ws4[f'A{row}'].fill = header_fill
    row += 1

    ws4[f'A{row}'] = "GRAND TOTAL (one-time build)"
    ws4[f'A{row}'].font = Font(bold=True, size=12)
    ws4[f'D{row}'] = f'={SUBTOTAL_LABOR}+{OVERHEAD_COST}+{CONTINGENCY_COST}'
    ws4[f'D{row}'].number_format = money
    ws4[f'D{row}'].font = Font(bold=True, size=12)
    for col in ['A', 'B', 'C', 'D', 'E']:
        ws4[f'{col}{row}'].fill = total_fill
        ws4[f'{col}{row}'].border = border
    GRAND_TOTAL = f'D{row}'
    row += 1

    ws4[f'A{row}'] = "Est. cost per calendar month"
    ws4[f'D{row}'] = f"={GRAND_TOTAL}/'Rates & Assumptions'!{DURATION}"
    ws4[f'D{row}'].number_format = money
    ws4[f'E{row}'] = "Burn rate across the build"
    for col in ['A', 'B', 'C', 'D', 'E']:
        ws4[f'{col}{row}'].border = border
    row += 2

    # Range view
    ws4.merge_cells(f'A{row}:E{row}')
    ws4[f'A{row}'] = "SCENARIO RANGE (region sensitivity)"
    ws4[f'A{row}'].font = header_font
    ws4[f'A{row}'].fill = header_fill
    row += 1
    ws4[f'A{row}'] = "Set region on 'Rates & Assumptions' to Offshore / Nearshore / Onshore US to see low/base/high."
    ws4.merge_cells(f'A{row}:E{row}')
    ws4[f'A{row}'].alignment = Alignment(wrap_text=True)
    row += 2

    ws4[f'A{row}'] = "Guideline ranges (this scope, ~7 months):"
    ws4[f'A{row}'].font = Font(bold=True)
    row += 1
    guide = [
        ("Offshore-heavy blend", "$350K - $500K"),
        ("Nearshore blend (base)", "$550K - $800K"),
        ("Onshore US blend", "$1.1M - $1.6M"),
    ]
    for g, v in guide:
        ws4[f'A{row}'] = g
        ws4[f'B{row}'] = v
        ws4.merge_cells(f'B{row}:C{row}')
        ws4[f'A{row}'].border = border
        for col in ['B', 'C']:
            ws4[f'{col}{row}'].border = border
        row += 1

    # Save
    filename = "claims_copilot_dev_cost_calculator.xlsx"
    wb.save(filename)
    print(f"Created: {filename}")
    print("Sheets: Team & Skills | Rates & Assumptions | Effort Allocation | Cost Summary")
    return filename


if __name__ == "__main__":
    create_dev_cost_calculator()
