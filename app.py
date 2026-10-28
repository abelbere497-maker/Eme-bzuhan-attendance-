import datetime
import sqlite3
import pandas as pd
import streamlit as st

# ገጹን ሰፊ እና ውብ እንዲሆን ማቀናበር
st.set_page_config(
    page_title='እመ ብዙኃን ሰ/ት/ቤት አቴንዳንስ', page_icon='⛪', layout='centered'
)

# የዳታቤዝ ማዋቀሪያ
conn = sqlite3.connect('attendance.db', check_same_thread=False)
c = conn.cursor()

# <table>ዎችን መፍጠር (ተማሪዎች እና አቴንዳንስ)
c.execute(
    '''CREATE TABLE IF NOT EXISTS students (
             qr_code TEXT PRIMARY KEY, 
             full_name TEXT, 
             is_vip INTEGER DEFAULT 0
         )'''
)

c.execute(
    '''CREATE TABLE IF NOT EXISTS attendance (
             id INTEGER PRIMARY KEY AUTOINCREMENT, 
             qr_code TEXT, 
             date TEXT, 
             time TEXT, 
             day_name TEXT,
             status TEXT
         )'''
)
conn.commit()


# የፈረንጅ ቀንን ወደ ኢትዮጵያ ቀን እና ሰዓት መቀየሪያ ፊደል (Function)
def convert_to_ethiopian(g_date_str):
  parts = g_date_str.split('-')
  g_year = int(parts[0])
  g_month = int(parts[1])
  g_day = int(parts[2])

  ym = g_month
  yy = g_year
  if ym < 3:
    yy -= 1
    ym += 12
  B = 0
  if yy > 1582 or (yy == 1582 and ym > 10) or (yy == 1582 and ym == 10 and g_day >= 15):
    A = yy // 100
    B = 2 - A + A // 4

  jd = int(365.25 * (yy + 4716)) + int(30.6001 * (ym + 1)) + g_day + B - 1524.5

  r = int(jd - 1724220.5) % 1461
  j = (r % 365) + 365 * (r // 1460)
  eth_year = 4 * (int(jd - 1724220.5) // 1461) + (r // 365) - (r // 1460) + 1
  eth_month = (j // 30) + 1
  eth_day = (j % 30) + 1

  months_amharic = [
      'መስከረም', 'ጥቅምት', 'ህዳር', 'ታህሳስ', 'ጥር', 'የካቲት', 
      'መጋቢት', 'ሚያዝያ', 'ግንቦት', 'ሰኔ', 'ሐምሌ', 'ነሐሴ', 'ጳጉሜ'
  ]
  
  if 1 <= eth_month <= 13:
    eth_month_name = months_amharic[eth_month - 1]
  else:
    eth_month_name = 'ጳጉሜ'

  return f'{eth_month_name} {eth_day}, {eth_year} ዓ.ም.'


def get_ethiopian_datetime():
  utc_now = datetime.datetime.utcnow()
  eat_now = utc_now + datetime.timedelta(hours=3)
  
  g_year = eat_now.year
  g_month = eat_now.month
  g_day = eat_now.day
  
  h = eat_now.hour
  m = eat_now.minute
  s = eat_now.second

  db_date_str = eat_now.strftime('%Y-%m-%d')
  eth_date_str = convert_to_ethiopian(db_date_str)
  day_name_en = eat_now.strftime('%A')

  eth_h = h - 6
  if eth_h <= 0:
    eth_h += 12
    period = 'ሌሊት' if 0 <= h < 6 else 'ማታ'
  else:
    if eth_h > 12:
      eth_h -= 12
    
    if 6 <= h < 12:
      period = 'ጠዋት'
    elif 12 <= h < 18:
      period = 'ከሰዓት'
    elif 18 <= h < 24:
      period = 'ማታ'
    else:
      period = 'ሌሊት'

  eth_time_str = f'{eth_h}:{m:02d}:{s:02d} {period}'

  return eth_date_str, eth_time_str, db_date_str, day_name_en


# 1. የሎጊን ሲስተም (Login System)
if 'logged_in' not in st.session_state:
  st.session_state.logged_in = False

if not st.session_state.logged_in:
  st.title('⛪ የእመ ብዙኃን ሰንበት ትምህርት ቤት')
  st.subheader('የሰዓት መቆጣጠሪያ መተግበሪያ - ሎጊን')

  password = st.text_input('የመተግበሪያ መክፈቻ ቃለ-ይለፍ (Password)', type='password')
  if st.button('ግባ', use_container_width=True):
    if password == 'emet123':
      st.session_state.logged_in = True
      st.rerun()
    else:
      st.error('የገባው ቃለ-ይለፍ ስህተት ነው! እባክዎ እንደገና ይሞክሩ።')
  st.stop()

# ሎጊን ከተደረገ በኋላ የሚታየው ዋና ምናኑ (Menu)
st.sidebar.title('⛪ የእመ ብዙኃን ሰ/ት/ቤት')
st.sidebar.write('የአቴንዳንስ መቆጣጠሪያ ሲስተም')
menu = st.sidebar.selectbox(
    'አማራጭ ይምረጡ',
    ['አቴንዳንስ መያዣ (Scan)', 'ተማሪዎችን መመዝገብ', 'ሪፖርት እና ፐርሰንት ማውጫ'],
)


# 2. የሰዓት እና ቀን ማረጋገጫ ሎጂክ
def check_attendance_time(is_vip=False):
  utc_now = datetime.datetime.utcnow()
  eat_now = utc_now + datetime.timedelta(hours=3)
  current_day = eat_now.strftime('%A')
  g_hour = eat_now.hour
  g_minute = eat_now.minute
  current_total_mins = g_hour * 60 + g_minute

  if current_day not in ['Tuesday', 'Saturday', 'Sunday']:
    return False

  if is_vip:
    if current_total_mins <= (19 * 60 + 30):
      return True
    else:
      return False

  if current_day == 'Tuesday':
    if (17 * 60 + 45) <= current_total_mins <= (18 * 60 + 15):
      return True
  elif current_day == 'Saturday':
    if (17 * 60 + 30) <= current_total_mins <= (18 * 60 + 0):
      return True
  elif current_day == 'Sunday':
    if (16 * 60 + 0) <= current_total_mins <= (17 * 60 + 0):
      return True

  return False


if menu == 'አቴንዳንስ መያዣ (Scan)':
  st.header('📱 የተማሪዎች አቴንዳንስ መያዣ')

  eth_date_str, eth_time_str, db_date_str, day_name_en = get_ethiopian_datetime()

  st.info(
      f'📅 የኢትዮጵያ ቀን: **{eth_date_str}** | ሰዓት: **{eth_time_str}**'
  )

  qr_input = st.text_input(
      'የQR ኮድ (QR Code) ስካን ያድርጉ ወይም ቁጥሩን ይጻፉ', key='qr_scan'
  )

  if qr_input:
    c.execute(
        'SELECT full_name, is_vip FROM students WHERE qr_code = ?', (qr_input,)
    )
    student = c.fetchone()

    if student:
      name, is_vip = student
      is_time_valid = check_attendance_time(is_vip=bool(is_vip))

      if is_time_valid:
        c.execute(
            'SELECT * FROM attendance WHERE qr_code = ? AND date = ?',
            (qr_input, db_date_str),
        )
        already_checked = c.fetchone()

        if already_checked:
          st.warning(f'⚠️ ትኩረት: {name} ቀድሞውኑ ዛሬ ተመዝግቧል!')
        else:
          c.execute(
              'INSERT INTO attendance (qr_code, date, time, day_name, status) VALUES (?, ?, ?, ?, ?)',
              (qr_input, db_date_str, eth_time_str, day_name_en, 'Present'),
          )
          conn.commit()
          st.success(f'✅ ተሳክቷል! {name} በሰዓቱ ገብቷል (ተመዝግቧል)')
      else:
        st.error(
            '❌ አልተፈቀደም! የመደበኛ ሰዓት ገደብ አልፏል፤ ወይም የልዩ ፈቃድ (VIP) ተማሪ ካልሆኑ በስተቀር ከሰዓት ውጪ መመዝገብ አይቻልም!'
        )
    else:
      st.error(
          '❌ ይህ QR ኮድ በስርዓቱ ውስጥ አልተመዘገበም! እባክዎ መጀመሪያ "ተማሪዎችን'
          ' መመዝገብ" በሚለው ምናኑ ያስመዝግቡት።'
      )

elif menu == 'ተማሪዎችን መመዝገብ':
  st.header('📝 አዲስ ተማሪ መመዝገቢያ እና የተመዝጋቢዎች ዝርዝር')

  with st.form('student_form', clear_on_submit=True):
    reg_qr = st.text_input('የQR ኮድ ቁጥር (QR Code Number)')
    reg_name = st.text_input('የተማሪው ሙሉ ስም')
    reg_vip = st.checkbox(
        'ሙሉ ቀንና ሰዓት ፈቃድ ያለው (VIP - እስከ 1:30 ማታ የሚመጣ)'
    )
    submitted = st.form_submit_button('ተማሪውን መዝግብ', use_container_width=True)

    if submitted:
      if reg_qr and reg_name:
        try:
          c.execute(
              'INSERT INTO students (qr_code, full_name, is_vip) VALUES (?, ?,'
              ' ?)',
              (reg_qr, reg_name, 1 if reg_vip else 0),
          )
          conn.commit()
          st.success(f'✅ {reg_name} በትክክል ተመዝግቧል!')
        except sqlite3.IntegrityError:
          st.error('❌ ይህ የQR ኮድ ቁጥር አስቀድሞ ተመዝግቧል!')
      else:
        st.warning('⚠️ እባክዎ ሁሉንም መረጃዎች በትክክል ይሙሉ!')

  st.divider()
  st.subheader('📋 አጠቃላይ የተመዘገቡ ተማሪዎች ዝርዝር')

  # የተመዘገቡትን ተማሪዎች ከዳታቤዝ ማምጣት
  students_query = """
        SELECT qr_code as 'የQR ኮድ', 
               full_name as 'የተማሪው ሙሉ ስም', 
               CASE WHEN is_vip = 1 THEN 'አዎ (VIP)' else 'መደበኛ' END as 'የተማሪው ዓይነት' 
        FROM students
    """
  students_df = pd.read_sql_query(students_query, conn)

  if not students_df.empty:
    st.dataframe(students_df, use_container_width=True)

    # ወደ Excel ፋይል መቀየሪያ
    def convert_students_to_excel(df_to_export):
      from io import BytesIO

      output = BytesIO()
      with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_to_export.to_excel(writer, index=False, sheet_name='Registered_Students')
      processed_data = output.getvalue()
      return processed_data

    excel_data = convert_students_to_excel(students_df)

    st.download_button(
        label='📥 የተመዘገቡ ተማሪዎችን ዝርዝር ወደ Excel አውርድ',
        data=excel_data,
        file_name='Eme_Muhian_Registered_Students.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        use_container_width=True,
    )
  else:
    st.info('ℹ️ እስካሁን የተመዘገበ ተማሪ የለም።')

elif menu == 'ሪፖርት እና ፐርሰንት ማውጫ':
  st.header('📊 የድግግሞሽ እና ፐርሰንት ሪፖርት ማውጫ')

  report_type = st.selectbox(
      'የሪፖርት ምድብ ይምረጡ',
      ['ማክሰኞ እና ቅዳሜ (አንድ ላይ)', 'እሁድ (ለብቻው)', 'ሁለቱንም አጠቃላይ']
  )

  col1, col2 = st.columns(2)
  with col1:
    start_date = st.date_input(
        'የመጀመሪያ ቀን (Start Date)', datetime.date.today() - datetime.timedelta(days=30)
    )
  with col2:
    end_date = st.date_input('የመጨረሻ ቀን (End Date)', datetime.date.today())

  total_sessions_input = st.number_input(
      'በዚህ የጊዜ ገደብ ውስጥ የነበሩ አጠቃላይ መረሐ ግብሮች/ቀናት ብዛት',
      min_value=1,
      value=10,
  )

  min_percentage = st.slider(
      'ትንሹ የክትትል ፐርሰንት (% ማጣሪያ)', min_value=0, max_value=100, value=50
  )

  if st.button('ሪፖርት አውጣ', use_container_width=True):
    if report_type == 'ማክሰኞ እና ቅዳሜ (አንድ ላይ)':
      day_filter = "AND a.day_name IN ('Tuesday', 'Saturday')"
    elif report_type == 'እሁድ (ለብቻው)':
      day_filter = "AND a.day_name = 'Sunday'"
    else:
      day_filter = ""

    query = f"""
            SELECT s.qr_code as 'የQR ኮድ', s.full_name as 'የተማሪው ሙሉ ስም', 
                   CASE WHEN s.is_vip = 1 THEN 'አዎ (VIP)' else 'መደበኛ' END as 'የተማሪው ዓይነት',
                   COUNT(a.id) as 'የተገኘበት ብዛት'
            FROM students s
            LEFT JOIN attendance a ON s.qr_code = a.qr_code 
            AND a.date BETWEEN ? AND ? {day_filter}
            GROUP BY s.qr_code, s.full_name, s.is_vip
        """
    df = pd.read_sql_query(
        query, conn, params=(str(start_date), str(end_date))
    )

    df['የተገኘበት ፐርሰንት (%)'] = (
        df['የተገኘበት ብዛት'] / total_sessions_input
    ) * 100
    df['የተገኘበት ፐርሰንት (%)'] = df['የተገኘበት ፐርሰንት (%)'].round(2)

    filtered_df = df[df['የተገኘበት ፐርሰንት (%)'] >= min_percentage]

    st.subheader(
        f'📋 ውጤት: {report_type} (ከ {min_percentage}% እና በላይ)'
    )
    st.dataframe(filtered_df, use_container_width=True)


    def convert_df_to_excel(df_to_export):
      from io import BytesIO

      output = BytesIO()
      with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_to_export.to_excel(writer, index=False, sheet_name='Attendance_Report')
      processed_data = output.getvalue()
      return processed_data


    excel_data = convert_df_to_excel(filtered_df)

    st.download_button(
        label='📥 ሪፖርቱን ወደ Excel ፋይል አውርድ',
        data=excel_data,
        file_name=f'Eme_Muhian_Attendance_{report_type}_{start_date}_to_{end_date}.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        use_container_width=True,
    )
