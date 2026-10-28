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

# <table>ዎችን መፍጠር (ተማሪዎች እና አቴንዳንስ) - phone_number ተጨምሯል
c.execute(
    '''CREATE TABLE IF NOT EXISTS students (
             qr_code TEXT PRIMARY KEY, 
             full_name TEXT, 
             phone_number TEXT DEFAULT '',
             permission_type TEXT DEFAULT 'መደበኛ'
         )'''
)

# የድሮ ዳታቤዝ ካለ አምዶቹ በራሳቸው እንዲስተካከሉ
try:
  c.execute("ALTER TABLE students ADD COLUMN phone_number TEXT DEFAULT ''")
  conn.commit()
except sqlite3.OperationalError:
  pass

try:
  c.execute("ALTER TABLE students ADD COLUMN permission_type TEXT DEFAULT 'መደበኛ'")
  conn.commit()
except sqlite3.OperationalError:
  pass

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


# የፈረንጅ ቀንን ወደ ኢትዮጵያ ቀን መቀየሪያ ፊደል
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


# 1. የሎጊን ሲስተም (Owner, Admin እና Student/Member)
if 'logged_in' not in st.session_state:
  st.session_state.logged_in = False
  st.session_state.role = None

if not st.session_state.logged_in:
  st.title('⛪ የእመ ብዙኃን ሰንበት ትምህርት ቤት')
  st.subheader('የሰዓት መቆጣጠሪያ መተግበሪያ - ሎጊን')

  password = st.text_input('የመተግበሪያ መክፈቻ ቃለ-ይለፍ (ለአባላት ባዶውን ይተውት)', type='password')
  
  col_l1, col_l2 = st.columns(2)
  with col_l1:
    if st.button('እንደ ኦነር/አድሚን ግባ', use_container_width=True):
      if password == 'emet_owner2026':
        st.session_state.logged_in = True
        st.session_state.role = 'owner'
        st.rerun()
      elif password == 'emet_admin2026':
        st.session_state.logged_in = True
        st.session_state.role = 'admin'
        st.rerun()
      else:
        st.error('የገባው ቃለ-ይለፍ ስህተት ነው!')
  with col_l2:
    if st.button('🔍 እንደ አባል (ተማሪ) ሪፖርት ለማየት ግባ', use_container_width=True):
      st.session_state.logged_in = True
      st.session_state.role = 'student'
      st.rerun()
  st.stop()

# ሎጊን ከተደረገ በኋላ የሚታየው ዋና ምናኑ
st.sidebar.title('⛪ የእመ ብዙኃን ሰ/ት/ቤት')
if st.session_state.role == 'owner':
  role_display = 'ኦነር (Owner)'
elif st.session_state.role == 'admin':
  role_display = 'አድሚን (Admin)'
else:
  role_display = 'አባል / ተማሪ (Student)'

st.sidebar.write(f'የገቡበት አካውንት: **{role_display}**')

if st.session_state.role == 'owner':
  menu = st.sidebar.selectbox(
      'አማራጭ ይምረጡ',
      ['አቴንዳንስ መያዣ (Scan)', 'ተማሪዎችን መመዝገብ እና ማስተካከል', 'ሪፖርት እና ፐርሰንት ማውጫ'],
  )
elif st.session_state.role == 'admin':
  menu = 'አቴንዳንስ መያዣ (Scan)'
  st.sidebar.info('ℹ️ Admin ነዎት፤ የሚችሉት ስካን (አቴንዳንስ መያዝ) ብቻ ነው።')
else:
  menu = 'የግል አቴንዳንስ መመልከቻ'
  st.sidebar.info('ℹ️ የአባል ገጽ ነዎት፤ የራብዎን አቴንዳንስ ማየት ይችላሉ።')

st.sidebar.divider()
if st.sidebar.button('🚪 ውጣ (Logout)', use_container_width=True):
  st.session_state.logged_in = False
  st.session_state.role = None
  st.rerun()


# 2. የሰዓት እና ፈቃድ ማረጋገጫ ሎጂክ
def check_attendance_eligibility(permission_type):
  utc_now = datetime.datetime.utcnow()
  eat_now = utc_now + datetime.timedelta(hours=3)
  current_day = eat_now.strftime('%A')
  g_hour = eat_now.hour
  g_minute = eat_now.minute
  current_total_mins = g_hour * 60 + g_minute

  if current_day not in ['Tuesday', 'Saturday', 'Sunday']:
    return False, 'የፕሮግራም ቀን አይደለም'

  if permission_type == 'የሰዓት ፈቃድ' and current_day in ['Tuesday', 'Saturday']:
    if current_total_mins <= (19 * 60 + 40):
      return True, 'OK'
    else:
      return False, 'የሰዓት ፈቃድ ገደብ (ከ 1:40 ማታ) አልፏል!'

  if current_day == 'Tuesday':
    if (17 * 60 + 45) <= current_total_mins <= (18 * 60 + 20):
      return True, 'OK'
  elif current_day == 'Saturday':
    if (17 * 60 + 30) <= current_total_mins <= (18 * 60 + 5):
      return True, 'OK'
  elif current_day == 'Sunday':
    if (16 * 60 + 0) <= current_total_mins <= (17 * 60 + 0):
      return True, 'OK'

  return False, 'የመደበኛ ሰዓት ገደብ አልፏል!'


def auto_fill_past_leave(qr_code, permission_type, current_db_date):
  utc_now = datetime.datetime.utcnow()
  eat_now = utc_now + datetime.timedelta(hours=3)
  
  for i in range(1, 15):
    past_date_dt = eat_now - datetime.timedelta(days=i)
    past_db_date = past_date_dt.strftime('%Y-%m-%d')
    past_day_name = past_date_dt.strftime('%A')

    is_leave_day = False
    if past_day_name == 'Tuesday' and permission_type == 'ሙሉ ፈቃድ - ማክሰኞ':
      is_leave_day = True
    elif past_day_name == 'Saturday' and permission_type == 'ሙሉ ፈቃድ - ቅዳሜ':
      is_leave_day = True

    if is_leave_day:
      c.execute(
          'SELECT * FROM attendance WHERE qr_code = ? AND date = ?',
          (qr_code, past_db_date)
      )
      already_exists = c.fetchone()

      if not already_exists:
        c.execute(
            'INSERT INTO attendance (qr_code, date, time, day_name, status) VALUES (?, ?, ?, ?, ?)',
            (qr_code, past_db_date, 'ሙሉ ቀን', past_day_name, 'ፈቃድ')
        )
        conn.commit()


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
        'SELECT full_name, permission_type FROM students WHERE qr_code = ?', (qr_input,)
    )
    student = c.fetchone()

    if student:
      name, perm_type = student
      
      auto_fill_past_leave(qr_input, perm_type, db_date_str)
      is_eligible, msg = check_attendance_eligibility(perm_type)

      if is_eligible:
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
        st.error(f'❌ አልተፈቀደም! {msg}')
    else:
      st.error(
          '❌ ይህ QR ኮድ በስርዓቱ ውስጥ አልተመዘገበም! እባክዎ መጀመሪያ ተማሪውን ያስመዝግቡት።'
      )

elif menu == 'የግል አቴንዳንስ መመልከቻ':
  st.header('📊 የራሴን አቴንዳንስ መመልከቻ (የአባል ገጽ)')
  st.write('የQR ኮድ ቁጥርዎን ወይም ስምዎን በመጻፍ የተገኙበትን እና የፈቃድ መዝገብዎን ይመልከቱ።')

  search_input = st.text_input('የQR ኮድ ቁጥር ወይም ሙሉ ስም ይጻፉ')
  
  if search_input:
    c.execute(
        "SELECT qr_code, full_name, permission_type FROM students WHERE qr_code = ? OR full_name LIKE ?",
        (search_input, f'%{search_input}%')
    )
    student_info = c.fetchone()

    if student_info:
      s_qr, s_name, s_perm = student_info
      st.success(f'👤 ተማሪ: **{s_name}** (QR: {s_qr}) | የፈቃድ ዓይነት: **{s_perm}**')

      # የእሱን አቴንዳንስ ማምጣት
      att_query = """
          SELECT date as 'ቀን', time as 'ሰዓት', day_name as 'ዕለት', status as 'ሁኔታ'
          FROM attendance
          WHERE qr_code = ?
          ORDER BY date DESC
      """
      att_df = pd.read_sql_query(att_query, conn, params=(s_qr,))

      if not att_df.empty:
        st.subheader('📋 የመገኘት ታሪክዎ')
        st.dataframe(att_df, use_container_width=True)
      else:
        st.info('ℹ️ እስካሁን የተመዘገበ የመገኘት ታሪክ የለም።')
    else:
      st.error('❌ የተማሪው ስም ወይም የQR ኮድ አልተገኘም!')

elif menu == 'ተማሪዎችን መመዝገብ እና ማስተካከል' and st.session_state.role == 'owner':
  st.header('📝 ተማሪዎችን መመዝገብ፣ ማስተካከል እና መቆጣጠር')

  tab1, tab2 = st.tabs(['➕ አዲስ ተማሪ መመዝገብ', '✏️ ተማሪዎችን ማስተካከል / ማጥፋት'])

  with tab1:
    with st.form('student_form', clear_on_submit=True):
      reg_qr = st.text_input('የQR ኮድ ቁጥር (QR Code Number)')
      reg_name = st.text_input('የተማሪው ሙሉ ስም')
      reg_phone = st.text_input('ስልክ ቁጥር (Phone Number)')
      reg_perm = st.selectbox(
          'የፈቃድ ዓይነት ይምረጡ',
          [
              'መደበኛ',
              'የሰዓት ፈቃድ',
              'ሙሉ ፈቃድ - ማክሰኞ',
              'ሙሉ ፈቃድ - ቅዳሜ'
          ]
      )
      submitted = st.form_submit_button('ተማሪውን መዝግብ', use_container_width=True)

      if submitted:
        if reg_qr and reg_name:
          try:
            c.execute(
                'INSERT INTO students (qr_code, full_name, phone_number, permission_type) VALUES (?, ?, ?, ?)',
                (reg_qr, reg_name, reg_phone, reg_perm),
            )
            conn.commit()
            st.success(f'✅ {reg_name} በትክክል ተመዝግቧል!')
          except sqlite3.IntegrityError:
            st.error('❌ ይህ የQR ኮድ ቁጥር አስቀድሞ ተመዝግቧል!')
        else:
          st.warning('⚠️ እባክዎ ሁሉንም መረጃዎች በትክክል ይሙሉ!')

  with tab2:
    st.subheader('🔍 የተማሪ መረጃ ማስተካከያ እና መሰረዣ')
    
    search_query = st.text_input('ለማስተካከል የሚፈልጉትን የተማሪ ስም ወይም የQR ኮድ ይጻፉ')
    
    if search_query:
      c.execute(
          "SELECT qr_code, full_name, phone_number, permission_type FROM students WHERE qr_code LIKE ? OR full_name LIKE ?",
          (f'%{search_query}%', f'%{search_query}%')
      )
      matched_students = c.fetchall()

      if matched_students:
        for m_qr, m_name, m_phone, m_perm in matched_students:
          with st.expander(f'👤 {m_name} (QR: {m_qr})'):
            perm_options = [
                'መደበኛ',
                'የሰዓት ፈቃድ',
                'ሙሉ ፈቃድ - ማክሰኞ',
                'ሙሉ ፈቃድ - ቅዳሜ'
            ]
            default_idx = perm_options.index(m_perm) if m_perm in perm_options else 0

            with st.form(key=f'update_form_{m_qr}'):
              new_name = st.text_input('ሙሉ ስም ማስተካከያ', value=m_name)
              new_phone = st.text_input('ስልክ ቁጥር ማስተካከያ', value=str(m_phone))
              new_perm = st.selectbox('የፈቃድ ዓይነት ማስተካከያ', perm_options, index=default_idx)
              
              col_u1, col_u2 = st.columns(2)
              with col_u1:
                update_btn = st.form_submit_button('💾 መረጃውን አደስ (Update)', use_container_width=True)
              with col_u2:
                delete_btn = st.form_submit_button('🗑️ ተማሪውን ሰርዝ (Delete)', use_container_width=True)

              if update_btn:
                c.execute(
                    'UPDATE students SET full_name = ?, phone_number = ?, permission_type = ? WHERE qr_code = ?',
                    (new_name, new_phone, new_perm, m_qr)
                )
                conn.commit()
                st.success(f'✅ የ {new_name} መረጃ በተሳካ ሁኔታ ታድሷል!')
                st.rerun()

              if delete_btn:
                c.execute('DELETE FROM students WHERE qr_code = ?', (m_qr,))
                conn.commit()
                st.warning(f'⚠️ {m_name} ከሲስተሙ ተሰርዟል!')
                st.rerun()
      else:
        st.info('ማንም ተማሪ አልተገኘም።')

  st.divider()
  st.subheader('📋 አጠቃላይ የተመዘገቡ ተማሪዎች ዝርዝር')

  students_query = """
        SELECT qr_code as 'የQR ኮድ', 
               full_name as 'የተማሪው ሙሉ ስም', 
               phone_number as 'ስልክ ቁጥር',
               permission_type as 'የፈቃድ ዓይነት' 
        FROM students
    """
  students_df = pd.read_sql_query(students_query, conn)

  if not students_df.empty:
    st.dataframe(students_df, use_container_width=True)

    csv_data = students_df.to_csv(index=False).encode('utf-8-sig')

    st.download_button(
        label='📥 የተመዘገቡ ተማሪዎችን ዝርዝር ወደ Excel/CSV አውርድ',
        data=csv_data,
        file_name='Eme_Muhian_Registered_Students.csv',
        mime='text/csv',
        use_container_width=True,
    )
  else:
    st.info('ℹ️ እስካሁን የተመዘገበ ተማሪ የለም።')

elif menu == 'ሪፖርት እና ፐርሰንት ማውጫ' and st.session_state.role == 'owner':
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
                   s.phone_number as 'ስልክ ቁጥር',
                   s.permission_type as 'የፈቃድ ዓይነት',
                   COUNT(a.id) as 'የተገኘበት/በፈቃድ የተያዘ ብዛት'
            FROM students s
            LEFT JOIN attendance a ON s.qr_code = a.qr_code 
            AND a.date BETWEEN ? AND ? {day_filter}
            GROUP BY s.qr_code, s.full_name, s.phone_number, s.permission_type
        """
    df = pd.read_sql_query(
        query, conn, params=(str(start_date), str(end_date))
    )

    df['የተገኘበት ፐርሰንት (%)'] = (
        df['የተገኘበት/በፈቃድ የተያዘ ብዛት'] / total_sessions_input
    ) * 100
    df['የተገኘበት ፐርሰንት (%)'] = df['የተገኘበት ፐርሰንት (%)'].round(2)

    filtered_df = df[df['የተገኘበት ፐርሰንት (%)'] >= min_percentage]

    st.subheader(
        f'📋 ውጤት: {report_type} (ከ {min_percentage}% እና በላይ)'
    )
    st.dataframe(filtered_df, use_container_width=True)

    csv_report_data = filtered_df.to_csv(index=False).encode('utf-8-sig')

    st.download_button(
        label='📥 ሪፖርቱን ወደ Excel/CSV ፋይል አውርድ',
        data=csv_report_data,
        file_name=f'Eme_Muhian_Attendance_{report_type}_{start_date}_to_{end_date}.csv',
        mime='text/csv',
        use_container_width=True,
    )
