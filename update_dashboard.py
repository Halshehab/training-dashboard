import os
import json
import pandas as pd

def generate_interactive_calendar():
    # 🔗 ضع هنا رابط التحميل المباشر لملف الإكسيل التشاركي (OneDrive أو Google Drive)
    excel_url = "https://docs.google.com/spreadsheets/d/1_nm_fLhSDVNRnWgn-t7onJpabfbGenAX/export?format=xlsx" 
    sheet_name = "تقويم التدريب"
    
    print(f"🔄 جاري سحب وقراءة البيانات من المجلد التشاركي...")
    
    try:
        df = pd.read_excel(excel_url, sheet_name=sheet_name)
    except Exception:
        try:
            df = pd.read_excel(excel_url, sheet_name=0)
        except Exception as e:
            print(f"❌ فشلت قراءة ملف الإكسيل: {e}")
            return

    # تنظيف مسميات الأعمدة
    df.columns = df.columns.str.strip()
    
    rename_dict = {
        'التاريخ': 'Date', 'السنة': 'Year', 'الشهر': 'Month',
        'اسم البرنامج': 'Program_Name', 'المسار': 'Training_Path',
        'عدد الأيام': 'Duration_Days', 'عدد المتدربين': 'Target_Count',
        'طريقة التنفيذ': 'Type', 'الموقع': 'Location',
        'الفئة المستهدفة': 'Entity', 'تكلفة البرنامج': 'Program_Cost',  
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
    
    # الحفاظ على الدقة العشرية للميزانيات وحساب الكسور بدقة مالية
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

    if not os.path.exists("template.html"):
        print("❌ خطأ: لم يتم العثور على ملف template.html")
        return

    with open("template.html", "r", encoding="utf-8") as f:
        html_template = f.read()

    dashboard_title = "تقويم البرامج التدريبية التفاعلي ولوحة مؤشرات الميزانية (2026 - 2028)"
    final_html = html_template.replace("__DATA_PLACEHOLDER__", programs_json)
    final_html = final_html.replace("__DASHBOARD_TITLE__", dashboard_title)

    # حفظ الملف الناتج كـ index.html ليقرأه GitHub Pages مباشرة
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(final_html)
        
    print("✨ تم تحديث ملف index.html بنجاح بالبيانات الجديدة!")

if __name__ == "__main__":
    generate_interactive_calendar()
