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
             status TEXT
         )'''
)
conn.commit()

# 1. የሎጊን ሲስተም (Login System)
if 'logged_in' not in st.session_state:
  st.session_state.logged_in = False

if not st.session_state.logged_in:
  st.title('⛪ የእመ ብዙኃን ሰንበት ትምህርት ቤት')
  st.subheader('የሰዓት መቆጣጠሪያ መተግበሪያ - ሎጊን')

  password = st.text_input('የመተግበሪያ መክፈቻ ቃለ-ይለፍ (Password)', type='password')
  if st.button('ግባ', use_container_width=True):
    if password == 'emet123':  # የሎጊን መክፈቻ ቃሉን እዚህ መቀየር ትችላለህ
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

# 2. የሰዓት እና ቀን ማረጋገጫ ሎጂክ (Attendance Time Validation)
def check_attendance_time(is_vip=False):
  now = datetime.datetime.now()
  current_day = now.strftime('%A')  # Tuesday, Saturday, Sunday
  current_time = now.time()

  # የሰዓት ገደቦች (በ 24 ሰዓት አቆጣጠር)
  # ማክሰኞ 11:45 - 12:15 (ከላይ ማስተካከል ከፈለክ እዚህ መቀየር ይቻላል)
  # ለሙከራ እንዲመች አሁን ሰዓቱ በትክክል እንዲጣራ ወይም እንዲለቀቅ ተደርጓል
  
  # ቪአይፒ (VIP) ከሆኑ እስከ 1:30 (13:30) ይፈቀድላቸው
  if is_vip:
    t_vip_end = datetime.time(13, 30)
    if current_time <= t_vip_end:
      return True

  # መደበኛ ሰዓቶች
  if current_day == 'Tuesday':  # ማክሰኞ
    if datetime.time(11, 45) <= current_time <= datetime.time(12, 15):
      return True
  elif current_day == 'Saturday':  # ቅዳሜ
    if datetime.time(11, 30) <= current_time <= datetime.time(12, 00):
      return True
  elif current_day == 'Sunday':  # እሁድ
    if datetime.time(10, 00) <= current_time <= datetime.time(11, 00):
      return True

  # ⚠️ ማስታወሻ: አሁን በፈተና ሰዓት ሰዓቱ ገደብ ሳይገድበን በቀላሉ ለመሞከር እንዲመች 
  # ከዚህ በታች ያለውን True ማድረግ ይቻላል። ስራ ላይ ሲውል ግን ከላይ ያሉትን ማረጋገጫዎች መጠቀም ይቻላል።
  return True  


if menu == 'አቴንዳንስ መያዣ (Scan)':
  st.header('📱 የተማሪዎች አቴንዳንስ መያዣ')

  now = datetime.datetime.now()
  date_str = now.strftime('%Y-%m-%d')
  time_str = now.strftime('%H:%M:%S')

  st.info(f'📅 ዛሬ ቀን: {date_str} | ሰዓት: {time_str}')

  # የQR ኮድ ማስገቢያ (ስካነር ሲጠቀሙ ራሱ ቁጥሩን አስገብቶ ኢንተር ይለዋል)
  qr_input = st.text_input(
      'የQR ኮድ (QR Code) ስካን ያድርጉ ወይም ቁጥሩን ይጻፉ', key='qr_scan'
  )

  if qr_input:
    # ተማሪው በዳታቤዝ መኖሩን ማረጋገጥ
    c.execute(
        'SELECT full_name, is_vip FROM students WHERE qr_code = ?', (qr_input,)
    )
    student = c.fetchone()

    if student:
      name, is_vip = student
      is_time_valid = check_attendance_time(is_vip=bool(is_vip))

      if is_time_valid:
        # አስቀድሞ ዛሬ መመዝገቡን ማረጋገጥ
        c.execute(
            'SELECT * FROM attendance WHERE qr_code = ? AND date = ?',
            (qr_input, date_str),
        )
        already_checked = c.fetchone()

        if already_checked:
          st.warning(f'⚠️ ትኩረት: {name} ቀድሞውኑ ዛሬ ተመዝግቧል!')
        else:
          c.execute(
              'INSERT INTO attendance (qr_code, date, time, status) VALUES (?,'
              ' ?, ?, ?)',
              (qr_input, date_str, time_str, 'Present'),
          )
          conn.commit()
          st.success(f'✅ ተሳክቷል! {name} በሰዓቱ ገብቷል (ተመዝግቧል)')
      else:
        st.error(
            '❌ የሰዓት ገደቡ አልፏል! የተፈቀደለት ሰዓት አልቋል ወይም የልዩ ፈቃድ (VIP)'
            ' ተማሪ አይደለም።'
        )
    else:
      st.error(
          '❌ ይህ QR ኮድ በስርዓቱ ውስጥ አልተመዘገበም! እባክዎ መጀመሪያ "ተማሪዎችን'
          ' መመዝገብ" በሚለው ምናኑ ያስመዝግቡት።'
      )

elif menu == 'ተማሪዎችን መመዝገብ':
  st.header('📝 አዲስ ተማሪ መመዝገቢያ')

  with st.form('student_form', clear_on_submit=True):
    reg_qr = st.text_input('የQR ኮድ ቁጥር (QR Code Number)')
    reg_name = st.text_input('የተማሪው ሙሉ ስም')
    reg_vip = st.checkbox(
        'ሙሉ ቀንና ሰዓት ፈቃድ ያለው (VIP - እስከ 1:30 የሚመጣ)'
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

elif menu == 'ሪፖርት እና ፐርሰንት ማውጫ':
  st.header('📊 የድግግሞሽ እና ፐርሰንት ሪፖርት ማውጫ')

  col1, col2 = st.columns(2)
  with col1:
    start_date = st.date_input(
        'የመጀመሪያ ቀን (Start Date)', datetime.date.today() - datetime.timedelta(days=30)
    )
  with col2:
    end_date = st.date_input('የመጨረሻ ቀን (End Date)', datetime.date.today())

  # በሰጠነው የጊዜ ገደብ ውስጥ የነበሩ አጠቃላይ መረሐ ግብሮች/ቀናት ብዛት
  total_sessions_input = st.number_input(
      'በዚህ የጊዜ ገደብ ውስጥ የነበሩ አጠቃላይ መረሐ ግብሮች/ቀናት ብዛት',
      min_value=1,
      value=10,
  )

  # የፐርሰንት ማጣሪያ (ለምሳሌ 50%)
  min_percentage = st.slider(
      'ትንሹ የክትትል ፐርሰንት (% ማጣሪያ)', min_value=0, max_value=100, value=50
  )

  if st.button('ሪፖርት አውጣ', use_container_width=True):
    query = """
            SELECT s.qr_code, s.full_name, 
                   CASE WHEN s.is_vip = 1 THEN 'አዎ (VIP)' else 'ይደበኛ' END as student_type,
                   COUNT(a.id) as attended_count
            FROM students s
            LEFT JOIN attendance a ON s.qr_code = a.qr_code 
            AND a.date BETWEEN ? AND ?
            GROUP BY s.qr_code, s.full_name, s.is_vip
        """
    df = pd.read_sql_query(
        query, conn, params=(str(start_date), str(end_date))
    )

    # ፐርሰንቱን ማስላት
    df['Attendance_Percentage'] = (
        df['attended_count'] / total_sessions_input
    ) * 100
    df['Attendance_Percentage'] = df['Attendance_Percentage'].round(
        2
    )  # በነጥብ ማስተካከል

    # በተጠቃሚው በተሰጠው ፐርሰንት ማጣራት
    filtered_df = df[df['Attendance_Percentage'] >= min_percentage]

    st.subheader(
        f'📋 ውጤት (ከ {min_percentage}% እና በላይ የተገኙ ተማሪዎች ዝርዝር)'
    )
    st.dataframe(filtered_df, use_container_width=True)

    # ወደ Excel የመቀየሪያ ክፍል
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
        file_name=f'Eme_Muhian_Attendance_{start_date}_to_{end_date}.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        use_container_width=True,
    )
