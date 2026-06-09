import os
import json
import pandas as pd
import requests
from io import BytesIO

def generate_interactive_calendar():
    # رابط جوجل شيت المباشر بصيغة إكسيل الذي زودتني به
    google_sheet_url = "https://docs.google.com/spreadsheets/d/1_nm_fLhSDVNRnWgn-t7onJpabfbGenAX/export?format=xlsx"
    sheet_name = "تقويم التدريب"
    
    print(f"🔄 جاري سحب البيانات حياً من رابط Google Sheet...")
    
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
    
    # خريطة لمطابقة الأعمدة بدقة
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
        'التكرارات': 'Repetitions'
    }
    
    df = df.rename(columns=rename_dict)
    
    # معالجة التواريخ والأرباع
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df['Year'] = df['Date'].dt.year.fillna(2026).astype(int)
    df['Month_Val'] = df['Date'].dt.month.fillna(1).astype(int)
    
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

    # تجهيز سجلات JSON
    programs_list = []
    for _, row in df.iterrows():
        date_str = row['Date'].strftime('%Y-%m-%d') if not pd.isnull(row['Date']) else f"{row['Year']}-01-01"
        prog_cost = float(row['Program_Cost'])
        trav_cost = float(row['Total_Travel_Cost'])
        
        program_item = {
            "id": str(row.get('م', len(programs_list)+1)),
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
            "grand_total": prog_cost + trav_cost
        }
        programs_list.append(program_item)

    programs_json = json.dumps(programs_list, ensure_ascii=False, indent=4)

    # قالب واجهة الـ HTML المعتمد من طرفكم
    html_template = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>__DASHBOARD_TITLE__</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700&display=swap" rel="stylesheet">
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
            min-width: 200px;
        }
        .filter-group label { 
            display: block; 
            font-size: 13px; 
            font-weight: 600; 
            margin-bottom: 6px; 
            color: #ffffff; 
        }
        .filter-group select {
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

        .toggle-container {
            display: flex;
            align-items: center;
            justify-content: flex-start;
            background-color: var(--card-bg);
            padding: 12px 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.02);
            border: 1px solid var(--border-color);
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
        }
        .section-title {
            font-size: 18px;
            color: var(--brand-dark-green);
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid var(--bg-primary);
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
    </style>
</head>
<body>

    <div class="header-container">
        <div class="page-title-box">
            <h1>__DASHBOARD_TITLE__</h1>
            <p>الخطة الشاملة للمسارات التدريبية وفق وثيقة التدريب</p>
        </div>
        <div class="logo-area">
            <img src="https://weqaa.gov.sa/web/image/website/1/header_logo/%D9%85%D8%B1%D9%83%D8%B2%20%D9%88%D9%82%D8%A7%D8%A1?unique=457fbf0" alt="شعار المركز" onerror="this.style.display='none';">
        </div>
    </div>

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
        </div>

        <div class="toggle-container">
            <label class="switch">
                <input type="checkbox" id="toggle-reps" onchange="applyFilters()">
                <span class="slider"></span>
            </label>
            <span class="toggle-label">     🔄 تفعيل احتساب المؤشرات بالتكرار </span>
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
            <h3 id="title-grand">المجموع الكلي التقديري للميزانيات</h3>
            <div class="value" id="grand-total-kpi">0 ⃁</div>
        </div>
    </div>

    <div class="main-layout">
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

    <script>
        const trainingData = __DATA_PLACEHOLDER__;
        const pathColorsMap = {};
        const baseColors = ['#1d4229', '#29693b', '#b08932', '#420a70', '#4a4b4d', '#00a85a', '#cfa13a', '#5c1699'];

        function initApp() {
            const pathSelect = document.getElementById('filter-path');
            const uniquePaths = [...new Set(trainingData.map(item => item.path))];
            let pathOptions = '<option value="all">كل المسارات التدريبية</option>';
            uniquePaths.forEach((path, index) => {
                pathColorsMap[path] = baseColors[index % baseColors.length];
                pathOptions += '<option value="' + path + '">' + path + '</option>';
            });
            pathSelect.innerHTML = pathOptions;

            const typeSelect = document.getElementById('filter-type');
            const uniqueTypes = [...new Set(trainingData.map(item => item.type))];
            let typeOptions = '<option value="all">كل طرق التنفيذ</option>';
            uniqueTypes.forEach(type => { typeOptions += '<option value="' + type + '">' + type + '</option>'; });
            typeSelect.innerHTML = typeOptions;

            applyFilters();
        }

        function applyFilters() {
            const yearFilter = document.getElementById('filter-year').value;
            const quarterFilter = document.getElementById('filter-quarter').value;
            const pathFilter = document.getElementById('filter-path').value;
            const typeFilter = document.getElementById('filter-type').value;

            const filteredData = trainingData.filter(item => {
                const matchYear = (yearFilter === 'all' || item.year.toString() === yearFilter);
                const matchQuarter = (quarterFilter === 'all' || item.quarter === quarterFilter);
                const matchPath = (pathFilter === 'all' || item.path === pathFilter);
                const matchType = (typeFilter === 'all' || item.type === typeFilter);
                return matchYear && matchQuarter && matchPath && matchType;
            });

            const isRepeatedMode = document.getElementById('toggle-reps').checked;

            updateKPIs(filteredData, isRepeatedMode);
            renderGanttChart(filteredData);
            renderReportTable(filteredData, isRepeatedMode);
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
            document.getElementById('title-grand').innerText = useReps ? "المجموع الكلي للميزانيات (بالتكرار)" : "المجموع الكلي التقديري للميزانيات";

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

        window.onload = initApp;
    </script>
</body>
</html>
"""

    dashboard_title = "تقويم البرامج التدريبية التفاعلي ولوحة مؤشرات الميزانية (2026 - 2028)"
    final_html = html_template.replace("__DATA_PLACEHOLDER__", programs_json)
    final_html = final_html.replace("__DASHBOARD_TITLE__", dashboard_title)

    # حفظ السجل النهائي باسم index.html ليعمل على خوادم الـ Pages مباشرة
    output_filename = "index.html"
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(final_html)
        
    print(f"\n✨ تم تحديث الملف وحقن البيانات الحية بنجاح عبر الرابط!")

if __name__ == "__main__":
    generate_interactive_calendar()
