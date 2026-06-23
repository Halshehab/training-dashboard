import os
import json
import pandas as pd
import requests
from io import BytesIO

def generate_interactive_calendar():
    # رابط جوجل شيت المباشر بصيغة إكسيل
    google_sheet_url = "https://docs.google.com/spreadsheets/d/1DtM-hFIJwMt-AJ_VejNeUe0MNdOe73Txhg4q8nfOHSk/export?format=xlsx"
    sheet_name = "تقويم التدريب"
    
    print(f"🔄 جاري سحب البيانات  من رابط Google Sheet...")
    
    try:
        # سحب الملف عبر الشبكة
        response = requests.get(google_sheet_url, timeout=30)
        response.raise_for_status()
        excel_data = BytesIO(response.content)
        
        # قراءة الشيت المحدد أو الشيت الأول كبديل آمن
        try:
            df = pd.read_excel(excel_data, sheet_name=sheet_name)
        except Exception:
            df = pd.read_excel(excel_data, sheet_name=0)
            
    except Exception as e:
        print(f"❌ فشل جلب البيانات من الرابط، خطأ: {e}")
        return

    # تنظيف مسميات الأعمدة
    df.columns = df.columns.str.strip()
    
    # خريطة لمطابقة الأعمدة بدقة بما فيها أعمدة التواريخ المباشرة للحقائب وحالة الجاهزية
    rename_dict = {
        'التاريخ': 'Date',
        'السنة': 'Year',
        'الشهر': 'Month',
        'اسم البرنامج': 'Program_Name',
        'المسار': 'Training_Path',
        'عدد الأيام': 'Duration_Days',
        'عدد المتدربين': 'Target_Count',
        'طريقة التنفيذ': 'Type',
        'الموقع': 'Location',
        'الفئة المستهدفة': 'Entity',
        'تكلفة البرنامج': 'Program_Cost',  
        'إجمالي تكلفة أمر الإركاب والانتداب': 'Total_Travel_Cost',
        'التكرارات': 'Repetitions',
        'تاريخ بدء التطوير': 'Bag_Dev_Start',
        'تاريخ انتهاء التطوير': 'Bag_Dev_End',
        'تاريخ انتهاء المراجعة': 'Bag_Review_End',
        'تاريخ الاعتماد النهائي': 'Bag_Approval',
        'حالة الجاهزية': 'Readiness_Status'
    }
    
    df = df.rename(columns=rename_dict)
    
    # معالجة التواريخ والأرباع
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df['Year'] = df['Date'].dt.year.fillna(2026).astype(int)
    df['Month_Val'] = df['Date'].dt.month.fillna(1).astype(int)
    
    # معالجة تواريخ الحقائب التدريبية وتحويلها لتواريخ مقروءة
    bag_date_cols = ['Bag_Dev_Start', 'Bag_Dev_End', 'Bag_Review_End', 'Bag_Approval']
    for col in bag_date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')

    def calculate_quarter(month):
        if month in [1, 2, 3]: return 'Q1'
        elif month in [4, 5, 6]: return 'Q2'
        elif month in [7, 8, 9]: return 'Q3'
        else: return 'Q4'

    df['Quarter'] = df['Month_Val'].apply(calculate_quarter)
    
    # تنظيف الحقول المادية وتحويلها لأرقام مع الحفاظ على الدقة العشرية
    financial_cols = ['Program_Cost', 'Total_Travel_Cost']
    for col in financial_cols:
        if col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.replace(',', '').str.replace('"', '')
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
        else:
            df[col] = 0.0

    if 'Repetitions' in df.columns:
        df['Repetitions'] = pd.to_numeric(df['Repetitions'], errors='coerce').fillna(1).astype(int)
        df.loc[df['Repetitions'] < 1, 'Repetitions'] = 1
    else:
        df['Repetitions'] = 1

    df['Program_Name'] = df['Program_Name'].fillna('برنامج تدريبي غير مسمى')
    df['Training_Path'] = df['Training_Path'].fillna('مسار عام')
    df['Duration_Days'] = pd.to_numeric(df['Duration_Days'], errors='coerce').fillna(1).astype(int)
    df['Target_Count'] = pd.to_numeric(df['Target_Count'], errors='coerce').fillna(0).astype(int)
    df['Type'] = df['Type'].fillna('حضوري')
    df['Location'] = df['Location'].fillna('المقر الرئيسي')
    df['Entity'] = df['Entity'].fillna('جميع الموظفين')
    df['Readiness_Status'] = df['Readiness_Status'].fillna('لم تبدأ')

    # تجهيز سجلات JSON
    programs_list = []
    for idx, row in df.iterrows():
        date_str = row['Date'].strftime('%Y-%m-%d') if not pd.isnull(row['Date']) else f"{row['Year']}-01-01"
        prog_cost = float(row['Program_Cost'])
        trav_cost = float(row['Total_Travel_Cost'])
        
        # استخراج نصوص التواريخ الخاصة بمراحل الحقيبة مباشرة
        b_dev_start = row['Bag_Dev_Start'].strftime('%Y-%m-%d') if ('Bag_Dev_Start' in row and pd.notnull(row['Bag_Dev_Start'])) else '-'
        b_dev_end = row['Bag_Dev_End'].strftime('%Y-%m-%d') if ('Bag_Dev_End' in row and pd.notnull(row['Bag_Dev_End'])) else '-'
        b_rev_end = row['Bag_Review_End'].strftime('%Y-%m-%d') if ('Bag_Review_End' in row and pd.notnull(row['Bag_Review_End'])) else '-'
        b_approval = row['Bag_Approval'].strftime('%Y-%m-%d') if ('Bag_Approval' in row and pd.notnull(row['Bag_Approval'])) else '-'
        r_status = str(row['Readiness_Status']).strip()

        program_item = {
            "id": str(idx + 1), # استخدام الفهرس الفعلي لإكسيل لربط الحفظ والـ Web App بدقة
            "name": str(row['Program_Name']),
            "path": str(row['Training_Path']),
            "date": date_str,
            "year": int(row['Year']),
            "month": int(row['Month_Val']),
            "quarter": str(row['Quarter']),
            "duration": int(row['Duration_Days']),
            "target_count": int(row['Target_Count']),
            "type": str(row['Type']),
            "location": str(row['Location']),
            "entity": str(row['Entity']),
            "program_cost": prog_cost,
            "travel_cost": trav_cost,
            "repetitions": int(row['Repetitions']),
            "grand_total": prog_cost + trav_cost,
            "bag_dev_start": b_dev_start,
            "bag_dev_end": b_dev_end,
            "bag_review_end": b_rev_end,
            "bag_approval": b_approval,
            "readiness_status": r_status
        }
        programs_list.append(program_item)

    programs_json = json.dumps(programs_list, ensure_ascii=False, indent=4)

    # قالب واجهة الـ HTML المحدث بالشاشات الجديدة للحوكمة الإدارية
    html_template = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>__DASHBOARD_TITLE__</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {
            --brand-dark-green: #1d4229;
            --brand-safari-green: #29693b;
            --brand-bright-green: #00ff87;
            --brand-gold: #b08932;
            --brand-yellow: #f4d153;
            --brand-charcoal: #4a4b4d;
            --brand-purple: #420a70;
            
            --bg-primary: #f4f7f5;
            --text-main: #2b302c;
            --card-bg: #ffffff;
            --border-color: #e2e8e4;
            --danger-red: #ef4444;
            --warning-yellow: #f59e0b;
            --success-green: #10b981;
        }
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Cairo', sans-serif;
        }
        body {
            background-color: var(--bg-primary);
            color: var(--text-main);
            padding: 20px;
        }
        
        #login-overlay {
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            background-color: var(--bg-primary);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 9999;
        }
        .login-card {
            background-color: var(--card-bg);
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 10px 25px rgba(29, 66, 41, 0.08);
            border-top: 5px solid var(--brand-dark-green);
            width: 100%;
            max-width: 420px;
            text-align: center;
        }
        .login-card img {
            max-width: 160px;
            margin-bottom: 25px;
            object-fit: contain;
        }
        .login-card h2 {
            font-size: 20px;
            color: var(--brand-dark-green);
            margin-bottom: 8px;
            font-weight: 700;
        }
        .login-card p {
            font-size: 13px;
            color: var(--brand-charcoal);
            margin-bottom: 25px;
        }
        .login-field {
            margin-bottom: 18px;
            text-align: right;
        }
        .login-field label {
            display: block;
            font-size: 13px;
            font-weight: 600;
            color: var(--brand-dark-green);
            margin-bottom: 6px;
        }
        .login-field input {
            width: 100%;
            padding: 12px 14px;
            border-radius: 8px;
            border: 1px solid var(--border-color);
            background-color: #fafbfa;
            font-size: 14px;
            outline: none;
            transition: border-color 0.2s;
        }
        .login-field input:focus {
            border-color: var(--brand-safari-green);
        }
        .btn-login {
            width: 100%;
            padding: 12px;
            background-color: var(--brand-dark-green);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 15px;
            font-weight: 700;
            cursor: pointer;
            transition: background-color 0.2s;
            margin-top: 10px;
        }
        .btn-login:hover {
            background-color: var(--brand-safari-green);
        }
        .error-message {
            color: #d32f2f;
            font-size: 12px;
            font-weight: 600;
            margin-top: 12px;
            display: none;
        }

        #main-dashboard-content {
            display: none;
        }

        .header-container {
            display: flex;
            align-items: center;
            justify-content: space-between;
            background-color: var(--card-bg);
            padding: 20px 30px;
            border-radius: 12px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.02);
            margin-bottom: 25px;
            border-bottom: 3px solid var(--brand-dark-green);
        }
        .page-title-box {
            flex-grow: 1;
            text-align: right;
            margin-right: 20px;
        }
        .page-title-box h1 { 
            font-size: 24px; 
            font-weight: 700; 
            color: var(--brand-dark-green); 
        }
        .page-title-box p { 
            font-size: 13px; 
            color: var(--brand-charcoal); 
            margin-top: 4px;
        }
        .logo-area {
            flex-shrink: 0;
            max-width: 180px;
        }
        .logo-area img {
            max-width: 100%;
            max-height: 75px;
            object-fit: contain;
        }

        /* شريط التبويبات العلوي الرئيسي */
        .portal-nav-tabs {
            display: flex;
            gap: 8px;
            margin-bottom: 25px;
            border-bottom: 2px solid var(--border-color);
        }
        .portal-tab-btn {
            padding: 12px 22px;
            font-size: 14px;
            font-weight: 700;
            color: var(--brand-charcoal);
            background: none;
            border: none;
            cursor: pointer;
            border-radius: 8px 8px 0 0;
            display: flex;
            align-items: center;
            gap: 8px;
            transition: all 0.3s ease;
        }
        .portal-tab-btn.active {
            background-color: var(--brand-dark-green);
            color: white;
        }
        .portal-view-panel {
            display: none;
        }
        .portal-view-panel.active {
            display: block;
        }

        .controls-wrapper {
            display: flex;
            flex-direction: column;
            gap: 15px;
            margin-bottom: 25px;
        }

        .top-filters-container {
            background: linear-gradient(135deg, var(--brand-dark-green), var(--brand-safari-green));
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 4px 10px rgba(29, 66, 41, 0.15);
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
        }
        .filter-group {
            flex: 1;
            min-width: 180px;
        }
        .filter-group label { 
            display: block; 
            font-size: 13px; 
            font-weight: 600; 
            margin-bottom: 6px; 
            color: #ffffff; 
        }
        .filter-group select, .filter-group input {
            width: 100%;
            padding: 10px 14px;
            border-radius: 8px;
            border: 2px solid transparent;
            background-color: #ffffff;
            font-size: 14px;
            color: var(--brand-dark-green);
            font-weight: 600;
            outline: none;
            transition: all 0.2s;
        }

        .action-row-container {
            display: flex;
            align-items: center;
            justify-content: flex-start;
            background-color: var(--card-bg);
            padding: 12px 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.02);
            border: 1px solid var(--border-color);
        }

        .toggle-container {
            display: flex;
            align-items: center;
        }
        .toggle-label {
            font-size: 14px;
            font-weight: 700;
            color: var(--brand-dark-green);
            margin-left: 15px;
        }
        .switch {
            position: relative;
            display: inline-block;
            width: 60px;
            height: 30px;
        }
        .switch input { opacity: 0; width: 0; height: 0; }
        .slider {
            position: absolute;
            cursor: pointer;
            top: 0; left: 0; right: 0; bottom: 0;
            background-color: #ccc;
            transition: .4s;
            border-radius: 34px;
        }
        .slider:before {
            position: absolute;
            content: "";
            height: 22px; width: 22px;
            left: 4px; bottom: 4px;
            background-color: white;
            transition: .4s;
            border-radius: 50%;
        }
        input:checked + .slider { background-color: var(--brand-gold); }
        input:checked + .slider:before { transform: translateX(-30px); }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 20px;
            margin-bottom: 25px;
        }
        .stat-card {
            background: var(--card-bg);
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.02);
            border-right: 5px solid var(--brand-safari-green);
            text-align: center;
            transition: all 0.3s ease;
        }
        .stat-card h3 { font-size: 14px; color: var(--brand-charcoal); margin-bottom: 8px; }
        .stat-card .value { font-size: 24px; font-weight: 700; color: var(--brand-dark-green); }
        
        .mode-repeated {
            color: var(--brand-gold) !important;
            font-size: 25px !important;
        }

        .main-layout {
            display: grid;
            grid-template-columns: 1fr;
            gap: 25px;
        }
        .section-box {
            background: var(--card-bg);
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 3px 6px rgba(0,0,0,0.02);
            margin-bottom: 20px;
        }
        .section-title {
            font-size: 18px;
            color: var(--brand-dark-green);
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid var(--bg-primary);
        }

        /* كروت بوابة الأخصائي لتحديث البيانات  */
        .specialist-cards-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(310px, 1fr));
            gap: 20px;
            margin-top: 15px;
        }
        .specialist-live-card {
            background: white;
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 20px;
            border-top: 4px solid var(--brand-gold);
            box-shadow: 0 2px 5px rgba(0,0,0,0.01);
        }
        .specialist-live-card h4 {
            color: var(--brand-dark-green);
            font-size: 15px;
            margin-bottom: 8px;
            font-weight: 700;
        }
        .live-card-meta {
            font-size: 12px;
            color: var(--brand-charcoal);
            margin-bottom: 12px;
        }
        .live-input-group {
            margin-bottom: 12px;
        }
        .live-input-group label {
            display: block;
            font-size: 12px;
            font-weight: 600;
            color: var(--brand-dark-green);
            margin-bottom: 4px;
        }
        .live-input-group select {
            width: 100%;
            padding: 8px 10px;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
            outline: none;
        }
        .btn-submit-live {
            width: 100%;
            padding: 9px;
            background-color: var(--brand-safari-green);
            color: white;
            border: none;
            border-radius: 6px;
            font-weight: bold;
            cursor: pointer;
            font-size: 13px;
            transition: background 0.2s;
        }
        .btn-submit-live:hover { background-color: var(--brand-dark-green); }

        /* شريط نسبة الجاهزية الملون والمتحرك */
        .readiness-gauge-header {
            padding: 15px;
            border-radius: 10px;
            color: white;
            font-weight: bold;
            font-size: 18px;
            text-align: center;
            margin-bottom: 25px;
            text-shadow: 0 1px 2px rgba(0,0,0,0.15);
        }

        .gantt-chart-wrapper { overflow-x: auto; margin-top: 15px; }
        .gantt-container {
            min-width: 900px;
            display: flex;
            flex-direction: column;
            border: 1px solid var(--border-color);
            border-radius: 8px;
        }
        .gantt-header {
            display: flex;
            background-color: #f8faf9;
            font-weight: bold;
            border-bottom: 2px solid var(--border-color);
            text-align: center;
        }
        .gantt-row { display: flex; border-bottom: 1px solid var(--border-color); align-items: center; }
        .gantt-row:hover { background-color: #f3f7f4; }
        .gantt-label {
            width: 260px;
            padding: 12px;
            font-size: 13px;
            font-weight: 600;
            border-left: 1px solid var(--border-color);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .gantt-timeline-area { flex: 1; position: relative; height: 45px; display: flex; align-items: center; }
        .gantt-bar {
            height: 26px;
            border-radius: 15px;
            color: white;
            font-size: 11px;
            display: flex;
            align-items: center;
            padding: 0 12px;
            font-weight: 600;
            position: absolute;
            cursor: pointer;
        }
        .gantt-col-head { flex: 1; padding: 12px 5px; font-size: 12px; border-left: 1px solid var(--border-color); color: var(--brand-dark-green); }

        .table-container { overflow-x: auto; margin-top: 15px; }
        table { width: 100%; border-collapse: collapse; text-align: right; font-size: 14px; }
        th, td { padding: 12px 15px; border-bottom: 1px solid var(--border-color); }
        th { background-color: #f8faf9; color: var(--brand-dark-green); font-weight: 700; }
        
        .rep-badge {
            background-color: #fff3cd;
            color: #856404;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: bold;
            display: inline-block;
            margin-top: 4px;
        }

        /* تنسيقات شارات حالة الجاهزية */
        .status-badge {
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
            display: inline-block;
            text-align: center;
        }
        .status-not-started { background-color: #fee2e2; color: #991b1b; }
        .status-in-progress { background-color: #e0f2fe; color: #0369a1; }
        .status-completed { background-color: #dcfce7; color: #15803d; }
    </style>
</head>
<body>

    <div id="login-overlay">
        <div class="login-card">
            <img src="https://weqaa.gov.sa/web/image/website/1/header_logo/%D9%85%D8%B1%D9%83%D8%B2%20%D9%88%D9%82%D8%A7%D8%A1?unique=457fbf0" onerror="this.style.display='none';">
            <h2>بوابة الدخول للتنفيذيين</h2>
            <p>لوحة مؤشرات خطة البرامج التدريبية والميزانيات</p>
            
            <div class="login-field">
                <label for="username">اسم المستخدم:</label>
                <input type="text" id="username" placeholder="أدخل اسم المستخدم">
            </div>
            
            <div class="login-field">
                <label for="password">كلمة المرور:</label>
                <input type="password" id="password" placeholder="أدخل كلمة المرور">
            </div>
            
            <button class="btn-login" onclick="validateLogin()">تسجيل الدخول</button>
            <div id="login-error" class="error-message">⚠️ اسم المستخدم أو كلمة المرور غير صحيحة، يرجى المحاولة مرة أخرى.</div>
        </div>
    </div>

    <div id="main-dashboard-content">
        <div class="header-container">
            <div class="page-title-box">
                <h1>__DASHBOARD_TITLE__</h1>
                <p>الخطة الشاملة للمسارات التدريبية وفق وثيقة التدريب</p>
            </div>
            <div class="logo-area">
                <img src="https://weqaa.gov.sa/web/image/website/1/header_logo/%D9%85%D8%B1%D9%83%D8%B2%20%D9%88%D9%82%D8%A7%D8%A1?unique=457fbf0">
            </div>
        </div>

        <div class="portal-nav-tabs">
            <button class="portal-tab-btn active" id="btn-tab-dashboard" onclick="switchPortalTab('panel-dashboard')"><i class="fa-solid fa-chart-line"></i> لوحة المؤشرات والميزانيات </button>
            <button class="portal-tab-btn" id="btn-tab-readiness" onclick="switchPortalTab('panel-readiness')"><i class="fa-solid fa-layer-group"></i> لوحة الجاهزية العامة للحقائب التدريبية</button>
            <button class="portal-tab-btn" id="btn-tab-live" onclick="switchPortalTab('panel-live')"><i class="fa-solid fa-user-check"></i> بوابة تحديث البيانات  للأخصائيين</button>
        </div>

        <div id="panel-dashboard" class="portal-view-panel active">
            <div class="controls-wrapper">
                <div class="top-filters-container">
                    <div class="filter-group">
                        <label for="filter-year">📅 العام المستهدف:</label>
                        <select id="filter-year" onchange="applyFilters()">
                            <option value="all">كل الأعوام المستهدفة (2026 - 2028)</option>
                            <option value="2026">2026</option>
                            <option value="2027">2027</option>
                            <option value="2028">2028</option>
                        </select>
                    </div>
                    <div class="filter-group">
                        <label for="filter-quarter">⏱️ الربع السنوي الخاضع للتحليل:</label>
                        <select id="filter-quarter" onchange="applyFilters()">
                            <option value="all">كل الأرباع السنوية (الشامل)</option>
                            <option value="Q1">الربع الأول (Q1)</option>
                            <option value="Q2">الربع الثاني (Q2)</option>
                            <option value="Q3">الربع الثالث (Q3)</option>
                            <option value="Q4">الربع الرابع (Q4)</option>
                        </select>
                    </div>
                    <div class="filter-group">
                        <label for="filter-path">🎯 المسار التخصصي التدريبي:</label>
                        <select id="filter-path" onchange="applyFilters()"></select>
                    </div>
                    <div class="filter-group">
                        <label for="filter-type">⚙️ طريقة التنفيذ:</label>
                        <select id="filter-type" onchange="applyFilters()"></select>
                    </div>
                    <div class="filter-group">
                        <label for="search-program">🔍 بحث سريع باسم البرنامج:</label>
                        <input type="text" id="search-program" oninput="applyFilters()" placeholder="اكتب اسم البرنامج للبحث فورا...">
                    </div>
                </div>

                <div class="action-row-container">
                    <div class="toggle-container">
                        <label class="switch">
                            <input type="checkbox" id="toggle-reps" onchange="applyFilters()">
                            <span class="slider"></span>
                        </label>
                        <span class="toggle-label">     🔄 تفعيل احتساب المؤشرات بالتكرار </span>
                    </div>
                </div>
            </div>

            <div class="stats-grid">
                <div class="stat-card" style="border-right-color: var(--brand-dark-green);">
                    <h3 id="title-programs">إجمالي البرامج المدرجة</h3>
                    <div class="value" id="total-programs-kpi">0</div>
                </div>
                <div class="stat-card" style="border-right-color: var(--brand-gold);">
                    <h3 id="title-cost">إجمالي ميزانية التنفيذ (البرنامج)</h3>
                    <div class="value" id="total-cost-kpi">0 ⃁</div>
                </div>
                <div class="stat-card" style="border-right-color: var(--brand-charcoal);">
                    <h3 id="title-travel">تكاليف الانتداب والإركاب التقديري</h3>
                    <div class="value" id="total-travel-kpi">0 ⃁</div>
                </div>
                <div class="stat-card" style="border-right-color: var(--brand-safari-green);">
                    <h3>المجموع الكلي التقديري للميزانيات</h3>
                    <div class="value" id="grand-total-kpi">0 ⃁</div>
                </div>
            </div>

            <div class="main-layout">
                <div style="text-align: left; margin: 15px 20px;">
                    <button type="button" onclick="openBagsModal()" style="background-color: var(--brand-gold); color: white; border: none; padding: 10px 20px; font-size: 14px; font-weight: bold; border-radius: 6px; cursor: pointer; transition: background 0.3s;">
                        💼 المخطط الزمني ومواعيد الحقائب التفصيلية
                    </button>
                </div>

                <div id="bagsTimelineModal" style="display: none; position: fixed; z-index: 9999; left: 0; top: 0; width: 100%; height: 100%; overflow: auto; background-color: rgba(0,0,0,0.5);">
                    <div style="background-color: #fff; margin: 5% auto; padding: 25px; border-radius: 12px; width: 92%; max-width: 1300px; box-shadow: 0 5px 15px rgba(0,0,0,0.3); direction: rtl;">
                        
                        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #f1f5f9; padding-bottom: 15px; margin-bottom: 20px;">
                            <h2 style="margin: 0; color: var(--brand-dark-green); font-size: 20px; font-weight: bold;">🗓️ جدول المواعيد والمراحل التفصيلية لإعداد الحقائب التدريبية وجاهزيتها</h2>
                            <span onclick="closeBagsModal()" style="color: #aaa; font-size: 28px; font-weight: bold; cursor: pointer; transition: 0.2s;" onmouseover="this.style.color='#000'" onmouseout="this.style.color='#aaa'">&times;</span>
                        </div>

                        <div style="overflow-x: auto;">
                            <table style="width: 100%; border-collapse: collapse; text-align: right; font-size: 13px;">
                                <thead>
                                    <tr style="background-color: #f8fafc; border-bottom: 2px solid #e2e8f0;">
                                        <th style="padding: 12px; font-weight: bold; color: #334155; width: 28%;">اسم البرنامج التدريبي وتاريخ تنفيذه</th>
                                        <th style="padding: 12px; font-weight: bold; color: #334155; text-align: center; width: 20%;">مرحلة الإعداد والتطوير</th>
                                        <th style="padding: 12px; font-weight: bold; color: #334155; text-align: center; width: 20%;">مرحلة المراجعة والتدقيق</th>
                                        <th style="padding: 12px; font-weight: bold; color: #334155; text-align: center; width: 16%;">الاعتماد النهائي</th>
                                        <th style="padding: 12px; font-weight: bold; color: #334155; text-align: center; width: 16%;">حالة الجاهزية</th>
                                    </tr>
                                </thead>
                                <tbody id="bags-dynamic-rows"></tbody>
                            </table>
                        </div>
                    </div>
                </div>

                <div class="section-box">
                    <h2 class="section-title">📊 المخطط الزمني التفاعلي</h2>
                    <div class="gantt-chart-wrapper">
                        <div class="gantt-container" id="gantt-container-box"></div>
                    </div>
                </div>

                <div class="section-box">
                    <h2 class="section-title">🖨️ جدول البيانات والخطط التفصيلية (خيارات تتبع بنود الميزانية والتكرار)</h2>
                    <div class="table-container">
                        <table id="data-table-report">
                            <thead>
                                <tr>
                                    <th>اسم البرنامج التدريبي</th>
                                    <th>تاريخ البدء</th>
                                    <th>المسار التدريبي</th>
                                    <th>المدة / الموقع</th>
                                    <th>تكلفة التنفيذ (البرنامج)</th>
                                    <th>الإركاب والانتداب</th>
                                    <th>المجموع الكلي</th>
                                </tr>
                            </thead>
                            <tbody id="table-body-target"></tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        <div id="panel-readiness" class="portal-view-panel">
            <div class="controls-wrapper">
                <div class="top-filters-container">
                    <div class="filter-group">
                        <label for="ready-filter-year">📅 سنة خطة الجاهزية:</label>
                        <select id="ready-filter-year" onchange="calculateReadinessMetrics()">
                            <option value="all">كل الأعوام (2026 - 2028)</option>
                            <option value="2026">2026</option>
                            <option value="2027">2027</option>
                            <option value="2028">2028</option>
                        </select>
                    </div>
                    <div class="filter-group">
                        <label for="ready-filter-path">🎯 مسار الحقيبة التخصصي:</label>
                        <select id="ready-filter-path" onchange="calculateReadinessMetrics()"></select>
                    </div>
                    <div class="filter-group">
                        <label for="ready-search">🔍 تصفية سريعة بالاسم للحقائب:</label>
                        <input type="text" id="ready-search" oninput="calculateReadinessMetrics()" placeholder="اكتب اسم البرنامج...">
                    </div>
                </div>
            </div>

            <div id="ready-gauge-box" class="readiness-gauge-header">
                مؤشر الجاهزية العام للحقائب التدريبية الحالية: <span id="ready-percentage-span">0%</span>
            </div>

            <div class="stats-grid">
                <div class="stat-card" style="border-right-color: var(--success-green);">
                    <h3>حقائب جاهزة ومكتملة</h3>
                    <div class="value" id="ready-count-kpi">0</div>
                </div>
                <div class="stat-card" style="border-right-color: var(--warning-yellow);">
                    <h3>حقائب تحت التطوير والإعداد</h3>
                    <div class="value" id="dev-count-kpi">0</div>
                </div>
                <div class="stat-card" style="border-right-color: #0369a1;">
                    <h3>حقائب تحت المراجعة والتدقيق</h3>
                    <div class="value" id="review-count-kpi">0</div>
                </div>
                <div class="stat-card" style="border-right-color: var(--danger-red);">
                    <h3>إجمالي حقائب المسار </h3>
                    <div class="value" id="total-bags-kpi">0</div>
                </div>
            </div>

            <div class="section-box">
                <h2 class="section-title">💼 مصفوفة الحوكمة والمراحل الزمنية المباشرة للحقائب  </h2>
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>اسم البرنامج التدريبي المستهدف</th>
                                <th>المسار التخصصي</th>
                                <th>مرحلة التطوير والإعداد</th>
                                <th>تاريخ انتهاء المراجعة</th>
                                <th>الاعتماد النهائي</th>
                                <th>حالة الجاهزية الحالية</th>
                            </tr>
                        </thead>
                        <tbody id="ready-table-rows"></tbody>
                    </table>
                </div>
            </div>
        </div>

        <div id="panel-live" class="portal-view-panel">
            <div class="section-box" style="background:#fffbeb; border-right: 5px solid var(--brand-gold);">
                <h3 style="color:#856404; font-size:15px; margin-bottom:5px;"><i class="fa-solid fa-cloud-arrow-up"></i> بوابة التحديث الحي والتكامل مع المستند التشاركي:</h3>
                <p style="font-size:13px; color:#66511a;">تتيح هذه الشاشة للأخصائي تعديل "حالة الجاهزية" للبرامج التدريبية المكلف بها، وعند الضغط على حفظ يتم استدعاء دالة التكامل الفوري لعكس التغيير مباشرة على ملف الـ Google Sheet والمؤشرات التنفيذية.</p>
            </div>

            <div class="section-box" style="margin-top:15px;">
                <label style="font-weight:700; font-size:14px; display:block; margin-bottom:6px;">🔍 بحث سريع باسم البرنامج للوصول الفوري لبيانات الحقيبة التدريبية المكلف بها:</label>
                <input type="text" id="live-portal-search" oninput="renderSpecialistLivePortal()" placeholder="اكتب اسم البرنامج التدريبي المراد تحديثه ..." style="width:100%; padding:12px; border:1px solid var(--border-color); border-radius:8px; outline:none; font-size:14px;">
            </div>

            <div class="specialist-cards-grid" id="live-cards-container"></div>
        </div>
    </div>

    <script>
        const AUTH_CONFIG = {
            username: "admin",
            password: "weqaa2026"
        };

        // مصفوفة البيانات التشاركية الموحدة
        let trainingData = __DATA_PLACEHOLDER__;
        const pathColorsMap = {};
        const baseColors = ['#1d4229', '#29693b', '#b08932', '#420a70', '#4a4b4d', '#00a85a', '#cfa13a', '#5c1699'];

        function validateLogin() {
            const userInp = document.getElementById('username').value.trim();
            const passInp = document.getElementById('password').value;
            const errorDiv = document.getElementById('login-error');

            if (userInp === AUTH_CONFIG.username && passInp === AUTH_CONFIG.password) {
                document.getElementById('login-overlay').style.display = 'none';
                document.getElementById('main-dashboard-content').style.display = 'block';
                initApp();
            } else {
                errorDiv.style.display = 'block';
            }
        }

        document.getElementById('password').addEventListener('keyup', function(event) {
            if (event.key === 'Enter') validateLogin();
        });

        function switchPortalTab(panelId) {
            document.querySelectorAll('.portal-view-panel').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.portal-tab-btn').forEach(el => el.classList.remove('active'));
            
            document.getElementById(panelId).classList.add('active');
            if (panelId === 'panel-dashboard') document.getElementById('btn-tab-dashboard').classList.add('active');
            if (panelId === 'panel-readiness') document.getElementById('btn-tab-readiness').classList.add('active');
            if (panelId === 'panel-live') document.getElementById('btn-tab-live').classList.add('active');
        }

        function initApp() {
            const pathSelect = document.getElementById('filter-path');
            const readyPathSelect = document.getElementById('ready-filter-path');
            const uniquePaths = [...new Set(trainingData.map(item => item.path))];
            
            let pathOptions = '<option value="all">كل المسارات التدريبية</option>';
            let readyPathOptions = '<option value="all">كل مسارات الحقائب</option>';
            
            uniquePaths.forEach((path, index) => {
                pathColorsMap[path] = baseColors[index % baseColors.length];
                pathOptions += '<option value="' + path + '">' + path + '</option>';
                readyPathOptions += '<option value="' + path + '">' + path + '</option>';
            });
            
            pathSelect.innerHTML = pathOptions;
            readyPathSelect.innerHTML = readyPathOptions;

            const typeSelect = document.getElementById('filter-type');
            const uniqueTypes = [...new Set(trainingData.map(item => item.type))];
            let typeOptions = '<option value="all">كل طرق التنفيذ</option>';
            uniqueTypes.forEach(type => { typeOptions += '<option value="' + type + '">' + type + '</option>'; });
            typeSelect.innerHTML = typeOptions;

            applyFilters();
            calculateReadinessMetrics();
            renderSpecialistLivePortal();
        }

        function applyFilters() {
            const yearFilter = document.getElementById('filter-year').value;
            const quarterFilter = document.getElementById('filter-quarter').value;
            const pathFilter = document.getElementById('filter-path').value;
            const typeFilter = document.getElementById('filter-type').value;
            const searchQuery = document.getElementById('search-program').value.trim().toLowerCase();

            const filteredData = trainingData.filter(item => {
                const matchYear = (yearFilter === 'all' || item.year.toString() === yearFilter);
                const matchQuarter = (quarterFilter === 'all' || item.quarter === quarterFilter);
                const matchPath = (pathFilter === 'all' || item.path === pathFilter);
                const matchType = (typeFilter === 'all' || item.type === typeFilter);
                const matchSearch = (searchQuery === '' || item.name.toLowerCase().includes(searchQuery));
                return matchYear && matchQuarter && matchPath && matchType && matchSearch;
            });

            const isRepeatedMode = document.getElementById('toggle-reps').checked;

            updateKPIs(filteredData, isRepeatedMode);
            renderGanttChart(filteredData);
            renderReportTable(filteredData, isRepeatedMode);
            buildBagsDirectTimeline(filteredData);
        }

        function updateKPIs(data, useReps) {
            let totalPrograms = 0;
            let totalCost = 0;
            let totalTravel = 0;
            let grandTotal = 0;

            data.forEach(item => {
                const multiplier = useReps ? item.repetitions : 1;
                totalPrograms += item.repetitions;
                totalCost += (item.program_cost * multiplier);
                totalTravel += (item.travel_cost * multiplier);
                grandTotal += (item.grand_total * multiplier);
            });

            const kpiPrograms = document.getElementById('total-programs-kpi');
            const kpiCost = document.getElementById('total-cost-kpi');
            const kpiTravel = document.getElementById('total-travel-kpi');
            const kpiGrand = document.getElementById('grand-total-kpi');

            document.getElementById('title-programs').innerText = useReps ? "إجمالي البرامج (بالتكرار)" : "إجمالي البرامج المدرجة";
            document.getElementById('title-cost').innerText = useReps ? "إجمالي ميزانية التنفيذ (بالتكرار)" : "إجمالي ميزانية التنفيذ (البرنامج)";
            document.getElementById('title-travel').innerText = useReps ? "تكاليف الانتداب والإركاب (بالتكرار)" : "تكاليف الانتداب والإركاب التقديري";

            kpiPrograms.innerText = useReps ? totalPrograms : data.length;
            kpiCost.innerText = totalCost.toLocaleString('ar-SA') + ' ⃁';
            kpiTravel.innerText = totalTravel.toLocaleString('ar-SA') + ' ⃁';
            kpiGrand.innerText = grandTotal.toLocaleString('ar-SA') + ' ⃁';

            [kpiPrograms, kpiCost, kpiTravel, kpiGrand].forEach(el => {
                if (useReps) el.classList.add('mode-repeated');
                else el.classList.remove('mode-repeated');
            });
        }

        function renderGanttChart(data) {
            const container = document.getElementById('gantt-container-box');
            let htmlContent = '<div class="gantt-header">' +
                '<div class="gantt-label" style="background:#e8ede9;">اسم البرنامج التدريبي</div>' +
                '<div class="gantt-col-head">الربع الأول (Q1)</div>' +
                '<div class="gantt-col-head">الربع الثاني (Q2)</div>' +
                '<div class="gantt-col-head">الربع الثالث (Q3)</div>' +
                '<div class="gantt-col-head">الربع الرابع (Q4)</div>' +
                '</div>';

            if(data.length === 0) {
                htmlContent += '<div style="padding:20px; text-align:center; color:#94a3b8;">لا توجد برامج تدريبية تطابق خيارات التصفية الحالية</div>';
                container.innerHTML = htmlContent;
                return;
            }

            data.slice(0, 200).forEach(item => {
                let rightPercent = 0;
                let widthPercent = 21;

                if (item.quarter === 'Q1') rightPercent = 2;
                else if (item.quarter === 'Q2') rightPercent = 27;
                else if (item.quarter === 'Q3') rightPercent = 52;
                else if (item.quarter === 'Q4') rightPercent = 77;

                const barColor = pathColorsMap[item.path] || '#475569';

                htmlContent += '<div class="gantt-row">' +
                    '<div class="gantt-label" title="' + item.name + '">' + item.name + ' <span style="font-size:10px; color:var(--brand-gold);">[×' + item.repetitions + ']</span></div>' +
                    '<div class="gantt-timeline-area">' +
                    '<div class="gantt-bar" style="right: ' + rightPercent + '%; width: ' + widthPercent + '%; background-color: ' + barColor + ';" ' +
                    'title="المسار: ' + item.path + ' | التكرار: ' + item.repetitions + ' | المجموع الفرعي: ' + item.grand_total.toLocaleString('ar-SA') + ' ⃁">' +
                    item.path + ' (' + item.duration + ' أيام) - ' + item.type +
                    '</div>' +
                    '</div>' +
                    '</div>';
            });
            container.innerHTML = htmlContent;
        }

        function renderReportTable(data, useReps) {
            const tbody = document.getElementById('table-body-target');
            let tableHtml = '';

            data.forEach(item => {
                const clr = pathColorsMap[item.path] || '#333';
                const multiplier = useReps ? item.repetitions : 1;
                
                const pCost = item.program_cost * multiplier;
                const tCost = item.travel_cost * multiplier;
                const gTotal = item.grand_total * multiplier;

                tableHtml += '<tr>' +
                    '<td style="font-weight:600; color:var(--brand-dark-green);">' + item.name +  
                    '<br><span class="rep-badge">عدد التكرار المعتمد: ' + item.repetitions + '</span></td>' +
                    '<td>' + item.date + ' <span style="font-size:11px; color:var(--brand-charcoal); display:block; font-weight: bold;">' + item.quarter + '</span></td>' +
                    '<td><span style="color:' + clr + '; font-weight:bold;">●</span> ' + item.path + '</td>' +
                    '<td>' + item.duration + ' أيام <br><span style="font-size:11px; color:var(--brand-charcoal);">' + item.location + ' (' + item.type + ')</span></td>' +
                    '<td class="' + (useReps ? 'mode-repeated':'') + '">' + pCost.toLocaleString('ar-SA') + ' ⃁</td>' +
                    '<td class="' + (useReps ? 'mode-repeated':'') + '">' + tCost.toLocaleString('ar-SA') + ' ⃁</td>' +
                    '<td style="font-weight:700;" class="' + (useReps ? 'mode-repeated':'') + '">' + gTotal.toLocaleString('ar-SA') + ' ⃁</td>' +
                    '</tr>';
            });
            tbody.innerHTML = tableHtml || '<tr><td colspan="7" style="text-align:center; color:#94a3b8;">لا توجد بيانات متاحة للعرض حالياً</td></tr>';
        }

        function openBagsModal() { document.getElementById('bagsTimelineModal').style.display = 'block'; }
        function closeBagsModal() { document.getElementById('bagsTimelineModal').style.display = 'none'; }

        function buildBagsDirectTimeline(data) {
            const tbody = document.getElementById('bags-dynamic-rows');
            let rowsHtml = '';

            if(!data || data.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:30px; color:#94a3b8;">لا توجد برامج مطابقة للحقائب.</td></tr>';
                return;
            }

            data.forEach(item => {
                let statusClass = 'status-not-started';
                let statusText = item.readiness_status || 'لم تبدأ';
                
                if (statusText.includes('مكتمل') || statusText.includes('جاهز') || statusText.includes('تمت')) statusClass = 'status-completed';
                else if (statusText.includes('جاري') || statusText.includes('تحت')) statusClass = 'status-in-progress';

                rowsHtml += `<tr style="border-bottom: 1px solid #f1f5f9; vertical-align: middle;">
                    <td style="padding: 15px 12px;">
                        <div style="font-weight: 600; color: #1e293b; margin-bottom: 4px;">${item.name}</div>
                        <div style="color: var(--brand-safari-green); font-size: 12px; font-weight: bold;">📅 التنفيذ: ${item.date}</div>
                    </td>
                    <td style="padding: 15px 12px; text-align: center;">
                        <div style="font-size: 12px; margin-bottom: 4px;"><span style="color: #64748b;">البدء:</span> <span style="background: #f1f5f9; padding: 2px 6px; border-radius:4px; font-weight:600; color:#1e293b;">${item.bag_dev_start}</span></div>
                        <div style="font-size: 12px;"><span style="color: #64748b;">الانتهاء:</span> <span style="background: #f1f5f9; padding: 2px 6px; border-radius:4px; font-weight:600; color:#1e293b;">${item.bag_dev_end}</span></div>
                    </td>
                    <td style="padding: 15px 12px; text-align: center;">
                        <div style="font-size: 12px;"><span style="color: #b45309;">الانتهاء:</span> <span style="background: #fef3c7; padding: 2px 6px; border-radius:4px; font-weight:600; color:#b45309;">${item.bag_review_end}</span></div>
                    </td>
                    <td style="padding: 15px 12px; text-align: center;">
                        <div style="background: #f8fafc; border: 1px solid #e2e8f0; color: #334155; padding: 6px 12px; border-radius: 6px; font-weight: 600; display: inline-block;">${item.bag_approval}</div>
                    </td>
                    <td style="padding: 15px 12px; text-align: center;">
                        <span class="status-badge ${statusClass}">${statusText}</span>
                    </td>
                </tr>`;
            });
            tbody.innerHTML = rowsHtml;
        }

        // --- حساب فلاتر ومؤشرات شاشة لوحة الجاهزية العامة للحقائب التدريبية ---
        function calculateReadinessMetrics() {
            const yearFilter = document.getElementById('ready-filter-year').value;
            const pathFilter = document.getElementById('ready-filter-path').value;
            const searchKeyword = document.getElementById('ready-search').value.trim().toLowerCase();

            // لتكون اللوحة خاصة بالحقائب دون تكرار، نقوم بحصر الحقائب  أولاً بالاسم
            const uniqueMap = new Map();
            trainingData.forEach(item => { if(!uniqueMap.has(item.name)) uniqueMap.set(item.name, item); });
            const uniqueBags = Array.from(uniqueMap.values());

            const filteredBags = uniqueBags.filter(item => {
                const matchYear = (yearFilter === 'all' || item.year.toString() === yearFilter);
                const matchPath = (pathFilter === 'all' || item.path === pathFilter);
                const matchSearch = (searchKeyword === '' || item.name.toLowerCase().includes(searchKeyword));
                return matchYear && matchPath && matchSearch;
            });

            let readyCount = 0, devCount = 0, reviewCount = 0;
            const tbody = document.getElementById('ready-table-rows');
            let tableHtml = '';

            filteredBags.forEach(item => {
                let statusText = item.readiness_status || 'لم تبدأ';
                let sClass = 'status-not-started';

                if (statusText.includes('مكتمل') || statusText.includes('جاهز') || statusText.includes('تمت')) {
                    readyCount++;
                    sClass = 'status-completed';
                } else if (statusText.includes('جاري') || statusText.includes('تطوير')) {
                    devCount++;
                    sClass = 'status-in-progress';
                } else {
                    reviewCount++;
                }

                tableHtml += `<tr>
                    <td style="font-weight:600; color:var(--brand-dark-green);">${item.name}</td>
                    <td>${item.path}</td>
                    <td>${item.bag_dev_start} إلى ${item.bag_dev_end}</td>
                    <td>${item.bag_review_end}</td>
                    <td><div style="background:#f8fafc; padding:4px 8px; border-radius:4px; font-weight:600; display:inline-block;">${item.bag_approval}</div></td>
                    <td><span class="status-badge ${sClass}">${statusText}</span></td>
                </tr>`;
            });

            tbody.innerHTML = tableHtml || '<tr><td colspan="6" style="text-align:center; color:#94a3b8;">لا توجد حقائب تطابق خيارات التصفية الحالية</td></tr>';

            const total = filteredBags.length;
            const percentage = total > 0 ? Math.round((readyCount / total) * 100) : 0;

            document.getElementById('ready-count-kpi').innerText = readyCount;
            document.getElementById('dev-count-kpi').innerText = devCount;
            document.getElementById('review-count-kpi').innerText = reviewCount;
            document.getElementById('total-bags-kpi').innerText = total;

            // تحديث وتلوين مؤشر الجاهزية ديناميكياً (🔴 أقل من 60% | 🟡 من 60 إلى 80% | 🟢 أعلى من 80%)
            const gaugeBox = document.getElementById('ready-gauge-box');
            document.getElementById('ready-percentage-span').innerText = percentage + '%';
            if (percentage < 60) gaugeBox.style.backgroundColor = 'var(--danger-red)';
            else if (percentage <= 80) gaugeBox.style.backgroundColor = 'var(--warning-yellow)';
            else gaugeBox.style.backgroundColor = 'var(--success-green)';
        }

        // --- بناء بوابة الأخصائيين وتحديث البيانات التشاركية  ---
        function renderSpecialistLivePortal() {
            const container = document.getElementById('live-cards-container');
            const searchKeyword = document.getElementById('live-portal-search').value.trim().toLowerCase();
            container.innerHTML = '';

            // حصر البرامج  لتسهيل التحديث التشاركي ومنع تكرار الكروت لنفس البرنامج للأخصائي
            const uniquePortalMap = new Map();
            trainingData.forEach(item => { if(!uniquePortalMap.has(item.name)) uniquePortalMap.set(item.name, item); });
            let portalItems = Array.from(uniquePortalMap.values());

            if (searchKeyword) {
                portalItems = portalItems.filter(item => item.name.toLowerCase().includes(searchKeyword));
            }

            if(portalItems.length === 0) {
                container.innerHTML = '<div style="grid-column: 1/-1; text-align:center; padding:20px; color:#94a3b8;">لا توجد برامج مطابقة لبحث الأخصائي حالياً</div>';
                return;
            }

            portalItems.forEach(item => {
                container.innerHTML += `<div class="specialist-live-card">
                    <h4>${item.name}</h4>
                    <div class="live-card-meta">📅 تاريخ التنفيذ المعتمد بالخطة: ${item.date} <br> 🎯 المسار: ${item.path}</div>
                    <div class="live-input-group">
                        <label>حالة جاهزية الحقيبة الحالية:</label>
                        <select id="live-status-select-${item.id}">
                            <option value="لم تبدأ" ${item.readiness_status === 'لم تبدأ'?'selected':''}>لم تبدأ</option>
                            <option value="جاري التطوير والإعداد" ${item.readiness_status.includes('جاري')?'selected':''}>جاري التطوير والإعداد</option>
                            <option value="تحت المراجعة والتدقيق" ${item.readiness_status.includes('مراجعة')?'selected':''}>تحت المراجعة والتدقيق</option>
                            <option value="مكتمل وجاهز للتنفيذ" ${item.readiness_status.includes('مكتمل') || item.readiness_status.includes('جاهز')?'selected':''}>مكتمل وجاهز للتنفيذ</option>
                        </select>
                    </div>
                    <button class="btn-submit-live" onclick="submitSpecialistUpdate('${item.id}', '${item.name}')"><i class="fa-solid fa-cloud-arrow-up"></i> حفظ وتحديث مباشر</button>
                </div>`;
            });
        }

        // دالة الـ Web App التفاعلية المرتبطة بملف الإكسيل التشاركي وتحديث المؤشرات والذاكرة لحظياً
        function submitSpecialistUpdate(rowId, programName) {
            const selectEl = document.getElementById(`live-status-select-${rowId}`);
            const updatedStatus = selectEl.value;

            // 1. تحديث المصفوفة محلياً فوراً في الذاكرة لتتأثر باقي الشاشات
            trainingData.forEach(item => {
                if (item.name === programName) { item.readiness_status = updatedStatus; }
            });
            applyFilters();
            calculateReadinessMetrics();

            // 2. رابط الـ Web App الخاص بك
            const googleWebAppUrl = "https://script.google.com/macros/s/AKfycbyQei13DCLMNP0yyT16L-3x35VL19bSjErrsHWx764IBLef1mUvouOIsSq3aWZ_b5xs/exec";

            // 3. السطور المضافة لإرسال JSON بالمسميات المطابقة للـ Apps Script تماماً
            const payloadData = {
                program_name: programName,
                new_status: updatedStatus
            };

            fetch(googleWebAppUrl, {
                method: 'POST',
                mode: 'no-cors', // يتوافق مع قيود CORS لـ Google Apps Script
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payloadData)
            })
            .then(() => {
                alert(`✅ تم بث وتحديث [${programName}] بنجاح في ملف الاكسل التشاركي!`);
            })
            .catch(err => console.error("خطأ في الاتصال بالسيرفر السحابي:", err));
        }
    </script>
</body>
</html>
"""

    dashboard_title = "تقويم البرامج التدريبية التفاعلي ولوحة مؤشرات الميزانية (2026 - 2028)"
    final_html = html_template.replace("__DATA_PLACEHOLDER__", programs_json)
    final_html = final_html.replace("__DASHBOARD_TITLE__", dashboard_title)

    output_filename = "index.html"
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(final_html)
        
    print(f"\n✨ نجاح التطوير الهيكلي الموحد! تم إضافة 'لوحة الجاهزية العامة للحقائب' و 'بوابة تحديث البيانات ' بنجاح في ملف 'index.html'.")

if __name__ == "__main__":
    generate_interactive_calendar()
