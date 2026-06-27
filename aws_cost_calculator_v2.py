"""
AWS Cost Calculator for Claims Copilot - Version 2
Includes model alternatives, service options, and trade-off analysis
"""

import openpyxl
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

def create_cost_calculator():
    wb = openpyxl.Workbook()
    
    # Styles
    header_font = Font(bold=True, size=14, color="FFFFFF")
    header_fill = PatternFill(start_color="2F5496", end_color="2F5496", fill_type="solid")
    input_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
    calc_fill = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
    total_fill = PatternFill(start_color="DDEBF7", end_color="DDEBF7", fill_type="solid")
    warning_fill = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")
    alt_fill = PatternFill(start_color="E2F0D9", end_color="E2F0D9", fill_type="solid")
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    currency_format = '"$"#,##0.00'
    number_format = '#,##0'
    
    # ==================== SHEET 1: MODEL COMPARISON ====================
    ws_models = wb.active
    ws_models.title = "Model Comparison"
    
    ws_models.column_dimensions['A'].width = 25
    ws_models.column_dimensions['B'].width = 15
    ws_models.column_dimensions['C'].width = 15
    ws_models.column_dimensions['D'].width = 12
    ws_models.column_dimensions['E'].width = 12
    ws_models.column_dimensions['F'].width = 15
    ws_models.column_dimensions['G'].width = 50
    
    row = 1
    ws_models.merge_cells('A1:G1')
    ws_models['A1'] = "AWS Bedrock Model Comparison for Claims Copilot (June 2026)"
    ws_models['A1'].font = Font(bold=True, size=18, color="2F5496")
    row = 3
    
    # Model comparison header
    ws_models.merge_cells(f'A{row}:G{row}')
    ws_models[f'A{row}'] = "AVAILABLE BEDROCK MODELS (Claude 3.x models are RETIRED)"
    ws_models[f'A{row}'].font = header_font
    ws_models[f'A{row}'].fill = header_fill
    row += 1
    
    headers = ["Model", "Input $/1M", "Output $/1M", "Speed", "Quality", "Recommended For", "Trade-offs"]
    for i, h in enumerate(headers):
        col = chr(65 + i)
        ws_models[f'{col}{row}'] = h
        ws_models[f'{col}{row}'].font = Font(bold=True)
        ws_models[f'{col}{row}'].fill = PatternFill(start_color="D9E2F3", end_color="D9E2F3", fill_type="solid")
        ws_models[f'{col}{row}'].border = border
    row += 1
    
    # Model data: (name, input_price, output_price, speed, quality, recommended_for, tradeoffs)
    # Pricing as of June 2026 - Claude 4.x models (3.x models are retired)
    models = [
        ("Claude Haiku 4.5", 1.00, 5.00, "⚡⚡⚡", "★★★★", "RECOMMENDED - Best balance", "Fast, cost-effective, great tool-calling"),
        ("Claude Sonnet 4.5", 3.00, 15.00, "⚡⚡", "★★★★★", "Complex investigations", "3x cost of Haiku, better reasoning"),
        ("Claude Sonnet 4.6", 3.50, 17.50, "⚡⚡", "★★★★★", "Latest mid-tier", "Newest Sonnet, slight premium"),
        ("Claude Opus 4.5", 15.00, 75.00, "⚡", "★★★★★+", "Critical decisions", "15x cost of Haiku, top quality"),
        ("Claude Opus 4.8", 20.00, 100.00, "⚡", "★★★★★+", "Absolute best quality", "Latest Opus, highest cost"),
        ("Llama 3.2 90B", 1.35, 1.35, "⚡⚡", "★★★", "Cost-sensitive", "Open source, less reliable tool-calling"),
        ("Amazon Nova Pro", 0.80, 3.20, "⚡⚡⚡", "★★★", "AWS-native option", "Cheaper but less capable than Claude"),
        ("Mistral Large 2", 4.00, 12.00, "⚡⚡", "★★★★", "Alternative to Sonnet", "Good quality, different strengths"),
    ]
    
    model_start_row = row
    for model_data in models:
        name, inp, out, speed, quality, rec, trade = model_data
        ws_models[f'A{row}'] = name
        ws_models[f'B{row}'] = inp
        ws_models[f'B{row}'].number_format = '"$"#,##0.00'
        ws_models[f'C{row}'] = out
        ws_models[f'C{row}'].number_format = '"$"#,##0.00'
        ws_models[f'D{row}'] = speed
        ws_models[f'E{row}'] = quality
        ws_models[f'F{row}'] = rec
        ws_models[f'G{row}'] = trade
        
        # Highlight recommended model
        fill = alt_fill if name == "Claude 3.5 Haiku" else None
        for col in ['A', 'B', 'C', 'D', 'E', 'F', 'G']:
            ws_models[f'{col}{row}'].border = border
            if fill:
                ws_models[f'{col}{row}'].fill = fill
        row += 1
    
    row += 2
    
    # Analysis section
    ws_models.merge_cells(f'A{row}:G{row}')
    ws_models[f'A{row}'] = "RECOMMENDATION ANALYSIS"
    ws_models[f'A{row}'].font = header_font
    ws_models[f'A{row}'].fill = header_fill
    row += 1
    
    analysis = [
        ("Why Claude Haiku 4.5?", "Best cost/performance for Claims Copilot workload:"),
        ("", "• Tool-calling reliability: 95%+ success rate on structured outputs"),
        ("", "• Speed: 2-4 second responses (excellent for chat UX)"),
        ("", "• Cost: $1.00/M input is 3x cheaper than Sonnet 4.5"),
        ("", "• Vision: Supports document analysis at same price tier"),
        ("", ""),
        ("Is Haiku 4.5 overkill?", "NO - it's the minimum viable for agentic workflows:"),
        ("", "• Older Claude 3.x models are RETIRED (no longer available)"),
        ("", "• Llama/Nova are cheaper but have 80-85% tool-calling success vs 95%+"),
        ("", "• Haiku 4.5 is the entry point for reliable agent orchestration"),
        ("", ""),
        ("When to upgrade?", "Consider Claude Sonnet 4.5/4.6 (3x cost) if:"),
        ("", "• Investigation accuracy is critical and Haiku misses fraud patterns"),
        ("", "• Regulatory scrutiny requires deeper reasoning chains"),
        ("", "• Human reviewers frequently disagree with AI recommendations"),
        ("", ""),
        ("When to use Opus?", "Consider Claude Opus 4.x (15-20x cost) only if:"),
        ("", "• Handling edge cases that require exceptional reasoning"),
        ("", "• Final decision-maker with legal/compliance implications"),
        ("", "• Budget is not a primary constraint"),
    ]
    
    for label, text in analysis:
        ws_models[f'A{row}'] = label
        ws_models[f'A{row}'].font = Font(bold=True) if label else None
        ws_models[f'B{row}'] = text
        ws_models.merge_cells(f'B{row}:G{row}')
        row += 1
    
    row += 2
    
    # Cost comparison table
    ws_models.merge_cells(f'A{row}:G{row}')
    ws_models[f'A{row}'] = "MONTHLY COST COMPARISON (50 users, 500 claims/day, same workload)"
    ws_models[f'A{row}'].font = header_font
    ws_models[f'A{row}'].fill = header_fill
    row += 1
    
    comparison_headers = ["Model", "Chat Cost", "Investigation Cost", "Vision Cost", "Total Bedrock", "vs Haiku 3.5", "Notes"]
    for i, h in enumerate(comparison_headers):
        col = chr(65 + i)
        ws_models[f'{col}{row}'] = h
        ws_models[f'{col}{row}'].font = Font(bold=True)
        ws_models[f'{col}{row}'].fill = PatternFill(start_color="D9E2F3", end_color="D9E2F3", fill_type="solid")
        ws_models[f'{col}{row}'].border = border
    row += 1
    
    # Pre-calculated costs for reference workload (50 users, 500 claims/day)
    # Based on: 44K chat msgs, 2750 investigations, 33K docs per month
    comparisons = [
        ("Claude Haiku 4.5", 198, 231, 116, 545, "—", "RECOMMENDED"),
        ("Claude Sonnet 4.5", 593, 693, 347, 1633, "+200%", "Premium quality"),
        ("Claude Sonnet 4.6", 692, 808, 404, 1904, "+249%", "Latest Sonnet"),
        ("Claude Opus 4.5", 2966, 3467, 1733, 8166, "+1399%", "Top tier, high cost"),
        ("Claude Opus 4.8", 3955, 4622, 2311, 10888, "+1898%", "Best quality, highest cost"),
        ("Amazon Nova Pro", 158, 185, 93, 436, "-20%", "Cheaper but less reliable"),
        ("Llama 3.2 90B", 238, 278, 139, 655, "+20%", "Open source alternative"),
    ]
    
    for comp in comparisons:
        name, chat, invest, vision, total, diff, notes = comp
        ws_models[f'A{row}'] = name
        ws_models[f'B{row}'] = chat
        ws_models[f'B{row}'].number_format = currency_format
        ws_models[f'C{row}'] = invest
        ws_models[f'C{row}'].number_format = currency_format
        ws_models[f'D{row}'] = vision
        ws_models[f'D{row}'].number_format = currency_format
        ws_models[f'E{row}'] = total
        ws_models[f'E{row}'].number_format = currency_format
        ws_models[f'F{row}'] = diff
        ws_models[f'G{row}'] = notes
        
        fill = alt_fill if name == "Claude 3.5 Haiku" else None
        for col in ['A', 'B', 'C', 'D', 'E', 'F', 'G']:
            ws_models[f'{col}{row}'].border = border
            if fill:
                ws_models[f'{col}{row}'].fill = fill
        row += 1
    
    # ==================== SHEET 2: SERVICE ALTERNATIVES ====================
    ws_services = wb.create_sheet("Service Alternatives")
    
    ws_services.column_dimensions['A'].width = 30
    ws_services.column_dimensions['B'].width = 20
    ws_services.column_dimensions['C'].width = 15
    ws_services.column_dimensions['D'].width = 15
    ws_services.column_dimensions['E'].width = 45
    
    row = 1
    ws_services.merge_cells('A1:E1')
    ws_services['A1'] = "AWS Service Alternatives & Trade-offs"
    ws_services['A1'].font = Font(bold=True, size=18, color="2F5496")
    row = 3
    
    # COMPUTE ALTERNATIVES
    ws_services.merge_cells(f'A{row}:E{row}')
    ws_services[f'A{row}'] = "COMPUTE OPTIONS"
    ws_services[f'A{row}'].font = header_font
    ws_services[f'A{row}'].fill = header_fill
    row += 1
    
    for i, h in enumerate(["Option", "Monthly Cost (50 users)", "Pros", "Cons", "Recommendation"]):
        col = chr(65 + i)
        ws_services[f'{col}{row}'] = h
        ws_services[f'{col}{row}'].font = Font(bold=True)
        ws_services[f'{col}{row}'].border = border
    row += 1
    
    compute_options = [
        ("ECS Fargate", "$340", "No server mgmt, auto-scaling", "Higher cost than EC2", "RECOMMENDED for <100 users"),
        ("ECS on EC2", "$200", "40% cheaper, Spot instances", "More ops overhead", "Consider for cost-sensitive"),
        ("Lambda + API GW", "$150", "Pay-per-request, scales to zero", "Cold starts, 15min limit", "Good for variable load"),
        ("EKS Fargate", "$400", "K8s ecosystem, portable", "Complexity, learning curve", "Only if K8s required"),
        ("App Runner", "$280", "Simplest deployment", "Less control, fewer options", "Good for simple APIs"),
    ]
    
    for opt in compute_options:
        name, cost, pros, cons, rec = opt
        ws_services[f'A{row}'] = name
        ws_services[f'B{row}'] = cost
        ws_services[f'C{row}'] = pros
        ws_services[f'D{row}'] = cons
        ws_services[f'E{row}'] = rec
        fill = alt_fill if "RECOMMENDED" in rec else None
        for col in ['A', 'B', 'C', 'D', 'E']:
            ws_services[f'{col}{row}'].border = border
            if fill:
                ws_services[f'{col}{row}'].fill = fill
        row += 1
    
    row += 1
    
    # DATABASE ALTERNATIVES
    ws_services.merge_cells(f'A{row}:E{row}')
    ws_services[f'A{row}'] = "DATABASE OPTIONS"
    ws_services[f'A{row}'].font = header_font
    ws_services[f'A{row}'].fill = header_fill
    row += 1
    
    for i, h in enumerate(["Option", "Monthly Cost", "Pros", "Cons", "Recommendation"]):
        col = chr(65 + i)
        ws_services[f'{col}{row}'] = h
        ws_services[f'{col}{row}'].font = Font(bold=True)
        ws_services[f'{col}{row}'].border = border
    row += 1
    
    db_options = [
        ("RDS PostgreSQL t3.medium", "$101 (Multi-AZ)", "Managed, reliable, Multi-AZ", "Fixed cost even if idle", "RECOMMENDED for prod"),
        ("RDS PostgreSQL t3.small", "$50 (Single-AZ)", "Cheaper for non-prod", "No HA, risk of downtime", "Good for staging/dev"),
        ("Aurora Serverless v2", "$80-300", "Auto-scales, pay-per-use", "Can spike unexpectedly", "Consider for variable load"),
        ("DynamoDB", "$50-150", "Serverless, fast reads", "Complex queries harder", "Good for simple key-value"),
        ("Aurora PostgreSQL", "$200+", "High performance, read replicas", "More expensive", "For high-volume (>1K TPS)"),
    ]
    
    for opt in db_options:
        name, cost, pros, cons, rec = opt
        ws_services[f'A{row}'] = name
        ws_services[f'B{row}'] = cost
        ws_services[f'C{row}'] = pros
        ws_services[f'D{row}'] = cons
        ws_services[f'E{row}'] = rec
        fill = alt_fill if "RECOMMENDED" in rec else None
        for col in ['A', 'B', 'C', 'D', 'E']:
            ws_services[f'{col}{row}'].border = border
            if fill:
                ws_services[f'{col}{row}'].fill = fill
        row += 1
    
    row += 1
    
    # CACHING ALTERNATIVES
    ws_services.merge_cells(f'A{row}:E{row}')
    ws_services[f'A{row}'] = "CACHING OPTIONS"
    ws_services[f'A{row}'].font = header_font
    ws_services[f'A{row}'].fill = header_fill
    row += 1
    
    for i, h in enumerate(["Option", "Monthly Cost", "Pros", "Cons", "Recommendation"]):
        col = chr(65 + i)
        ws_services[f'{col}{row}'] = h
        ws_services[f'{col}{row}'].font = Font(bold=True)
        ws_services[f'{col}{row}'].border = border
    row += 1
    
    cache_options = [
        ("ElastiCache Redis t3.small", "$25", "Full Redis features, reliable", "Fixed cost", "RECOMMENDED"),
        ("ElastiCache Redis t3.micro", "$13", "Cheapest managed option", "Limited memory (500MB)", "OK for <20 users"),
        ("ElastiCache Serverless", "$20-100", "Auto-scales, no sizing", "Can be unpredictable cost", "Consider for variable load"),
        ("DynamoDB DAX", "$50+", "If using DynamoDB already", "Only for DynamoDB", "Only with DynamoDB"),
        ("In-memory (no cache)", "$0", "No extra cost", "Slower, lost on restart", "Only for demo/dev"),
    ]
    
    for opt in cache_options:
        name, cost, pros, cons, rec = opt
        ws_services[f'A{row}'] = name
        ws_services[f'B{row}'] = cost
        ws_services[f'C{row}'] = pros
        ws_services[f'D{row}'] = cons
        ws_services[f'E{row}'] = rec
        fill = alt_fill if "RECOMMENDED" in rec else None
        for col in ['A', 'B', 'C', 'D', 'E']:
            ws_services[f'{col}{row}'].border = border
            if fill:
                ws_services[f'{col}{row}'].fill = fill
        row += 1
    
    row += 1
    
    # BEDROCK OPTIMIZATION OPTIONS
    ws_services.merge_cells(f'A{row}:E{row}')
    ws_services[f'A{row}'] = "BEDROCK OPTIMIZATION OPTIONS"
    ws_services[f'A{row}'].font = header_font
    ws_services[f'A{row}'].fill = header_fill
    row += 1
    
    for i, h in enumerate(["Option", "Savings", "Pros", "Cons", "Recommendation"]):
        col = chr(65 + i)
        ws_services[f'{col}{row}'] = h
        ws_services[f'{col}{row}'].font = Font(bold=True)
        ws_services[f'{col}{row}'].border = border
    row += 1
    
    bedrock_opts = [
        ("On-Demand (default)", "0%", "No commitment, flexible", "Full price", "Start here"),
        ("Batch API", "50%", "Half price for async jobs", "24hr max latency", "RECOMMENDED for investigations"),
        ("Provisioned Throughput", "20-40%", "Guaranteed capacity", "$10K+ commitment", "Only for >100K claims/month"),
        ("Prompt Caching", "10-30%", "Cache system prompts", "Requires code changes", "Implement for chat"),
        ("Response Caching (Redis)", "Variable", "Avoid repeat LLM calls", "Stale responses risk", "Good for common queries"),
    ]
    
    for opt in bedrock_opts:
        name, savings, pros, cons, rec = opt
        ws_services[f'A{row}'] = name
        ws_services[f'B{row}'] = savings
        ws_services[f'C{row}'] = pros
        ws_services[f'D{row}'] = cons
        ws_services[f'E{row}'] = rec
        fill = alt_fill if "RECOMMENDED" in rec else None
        for col in ['A', 'B', 'C', 'D', 'E']:
            ws_services[f'{col}{row}'].border = border
            if fill:
                ws_services[f'{col}{row}'].fill = fill
        row += 1
    
    # ==================== SHEET 3: MAIN CALCULATOR ====================
    ws = wb.create_sheet("Cost Calculator")
    
    ws.column_dimensions['A'].width = 45
    ws.column_dimensions['B'].width = 18
    ws.column_dimensions['C'].width = 18
    ws.column_dimensions['D'].width = 18
    ws.column_dimensions['E'].width = 50
    
    row = 1
    ws.merge_cells('A1:E1')
    ws['A1'] = "AWS Cost Calculator - Claims Copilot"
    ws['A1'].font = Font(bold=True, size=18, color="2F5496")
    ws['A1'].alignment = Alignment(horizontal='center')
    row = 3
    
    # ========== INPUT SECTION ==========
    ws.merge_cells(f'A{row}:E{row}')
    ws[f'A{row}'] = "INPUT PARAMETERS (Enter values in YELLOW cells)"
    ws[f'A{row}'].font = header_font
    ws[f'A{row}'].fill = header_fill
    row += 1
    
    headers = ["Question", "Your Input", "Unit", "Min-Max Range", "Guidance"]
    for i, h in enumerate(headers):
        col = chr(65 + i)
        ws[f'{col}{row}'] = h
        ws[f'{col}{row}'].font = Font(bold=True)
        ws[f'{col}{row}'].fill = PatternFill(start_color="D9E2F3", end_color="D9E2F3", fill_type="solid")
        ws[f'{col}{row}'].border = border
    row += 1
    
    inputs = [
        ("1. Concurrent examiners", 50, "users", "5-500", "Active users at same time"),
        ("2. New claims per day", 500, "claims/day", "100-10,000", "Daily incoming claims"),
        ("3. Chat messages per examiner/day", 40, "messages", "20-100", "Copilot interactions per user"),
        ("4. % claims needing AI investigation", 25, "%", "10-50", "Full investigation rate"),
        ("5. Documents per claim", 3, "docs", "1-10", "Attachments per claim"),
        ("6. Average document size", 1.5, "MB", "0.5-5", "Image/PDF file size"),
        ("7. Data retention period", 3, "years", "1-7", "How long to keep data"),
        ("8. Uptime SLA", 99.9, "%", "99.5-99.99", "99.9=Multi-AZ, 99.99=Multi-region"),
        ("9. Number of environments", 2, "envs", "1-3", "1=Prod, 2=+Staging, 3=+Dev"),
        ("10. Working days per month", 22, "days", "20-25", "Business days"),
    ]
    
    input_start = row
    for q, default, unit, range_str, guidance in inputs:
        ws[f'A{row}'] = q
        ws[f'B{row}'] = default
        ws[f'B{row}'].fill = input_fill
        ws[f'B{row}'].number_format = '#,##0.00' if isinstance(default, float) else '#,##0'
        ws[f'C{row}'] = unit
        ws[f'D{row}'] = range_str
        ws[f'E{row}'] = guidance
        for col in ['A', 'B', 'C', 'D', 'E']:
            ws[f'{col}{row}'].border = border
        row += 1
    
    INPUT_USERS = f'B{input_start}'
    INPUT_CLAIMS = f'B{input_start+1}'
    INPUT_CHAT = f'B{input_start+2}'
    INPUT_INVEST = f'B{input_start+3}'
    INPUT_DOCS = f'B{input_start+4}'
    INPUT_SIZE = f'B{input_start+5}'
    INPUT_RETENTION = f'B{input_start+6}'
    INPUT_SLA = f'B{input_start+7}'
    INPUT_ENVS = f'B{input_start+8}'
    INPUT_DAYS = f'B{input_start+9}'
    
    row += 1
    
    # ========== MODEL SELECTION ==========
    ws.merge_cells(f'A{row}:E{row}')
    ws[f'A{row}'] = "MODEL SELECTION (Change pricing to see alternatives)"
    ws[f'A{row}'].font = header_font
    ws[f'A{row}'].fill = header_fill
    row += 1
    
    model_headers = ["Model Option", "Input $/1M", "Output $/1M", "Selected?", "Notes"]
    for i, h in enumerate(model_headers):
        col = chr(65 + i)
        ws[f'{col}{row}'] = h
        ws[f'{col}{row}'].font = Font(bold=True)
        ws[f'{col}{row}'].fill = PatternFill(start_color="D9E2F3", end_color="D9E2F3", fill_type="solid")
        ws[f'{col}{row}'].border = border
    row += 1
    
    model_options = [
        ("Amazon Nova Pro (Budget)", 0.80, 3.20, "", "Cheapest, less capable"),
        ("Claude Haiku 4.5 (Recommended)", 1.00, 5.00, "✓", "Best balance - DEFAULT"),
        ("Claude Sonnet 4.5 (Premium)", 3.00, 15.00, "", "Higher quality, 3x cost"),
        ("Claude Sonnet 4.6 (Latest Mid)", 3.50, 17.50, "", "Newest Sonnet"),
        ("Claude Opus 4.5+ (Enterprise)", 15.00, 75.00, "", "Top tier, 15x cost"),
    ]
    
    model_start = row
    for name, inp, out, selected, notes in model_options:
        ws[f'A{row}'] = name
        ws[f'B{row}'] = inp
        ws[f'B{row}'].number_format = '"$"#,##0.00'
        ws[f'C{row}'] = out
        ws[f'C{row}'].number_format = '"$"#,##0.00'
        ws[f'D{row}'] = selected
        ws[f'D{row}'].fill = input_fill if not selected else alt_fill
        ws[f'E{row}'] = notes
        for col in ['A', 'B', 'C', 'D', 'E']:
            ws[f'{col}{row}'].border = border
        row += 1
    
    row += 1
    
    # Active model pricing (user selects by entering ✓)
    ws[f'A{row}'] = "ACTIVE MODEL PRICING (edit B/C in row with ✓)"
    ws[f'A{row}'].font = Font(bold=True)
    row += 1
    ws[f'A{row}'] = "Input token price ($/1M)"
    ws[f'B{row}'] = 1.00
    ws[f'B{row}'].fill = input_fill
    ws[f'B{row}'].number_format = '"$"#,##0.00'
    PRICE_IN = f'B{row}'
    row += 1
    ws[f'A{row}'] = "Output token price ($/1M)"
    ws[f'B{row}'] = 5.00
    ws[f'B{row}'].fill = input_fill
    ws[f'B{row}'].number_format = '"$"#,##0.00'
    PRICE_OUT = f'B{row}'
    row += 1
    
    row += 1
    
    # ========== CALCULATED VOLUMES ==========
    ws.merge_cells(f'A{row}:E{row}')
    ws[f'A{row}'] = "CALCULATED MONTHLY VOLUMES"
    ws[f'A{row}'].font = header_font
    ws[f'A{row}'].fill = header_fill
    row += 1
    
    calc_start = row
    ws[f'A{row}'] = "Chat messages/month"
    ws[f'B{row}'] = f'={INPUT_USERS}*{INPUT_CHAT}*{INPUT_DAYS}'
    ws[f'B{row}'].number_format = number_format
    CALC_CHAT = f'B{row}'
    row += 1
    
    ws[f'A{row}'] = "Claims/month"
    ws[f'B{row}'] = f'={INPUT_CLAIMS}*{INPUT_DAYS}'
    ws[f'B{row}'].number_format = number_format
    CALC_CLAIMS = f'B{row}'
    row += 1
    
    ws[f'A{row}'] = "Investigations/month"
    ws[f'B{row}'] = f'={CALC_CLAIMS}*{INPUT_INVEST}/100'
    ws[f'B{row}'].number_format = number_format
    CALC_INVEST = f'B{row}'
    row += 1
    
    ws[f'A{row}'] = "Documents/month"
    ws[f'B{row}'] = f'={CALC_CLAIMS}*{INPUT_DOCS}'
    ws[f'B{row}'].number_format = number_format
    CALC_DOCS = f'B{row}'
    row += 1
    
    ws[f'A{row}'] = "Storage growth/month (GB)"
    ws[f'B{row}'] = f'={CALC_DOCS}*{INPUT_SIZE}/1024'
    ws[f'B{row}'].number_format = '#,##0.0'
    CALC_STORAGE = f'B{row}'
    row += 1
    
    for r in range(calc_start, row):
        ws[f'A{r}'].border = border
        ws[f'B{r}'].border = border
        ws[f'A{r}'].fill = calc_fill
        ws[f'B{r}'].fill = calc_fill
    
    row += 1
    
    # ========== COST BREAKDOWN ==========
    ws.merge_cells(f'A{row}:E{row}')
    ws[f'A{row}'] = "MONTHLY COST BREAKDOWN"
    ws[f'A{row}'].font = header_font
    ws[f'A{row}'].fill = header_fill
    row += 1
    
    cost_headers = ["Category", "Low Estimate", "Base Estimate", "High Estimate", "Notes"]
    for i, h in enumerate(cost_headers):
        col = chr(65 + i)
        ws[f'{col}{row}'] = h
        ws[f'{col}{row}'].font = Font(bold=True)
        ws[f'{col}{row}'].fill = PatternFill(start_color="D9E2F3", end_color="D9E2F3", fill_type="solid")
        ws[f'{col}{row}'].border = border
    row += 1
    
    cost_start = row
    
    # Bedrock - Chat
    ws[f'A{row}'] = "Bedrock - Copilot Chat"
    ws[f'B{row}'] = f'=({CALC_CHAT}*1500/1000000*{PRICE_IN})+({CALC_CHAT}*400/1000000*{PRICE_OUT})'
    ws[f'C{row}'] = f'=({CALC_CHAT}*2000/1000000*{PRICE_IN})+({CALC_CHAT}*500/1000000*{PRICE_OUT})'
    ws[f'D{row}'] = f'=({CALC_CHAT}*3000/1000000*{PRICE_IN})+({CALC_CHAT}*800/1000000*{PRICE_OUT})'
    ws[f'E{row}'] = "1.5K-3K input, 400-800 output per msg"
    COST_CHAT = f'C{row}'
    row += 1
    
    # Bedrock - Investigations
    ws[f'A{row}'] = "Bedrock - AI Investigations"
    ws[f'B{row}'] = f'=({CALC_INVEST}*8*2500/1000000*{PRICE_IN})+({CALC_INVEST}*8*600/1000000*{PRICE_OUT})'
    ws[f'C{row}'] = f'=({CALC_INVEST}*12*3000/1000000*{PRICE_IN})+({CALC_INVEST}*12*800/1000000*{PRICE_OUT})'
    ws[f'D{row}'] = f'=({CALC_INVEST}*15*4000/1000000*{PRICE_IN})+({CALC_INVEST}*15*1000/1000000*{PRICE_OUT})'
    ws[f'E{row}'] = "8-15 LLM calls per investigation"
    COST_INVEST = f'C{row}'
    row += 1
    
    # Bedrock - Vision
    ws[f'A{row}'] = "Bedrock - Document Vision"
    ws[f'B{row}'] = f'=({CALC_DOCS}*(800+{INPUT_SIZE}*200)/1000000*{PRICE_IN})+({CALC_DOCS}*300/1000000*{PRICE_OUT})'
    ws[f'C{row}'] = f'=({CALC_DOCS}*(1000+{INPUT_SIZE}*300)/1000000*{PRICE_IN})+({CALC_DOCS}*400/1000000*{PRICE_OUT})'
    ws[f'D{row}'] = f'=({CALC_DOCS}*(1500+{INPUT_SIZE}*500)/1000000*{PRICE_IN})+({CALC_DOCS}*600/1000000*{PRICE_OUT})'
    ws[f'E{row}'] = "Tokens scale with image size"
    COST_VISION = f'C{row}'
    row += 1
    
    # Compute - ECS
    ws[f'A{row}'] = "Compute - ECS Fargate"
    ws[f'B{row}'] = f'=CEILING({INPUT_USERS}/30,1)*2*730*0.04048+CEILING({INPUT_USERS}/30,1)*4*730*0.004445'
    ws[f'C{row}'] = f'=CEILING({INPUT_USERS}/25,1)*2*730*0.04048+CEILING({INPUT_USERS}/25,1)*4*730*0.004445'
    ws[f'D{row}'] = f'=CEILING({INPUT_USERS}/20,1)*2*730*0.04048+CEILING({INPUT_USERS}/20,1)*4*730*0.004445'
    ws[f'E{row}'] = "1 task per 20-30 users, 2vCPU/4GB"
    COST_ECS = f'C{row}'
    row += 1
    
    # Database - RDS
    ws[f'A{row}'] = "Database - RDS PostgreSQL"
    ws[f'B{row}'] = f'=IF({INPUT_SLA}<99.9,50,101)+15'
    ws[f'C{row}'] = f'=IF({INPUT_SLA}<99.9,50,101)*IF({INPUT_SLA}>=99.99,2,1)+20'
    ws[f'D{row}'] = f'=IF({INPUT_SLA}<99.9,75,150)*IF({INPUT_SLA}>=99.99,2,1)+30'
    ws[f'E{row}'] = "Multi-AZ if SLA>=99.9%"
    COST_RDS = f'C{row}'
    row += 1
    
    # Cache - Redis
    ws[f'A{row}'] = "Cache - ElastiCache Redis"
    ws[f'B{row}'] = '=13'
    ws[f'C{row}'] = '=25'
    ws[f'D{row}'] = '=50'
    ws[f'E{row}'] = "t3.micro to t3.medium"
    COST_REDIS = f'C{row}'
    row += 1
    
    # Storage - S3
    ws[f'A{row}'] = "Storage - S3"
    ws[f'B{row}'] = f'={CALC_STORAGE}*{INPUT_RETENTION}*6*0.023*0.8'
    ws[f'C{row}'] = f'={CALC_STORAGE}*{INPUT_RETENTION}*6*0.023'
    ws[f'D{row}'] = f'={CALC_STORAGE}*{INPUT_RETENTION}*6*0.023*1.3'
    ws[f'E{row}'] = "Avg storage over retention"
    COST_S3 = f'C{row}'
    row += 1
    
    # Networking
    ws[f'A{row}'] = "Networking - ALB + API Gateway"
    ws[f'B{row}'] = '=22+2'
    ws[f'C{row}'] = '=22+5'
    ws[f'D{row}'] = '=22+15'
    ws[f'E{row}'] = "ALB + API requests"
    COST_NET = f'C{row}'
    row += 1
    
    # Monitoring
    ws[f'A{row}'] = "Monitoring - CloudWatch"
    ws[f'B{row}'] = '=10'
    ws[f'C{row}'] = '=20'
    ws[f'D{row}'] = '=40'
    ws[f'E{row}'] = "Logs, metrics, alarms"
    COST_CW = f'C{row}'
    row += 1
    
    # Security
    ws[f'A{row}'] = "Security - KMS + Secrets"
    ws[f'B{row}'] = '=5'
    ws[f'C{row}'] = '=9'
    ws[f'D{row}'] = '=15'
    ws[f'E{row}'] = "Encryption + secrets mgmt"
    COST_SEC = f'C{row}'
    row += 1
    
    # Format cost rows
    for r in range(cost_start, row):
        for col in ['B', 'C', 'D']:
            ws[f'{col}{r}'].number_format = currency_format
        for col in ['A', 'B', 'C', 'D', 'E']:
            ws[f'{col}{r}'].border = border
    
    row += 1
    
    # ========== ENVIRONMENT MULTIPLIER ==========
    ws[f'A{row}'] = "Additional Environments (Staging/Dev)"
    ws[f'B{row}'] = f'=({INPUT_ENVS}-1)*0.4*(B{cost_start}+B{cost_start+1}+B{cost_start+2}+B{cost_start+3}+B{cost_start+4}+B{cost_start+5}+B{cost_start+6}+B{cost_start+7}+B{cost_start+8}+B{cost_start+9})'
    ws[f'C{row}'] = f'=({INPUT_ENVS}-1)*0.5*(C{cost_start}+C{cost_start+1}+C{cost_start+2}+C{cost_start+3}+C{cost_start+4}+C{cost_start+5}+C{cost_start+6}+C{cost_start+7}+C{cost_start+8}+C{cost_start+9})'
    ws[f'D{row}'] = f'=({INPUT_ENVS}-1)*0.6*(D{cost_start}+D{cost_start+1}+D{cost_start+2}+D{cost_start+3}+D{cost_start+4}+D{cost_start+5}+D{cost_start+6}+D{cost_start+7}+D{cost_start+8}+D{cost_start+9})'
    ws[f'E{row}'] = "40-60% of prod per additional env"
    COST_ENVS = f'C{row}'
    for col in ['B', 'C', 'D']:
        ws[f'{col}{row}'].number_format = currency_format
    for col in ['A', 'B', 'C', 'D', 'E']:
        ws[f'{col}{row}'].border = border
    row += 2
    
    # ========== TOTALS ==========
    ws.merge_cells(f'A{row}:E{row}')
    ws[f'A{row}'] = "TOTAL MONTHLY COST"
    ws[f'A{row}'].font = header_font
    ws[f'A{row}'].fill = header_fill
    row += 1
    
    ws[f'A{row}'] = "GRAND TOTAL - MONTHLY"
    ws[f'A{row}'].font = Font(bold=True, size=12)
    ws[f'B{row}'] = f'=SUM(B{cost_start}:B{cost_start+9})+B{cost_start+11}'
    ws[f'C{row}'] = f'=SUM(C{cost_start}:C{cost_start+9})+C{cost_start+11}'
    ws[f'D{row}'] = f'=SUM(D{cost_start}:D{cost_start+9})+D{cost_start+11}'
    ws[f'E{row}'] = "Low / Base / High estimates"
    TOTAL_LOW = f'B{row}'
    TOTAL_BASE = f'C{row}'
    TOTAL_HIGH = f'D{row}'
    for col in ['B', 'C', 'D']:
        ws[f'{col}{row}'].number_format = currency_format
        ws[f'{col}{row}'].font = Font(bold=True, size=12)
    for col in ['A', 'B', 'C', 'D', 'E']:
        ws[f'{col}{row}'].fill = total_fill
        ws[f'{col}{row}'].border = border
    row += 1
    
    ws[f'A{row}'] = "GRAND TOTAL - ANNUAL"
    ws[f'A{row}'].font = Font(bold=True, size=12)
    ws[f'B{row}'] = f'={TOTAL_LOW}*12'
    ws[f'C{row}'] = f'={TOTAL_BASE}*12'
    ws[f'D{row}'] = f'={TOTAL_HIGH}*12'
    ws[f'E{row}'] = "12-month projection"
    for col in ['B', 'C', 'D']:
        ws[f'{col}{row}'].number_format = currency_format
        ws[f'{col}{row}'].font = Font(bold=True, size=12)
    for col in ['A', 'B', 'C', 'D', 'E']:
        ws[f'{col}{row}'].fill = total_fill
        ws[f'{col}{row}'].border = border
    row += 2
    
    # ========== UNIT ECONOMICS ==========
    ws.merge_cells(f'A{row}:E{row}')
    ws[f'A{row}'] = "UNIT ECONOMICS (Base Estimate)"
    ws[f'A{row}'].font = header_font
    ws[f'A{row}'].fill = header_fill
    row += 1
    
    ws[f'A{row}'] = "Cost per claim"
    ws[f'B{row}'] = f'={TOTAL_BASE}/{CALC_CLAIMS}'
    ws[f'B{row}'].number_format = '"$"#,##0.000'
    ws[f'A{row}'].border = border
    ws[f'B{row}'].border = border
    row += 1
    
    ws[f'A{row}'] = "Cost per user per month"
    ws[f'B{row}'] = f'={TOTAL_BASE}/{INPUT_USERS}'
    ws[f'B{row}'].number_format = currency_format
    ws[f'A{row}'].border = border
    ws[f'B{row}'].border = border
    row += 1
    
    ws[f'A{row}'] = "Cost per investigation"
    ws[f'B{row}'] = f'={COST_INVEST}/{CALC_INVEST}'
    ws[f'B{row}'].number_format = '"$"#,##0.000'
    ws[f'A{row}'].border = border
    ws[f'B{row}'].border = border
    row += 1
    
    ws[f'A{row}'] = "Cost per chat message"
    ws[f'B{row}'] = f'={COST_CHAT}/{CALC_CHAT}'
    ws[f'B{row}'].number_format = '"$"#,##0.0000'
    ws[f'A{row}'].border = border
    ws[f'B{row}'].border = border
    row += 2
    
    # ========== OPTIMIZATION NOTE ==========
    ws.merge_cells(f'A{row}:E{row}')
    ws[f'A{row}'] = "POTENTIAL OPTIMIZATIONS (See 'Service Alternatives' sheet for details)"
    ws[f'A{row}'].font = header_font
    ws[f'A{row}'].fill = PatternFill(start_color="70AD47", end_color="70AD47", fill_type="solid")
    row += 1
    
    optimizations = [
        ("Bedrock Batch API for investigations", "50% savings on investigation costs", "Use for non-urgent overnight processing"),
        ("Reserved RDS capacity (1-year)", "40% savings on database", "Commit to 1-year term"),
        ("Spot instances for staging", "70% savings on staging compute", "Accept possible interruptions"),
        ("Response caching in Redis", "10-30% savings on repeat queries", "Implement for common questions"),
        ("S3 Intelligent Tiering", "20% savings on cold storage", "Auto-tier old documents"),
    ]
    
    for opt, savings, notes in optimizations:
        ws[f'A{row}'] = f"• {opt}"
        ws[f'B{row}'] = savings
        ws.merge_cells(f'C{row}:E{row}')
        ws[f'C{row}'] = notes
        row += 1
    
    # Save
    filename = "claims_copilot_aws_cost_calculator_v2.xlsx"
    wb.save(filename)
    print(f"✅ Created: {filename}")
    print("\nSheets included:")
    print("  1. Model Comparison - Bedrock model trade-offs")
    print("  2. Service Alternatives - Compute, DB, cache options")
    print("  3. Cost Calculator - Main calculator with ranges")
    print("\nInstructions:")
    print("  1. Review 'Model Comparison' to choose your model")
    print("  2. Review 'Service Alternatives' for infrastructure options")
    print("  3. Enter values in 'Cost Calculator' yellow cells")
    print("  4. Adjust model pricing in yellow cells to compare")
    
    return filename

if __name__ == "__main__":
    create_cost_calculator()
