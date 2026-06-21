import os
import json
import pandas as pd
import requests
from io import BytesIO

def generate_interactive_calendar():
    # رابط جوجل شيت المباشر بصيغة إكسيل
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
            "id": str(len(programs_list)+1),
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

    # قالب واجهة الـ HTML المحدث بالكامل مع بوابه تسجيل الدخول والجدولة العكسية والمخطط الزمني
    html_template = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>داشبورد خطة إعداد الحقائب التدريبية</title>
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
            --brand-blue: #2b5c8f;
            
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

        .top-filters-container {
            background: linear-gradient(135deg, var(--brand-dark-green), var(--brand-safari-green));
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 4px 10px rgba(29, 66, 41, 0.15);
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            margin-bottom: 25px;
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
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 15px;
            margin-bottom: 25px;
        }
        .stat-card {
            background: var(--card-bg);
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.02);
            border-right: 5px solid var(--brand-safari-green);
            text-align: center;
        }
        .stat-card h3 { font-size: 14px; color: var(--brand-charcoal); margin-bottom: 8px; }
        .stat-card .value { font-size: 24px; font-weight: 700; color: var(--brand-dark-green); }

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

        .table-container { overflow-x: auto; margin-top: 15px; }
        table { width: 100%; border-collapse: collapse; text-align: right; font-size: 14px; }
        th, td { padding: 12px 15px; border-bottom: 1px solid var(--border-color); }
        th { background-color: #f8faf9; color: var(--brand-dark-green); font-weight: 700; }
        
        .timeline-bar-container {
            background-color: #e2e8f0;
            border-radius: 6px;
            position: relative;
            height: 24px;
            width: 100%;
            overflow: hidden;
            display: flex;
        }
        .timeline-segment {
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 11px;
            font-weight: bold;
        }
        .seg-dev { background-color: #2b5c8f; }
        .seg-review { background-color: #b08932; }
        .seg-approve { background-color: #29693b; }
        .seg-buffer { background-color: #a0aec0; color: #2d3748; }

        .date-badge {
            font-size: 12px;
            background-color: #edf2f7;
            padding: 2px 6px;
            border-radius: 4px;
            display: inline-block;
            margin-top: 3px;
            font-weight: 600;
        }
    </style>
</head>
<body>

    <div id="login-overlay">
        <div class="login-card">
            <h2>بوابة الدخول الموحدة</h2>
            <p>خطة أتمتة وجدولة الحقائب التدريبية العكسية</p>
            
            <div class="login-field">
                <label for="username">اسم المستخدم:</label>
                <input type="text" id="username" placeholder="أدخل اسم المستخدم">
            </div>
            
            <div class="login-field">
                <label for="password">كلمة المرور:</label>
                <input type="password" id="password" placeholder="أدخل كلمة المرور">
            </div>
            
            <button class="btn-login" onclick="validateLogin()">تسجيل الدخول</button>
            <div id="login-error" class="error-message">⚠️ البيانات غير صحيحة، يرجى المحاولة مرة أخرى.</div>
        </div>
    </div>

    <div id="main-dashboard-content">
        <div class="header-container">
            <div class="page-title-box">
                <h1>داشبورد الجدولة العكسية للحقائب التدريبية</h1>
                <p>نظام ذكي لاحتساب فترات التطوير، المراجعة، والاعتماد بناءً على تاريخ التنفيذ المستهدف مع استبعاد العطلات</p>
            </div>
        </div>

        <div class="top-filters-container">
            <div class="filter-group">
                <label for="filter-path">🎯 اختيار المسار التدريبي التخصصي:</label>
                <select id="filter-path" onchange="applyFilters()"></select>
            </div>
            <div class="filter-group">
                <label for="search-program">🔍 بحث سريع باسم البرنامج:</label>
                <input type="text" id="search-program" oninput="applyFilters()" placeholder="اكتب اسم البرنامج للبحث...">
            </div>
        </div>

        <div class="stats-grid">
            <div class="stat-card" style="border-right-color: var(--brand-dark-green);">
                <h3>إجمالي البرامج المدرجة في المسار</h3>
                <div class="value" id="total-programs-kpi">0</div>
            </div>
            <div class="stat-card" style="border-right-color: var(--brand-blue);">
                <h3>إجمالي أيام العمل اللازمة للإعداد</h3>
                <div class="value" id="total-days-kpi">0 يوم عمل</div>
            </div>
        </div>

        <div class="main-layout">
            <div class="section-box">
                <h2 class="section-title">📅 المخطط الزمني وجدول المواعيد التفصيلية لإعداد الحقائب (جدولة عكسية)</h2>
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th style="width: 25%;">اسم البرنامج التدريبي وتاريخ تنفيذه</th>
                                <th style="width: 20%;">مرحلة الإعداد والتطوير (10 أيام)</th>
                                <th style="width: 20%;">مرحلة المراجعة والتدقيق (5 أيام)</th>
                                <th style="width: 15%;">الاعتماد النهائي (يوم واحد)</th>
                                <th style="width: 20%;">توزيع الفترات التتابعية للحقيبة</th>
                            </tr>
                        </thead>
                        <tbody id="table-body-target"></tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <script>
        const AUTH_CONFIG = { username: "admin", password: "weqaa2026" };
        const trainingData = __DATA_PLACEHOLDER__;

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

        // دالة ترجع تاريخ بعد طرح عدد معين من أيام العمل الفعلي (باستثناء الجمعة والسبت)
        function subtractBusinessDays(startDate, daysToSubtract) {
            let currentDate = new Date(startDate);
            let subtractedDays = 0;
            while (subtractedDays < daysToSubtract) {
                currentDate.setDate(currentDate.getDate() - 1);
                let dayOfWeek = currentDate.getDay(); // 5 = الجمعة, 6 = السبت
                if (dayOfWeek !== 5 && dayOfWeek !== 6) {
                    subtractedDays++;
                }
            }
            return new Date(currentDate);
        }

        function formatDate(date) {
            let d = new Date(date),
                month = '' + (d.getMonth() + 1),
                day = '' + d.getDate(),
                year = d.getFullYear();
            if (month.length < 2) month = '0' + month;
            if (day.length < 2) day = '0' + day;
            return [year, month, day].join('-');
        }

        function initApp() {
            const pathSelect = document.getElementById('filter-path');
            const uniquePaths = [...new Set(trainingData.map(item => item.path))];
            let pathOptions = '<option value="all">كل المسارات التدريبية</option>';
            uniquePaths.forEach(path => {
                pathOptions += `<option value="${path}">${path}</option>`;
            });
            pathSelect.innerHTML = pathOptions;
            applyFilters();
        }

        function applyFilters() {
            const pathFilter = document.getElementById('filter-path').value;
            const searchQuery = document.getElementById('search-program').value.trim().toLowerCase();

            const filteredData = trainingData.filter(item => {
                const matchPath = (pathFilter === 'all' || item.path === pathFilter);
                const matchSearch = (searchQuery === '' || item.name.toLowerCase().includes(searchQuery));
                return matchPath && matchSearch;
            });

            document.getElementById('total-programs-kpi').innerText = filteredData.length;
            document.getElementById('total-days-kpi').innerText = (filteredData.length * 16) + " يوم عمل";

            renderTimelineTable(filteredData);
        }

        function renderTimelineTable(data) {
            const tbody = document.getElementById('table-body-target');
            let html = '';

            if (data.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;">لا توجد بيانات مطابقة للخيارات الحالية</td></tr>';
                return;
            }

            data.forEach(item => {
                let executionDate = new Date(item.date);
                
                // 1. مهلة الأمان قبل التنفيذ (5 أيام عمل على الأقل) -> نصل لتاريخ الاعتماد النهائي
                let approvalDeadline = subtractBusinessDays(executionDate, 5);
                
                // 2. مرحلة الاعتماد النهائي (يوم عمل واحد)
                let approvalStart = subtractBusinessDays(approvalDeadline, 1);
                
                // 3. مرحلة المراجعة والتدقيق (5 أيام عمل)
                let reviewEnd = approvalStart;
                let reviewStart = subtractBusinessDays(reviewEnd, 5);
                
                // 4. مرحلة إعداد الحقيبة (10 أيام عمل)
                let devEnd = reviewStart;
                let devStart = subtractBusinessDays(devEnd, 10);

                html += `<tr>
                    <td>
                        <strong>${item.name}</strong>
                        <div style="color: #c53030; font-size:12px; margin-top:4px;">📅 التنفيذ: ${item.date}</div>
                    </td>
                    <td>
                        <span style="color:#2b5c8f; font-weight:bold;">البدء:</span> <div class="date-badge">${formatDate(devStart)}</div> <br>
                        <span style="color:#2b5c8f; font-weight:bold;">الانتهاء:</span> <div class="date-badge">${formatDate(devEnd)}</div>
                    </td>
                    <td>
                        <span style="color:#b08932; font-weight:bold;">البدء:</span> <div class="date-badge">${formatDate(reviewStart)}</div> <br>
                        <span style="color:#b08932; font-weight:bold;">الانتهاء:</span> <div class="date-badge">${formatDate(reviewEnd)}</div>
                    </td>
                    <td>
                        <div class="date-badge" style="background-color:#c6f6d5; color:#22543d; font-weight:bold;">${formatDate(approvalDeadline)}</div>
                        <div style="font-size:10px; color:#4a5568; margin-top:2px;">(قبل التنفيذ بـ 5 أيام عمل)</div>
                    </td>
                    <td>
                        <div class="timeline-bar-container">
                            <div class="timeline-segment seg-dev" style="width: 50%;" title="إعداد الحقيبة: 10 أيام عمل">تطوير</div>
                            <div class="timeline-segment seg-review" style="width: 25%;" title="المراجعة: 5 أيام عمل">مراجعة</div>
                            <div class="timeline-segment seg-approve" style="width: 10%;" title="الاعتماد: يوم عمل">اعتماد</div>
                            <div class="timeline-segment seg-buffer" style="width: 15%;" title="مهلة الأمان: 5 أيام عمل">أمان</div>
                        </div>
                    </td>
                </tr>`;
            });

            tbody.innerHTML = html;
        }
    </script>
</body>
</html>
""".replace("__DATA_PLACEHOLDER__", programs_json)

    # حفظ ملف الداشبورد بصيغة HTML للتشغيل الفوري والتفاعلي الكامل
    output_filename = "interactive_backward_scheduling_dashboard.html"
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(html_template)
        
    print(f"✅ تم بنجاح إنتاج وتحديث الداشبورد التفاعلي وحفظه في: {output_filename}")

if __name__ == "__main__":
    generate_interactive_calendar()
