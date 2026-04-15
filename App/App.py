# NSP Resume Analyzer - AI-powered Resume Analysis Tool
# Built by Stuti Agrawal & Deepesh Mahawar

###### Packages Used ######
import streamlit as st
import pandas as pd
import base64, random
import time, datetime
import sqlite3
import os
import socket
import platform
import geocoder
import secrets
import io, random
import plotly.express as px
import plotly.graph_objects as go
from geopy.geocoders import Nominatim
from pdfminer.high_level import extract_text_to_fp
from pdfminer.layout import LAParams
from streamlit_tags import st_tags
from PIL import Image
from Courses import ds_course, web_course, android_course, ios_course, uiux_course, resume_videos, interview_videos
from resume_parser_lite import ResumeParser
import nltk
try:
    nltk.download('stopwords', quiet=True)
except:
    pass


###### Helper: PDF reader ######

def pdf_reader(file):
    output = io.StringIO()
    with open(file, 'rb') as f:
        extract_text_to_fp(f, output, laparams=LAParams(), output_type='text', codec='utf-8')
    return output.getvalue()


def show_pdf(file_path):
    with open(file_path, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="700" height="1000" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)


def course_recommender(course_list):
    st.subheader("**Courses & Certificates Recommendations 👨‍🎓**")
    c = 0
    rec_course = []
    no_of_reco = st.slider('Choose Number of Course Recommendations:', 1, 10, 5)
    random.shuffle(course_list)
    for c_name, c_link in course_list:
        c += 1
        st.markdown(f"({c}) [{c_name}]({c_link})")
        rec_course.append(c_name)
        if c == no_of_reco:
            break
    return rec_course


def get_csv_download_link(df, filename, text):
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">{text}</a>'
    return href


###### Database (SQLite) ######

DB_PATH = os.path.join(os.path.dirname(__file__), 'resume_analyzer.db')


def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_data (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            sec_token TEXT, ip_add TEXT, host_name TEXT, dev_user TEXT,
            os_name_ver TEXT, latlong TEXT, city TEXT, state TEXT, country TEXT,
            act_name TEXT, act_mail TEXT, act_mob TEXT,
            Name TEXT, Email_ID TEXT, resume_score TEXT,
            Timestamp TEXT, Page_no TEXT, Predicted_Field TEXT,
            User_level TEXT, Actual_skills TEXT, Recommended_skills TEXT,
            Recommended_courses TEXT, pdf_name TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_feedback (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            feed_name TEXT, feed_email TEXT,
            feed_score TEXT, comments TEXT, Timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()


def insert_data(sec_token, ip_add, host_name, dev_user, os_name_ver, latlong, city, state,
                country, act_name, act_mail, act_mob, name, email, res_score, timestamp,
                no_of_pages, reco_field, cand_level, skills, recommended_skills, courses, pdf_name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO user_data VALUES (
            NULL,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
        )
    """, (str(sec_token), str(ip_add), host_name, dev_user, os_name_ver, str(latlong),
          city, state, country, act_name, act_mail, act_mob, name, email,
          str(res_score), timestamp, str(no_of_pages), reco_field, cand_level,
          skills, recommended_skills, courses, pdf_name))
    conn.commit()
    conn.close()


def insertf_data(feed_name, feed_email, feed_score, comments, Timestamp):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO user_feedback VALUES (NULL,?,?,?,?,?)",
                (feed_name, feed_email, feed_score, comments, Timestamp))
    conn.commit()
    conn.close()


###### Page Config ######

st.set_page_config(
    page_title="Resume Analyser",
    page_icon='./Logo/recommend.png',
)


###### Main ######

def run():
    # Init DB
    init_db()

    # Logo & Sidebar
    try:
        img = Image.open('./Logo/RESUM.png')
        st.image(img)
    except Exception:
        st.title("🤖 Resume Analyser")

    st.sidebar.markdown("# Choose Something...")
    activities = ["User", "Feedback", "About", "Admin"]
    choice = st.sidebar.selectbox("Choose among the given options:", activities)
    link = '<b>Resume Analyser</b>'
    st.sidebar.markdown(link, unsafe_allow_html=True)

    ###### USER SIDE ######
    if choice == 'User':
        act_name = st.text_input('Name*')
        act_mail = st.text_input('Mail*')
        act_mob  = st.text_input('Mobile Number*')
        sec_token = secrets.token_urlsafe(12)
        host_name = socket.gethostname()
        ip_add = socket.gethostbyname(host_name)
        dev_user = os.getlogin()
        os_name_ver = platform.system() + " " + platform.release()

        # Geo location (graceful fallback)
        try:
            g = geocoder.ip('me')
            latlong = g.latlng
            geolocator = Nominatim(user_agent="http")
            location = geolocator.reverse(latlong, language='en')
            address = location.raw['address']
            city    = address.get('city', address.get('town', ''))
            state   = address.get('state', '')
            country = address.get('country', '')
        except Exception:
            latlong = city = state = country = 'N/A'

        st.markdown(
            "<h5 style='text-align: left; color: #021659;'>Upload Your Resume, And Get Smart Recommendations</h5>",
            unsafe_allow_html=True
        )
        pdf_file = st.file_uploader("Choose your Resume", type=["pdf"])

        if pdf_file is not None:
            with st.spinner('Hang On While We Cook Magic For You... 🔮'):
                time.sleep(2)

            save_image_path = './Uploaded_Resumes/' + pdf_file.name
            pdf_name = pdf_file.name
            os.makedirs('./Uploaded_Resumes', exist_ok=True)
            with open(save_image_path, "wb") as f:
                f.write(pdf_file.getbuffer())
            show_pdf(save_image_path)

            # Parse resume
            try:
                resume_data = ResumeParser(save_image_path).get_extracted_data()
            except Exception as e:
                st.error(f"Error parsing resume: {e}")
                resume_data = None

            if resume_data:
                resume_text = pdf_reader(save_image_path)

                # Validate extracted name — if too long it's the raw PDF blob
                raw_name = resume_data.get('name') or ''
                display_name = raw_name if (0 < len(raw_name) <= 60 and '\n' not in raw_name) else 'there'

                st.header("**Resume Analysis 🤘**")
                st.success("Hello " + display_name + "!")
                st.subheader("**Your Basic Info 👀**")
                try:
                    name_val    = raw_name if (0 < len(raw_name) <= 60) else 'Could not detect'
                    email_val   = resume_data.get('email', '') or 'Could not detect'
                    contact_val = resume_data.get('mobile_number', '') or 'Could not detect'
                    degree_raw  = resume_data.get('degree', [])
                    if isinstance(degree_raw, list):
                        degree_val = ', '.join(degree_raw) if degree_raw else 'N/A'
                    else:
                        degree_val = str(degree_raw) if degree_raw else 'N/A'
                    st.text('Name: '        + name_val)
                    st.text('Email: '       + email_val)
                    st.text('Contact: '     + contact_val)
                    st.text('Degree: '      + degree_val)
                    st.text('Resume pages: '+ str(resume_data.get('no_of_pages', 1)))
                except Exception:
                    pass



                # Experience level
                cand_level = ''
                if resume_data.get('no_of_pages', 1) < 1:
                    cand_level = "NA"
                    st.markdown("<h4 style='color: #d73b5c;'>You are at Fresher level!</h4>", unsafe_allow_html=True)
                elif any(k in resume_text for k in ['INTERNSHIP', 'INTERNSHIPS', 'Internship', 'Internships']):
                    cand_level = "Intermediate"
                    st.markdown("<h4 style='color: #1ed760;'>You are at intermediate level!</h4>", unsafe_allow_html=True)
                elif any(k in resume_text for k in ['EXPERIENCE', 'WORK EXPERIENCE', 'Experience', 'Work Experience']):
                    cand_level = "Experienced"
                    st.markdown("<h4 style='color: #fba171;'>You are at experience level!</h4>", unsafe_allow_html=True)
                else:
                    cand_level = "Fresher"
                    st.markdown("<h4 style='color: #fba171;'>You are at Fresher level!!</h4>", unsafe_allow_html=True)

                # Skills
                st.subheader("**Skills Recommendation 💡**")
                skills = resume_data.get('skills', [])
                keywords = st_tags(label='### Your Current Skills',
                                   text='See our skills recommendation below',
                                   value=skills, key='1  ')

                ds_keyword      = ['tensorflow', 'keras', 'pytorch', 'machine learning', 'deep learning', 'flask', 'streamlit']
                web_keyword     = ['react', 'django', 'node js', 'react js', 'php', 'laravel', 'magento', 'wordpress', 'javascript', 'angular js', 'c#', 'asp.net', 'flask']
                android_keyword = ['android', 'android development', 'flutter', 'kotlin', 'xml', 'kivy']
                ios_keyword     = ['ios', 'ios development', 'swift', 'cocoa', 'cocoa touch', 'xcode']
                uiux_keyword    = ['ux', 'adobe xd', 'figma', 'zeplin', 'balsamiq', 'ui', 'prototyping', 'wireframes']
                n_any           = ['english', 'communication', 'writing', 'microsoft office', 'leadership']

                recommended_skills = []
                reco_field = ''
                rec_course = ''

                for i in [s.lower() for s in skills]:
                    if i in ds_keyword:
                        reco_field = 'Data Science'
                        st.success("** Our analysis says you are looking for Data Science Jobs.**")
                        recommended_skills = ['Data Visualization', 'Predictive Analysis', 'Statistical Modeling', 'Data Mining', 'Clustering & Classification', 'Data Analytics', 'Quantitative Analysis', 'Web Scraping', 'ML Algorithms', 'Keras', 'Pytorch', 'Probability', 'Scikit-learn', 'Tensorflow', 'Flask', 'Streamlit']
                        st_tags(label='### Recommended skills for you.', text='Recommended skills generated from System', value=recommended_skills, key='2')
                        st.markdown("<h5 style='color: #1ed760;'>Adding this skills to resume will boost🚀 the chances of getting a Job</h5>", unsafe_allow_html=True)
                        rec_course = course_recommender(ds_course)
                        break
                    elif i in web_keyword:
                        reco_field = 'Web Development'
                        st.success("** Our analysis says you are looking for Web Development Jobs **")
                        recommended_skills = ['React', 'Django', 'Node JS', 'React JS', 'php', 'laravel', 'Magento', 'wordpress', 'Javascript', 'Angular JS', 'c#', 'Flask', 'SDK']
                        st_tags(label='### Recommended skills for you.', text='Recommended skills generated from System', value=recommended_skills, key='3')
                        st.markdown("<h5 style='color: #1ed760;'>Adding this skills to resume will boost🚀 the chances of getting a Job💼</h5>", unsafe_allow_html=True)
                        rec_course = course_recommender(web_course)
                        break
                    elif i in android_keyword:
                        reco_field = 'Android Development'
                        st.success("** Our analysis says you are looking for Android App Development Jobs **")
                        recommended_skills = ['Android', 'Android development', 'Flutter', 'Kotlin', 'XML', 'Java', 'Kivy', 'GIT', 'SDK', 'SQLite']
                        st_tags(label='### Recommended skills for you.', text='Recommended skills generated from System', value=recommended_skills, key='4')
                        st.markdown("<h5 style='color: #1ed760;'>Adding this skills to resume will boost🚀 the chances of getting a Job💼</h5>", unsafe_allow_html=True)
                        rec_course = course_recommender(android_course)
                        break
                    elif i in ios_keyword:
                        reco_field = 'IOS Development'
                        st.success("** Our analysis says you are looking for IOS App Development Jobs **")
                        recommended_skills = ['IOS', 'IOS Development', 'Swift', 'Cocoa', 'Cocoa Touch', 'Xcode', 'Objective-C', 'SQLite', 'Plist', 'StoreKit']
                        st_tags(label='### Recommended skills for you.', text='Recommended skills generated from System', value=recommended_skills, key='5')
                        st.markdown("<h5 style='color: #1ed760;'>Adding this skills to resume will boost🚀 the chances of getting a Job💼</h5>", unsafe_allow_html=True)
                        rec_course = course_recommender(ios_course)
                        break
                    elif i in uiux_keyword:
                        reco_field = 'UI-UX Development'
                        st.success("** Our analysis says you are looking for UI-UX Development Jobs **")
                        recommended_skills = ['UI', 'User Experience', 'Adobe XD', 'Figma', 'Zeplin', 'Balsamiq', 'Prototyping', 'Wireframes', 'Storyframes', 'Adobe Photoshop', 'Editing', 'Illustrator', 'After Effects', 'Premier Pro', 'Indesign', 'Wireframe', 'Solid', 'Grasp', 'User Research']
                        st_tags(label='### Recommended skills for you.', text='Recommended skills generated from System', value=recommended_skills, key='6')
                        st.markdown("<h5 style='color: #1ed760;'>Adding this skills to resume will boost🚀 the chances of getting a Job💼</h5>", unsafe_allow_html=True)
                        rec_course = course_recommender(uiux_course)
                        break
                    elif i in n_any:
                        reco_field = 'NA'
                        st.warning("** Currently our tool only predicts and recommends for Data Science, Web, Android, IOS and UI/UX Development**")
                        recommended_skills = ['No Recommendations']
                        st_tags(label='### Recommended skills for you.', text='Currently No Recommendations', value=recommended_skills, key='7')
                        st.markdown("<h5 style='color: #092851;'>Maybe Available in Future Updates</h5>", unsafe_allow_html=True)
                        rec_course = "Sorry! Not Available for this Field"
                        break

                # Resume Scoring
                st.subheader("**Resume Tips & Ideas 🥂**")
                resume_score = 0

                if 'Objective' in resume_text or 'Summary' in resume_text:
                    resume_score += 6
                    st.markdown("<h5 style='color: #1ed760;'>[+] Awesome! You have added Objective/Summary</h5>", unsafe_allow_html=True)
                else:
                    st.markdown("<h5 style='color: #000000;'>[-] Please add your career objective.</h5>", unsafe_allow_html=True)

                if any(k in resume_text for k in ['Education', 'School', 'College']):
                    resume_score += 12
                    st.markdown("<h5 style='color: #1ed760;'>[+] Awesome! You have added Education Details</h5>", unsafe_allow_html=True)
                else:
                    st.markdown("<h5 style='color: #000000;'>[-] Please add Education Details.</h5>", unsafe_allow_html=True)

                if any(k in resume_text for k in ['EXPERIENCE', 'Experience', 'WORK EXPERIENCE', 'Work Experience']):
                    resume_score += 16
                    st.markdown("<h5 style='color: #1ed760;'>[+] Awesome! You have added Experience</h5>", unsafe_allow_html=True)
                else:
                    st.markdown("<h5 style='color: #000000;'>[-] Please add Experience.</h5>", unsafe_allow_html=True)

                if any(k in resume_text for k in ['INTERNSHIP', 'INTERNSHIPS', 'Internship', 'Internships']):
                    resume_score += 6
                    st.markdown("<h5 style='color: #1ed760;'>[+] Awesome! You have added Internships</h5>", unsafe_allow_html=True)
                else:
                    st.markdown("<h5 style='color: #000000;'>[-] Please add Internships.</h5>", unsafe_allow_html=True)

                if any(k in resume_text for k in ['SKILLS', 'SKILL', 'Skills', 'Skill']):
                    resume_score += 7
                    st.markdown("<h5 style='color: #1ed760;'>[+] Awesome! You have added Skills</h5>", unsafe_allow_html=True)
                else:
                    st.markdown("<h5 style='color: #000000;'>[-] Please add Skills.</h5>", unsafe_allow_html=True)

                if any(k in resume_text for k in ['HOBBIES', 'Hobbies']):
                    resume_score += 4
                    st.markdown("<h5 style='color: #1ed760;'>[+] Awesome! You have added your Hobbies</h5>", unsafe_allow_html=True)
                else:
                    st.markdown("<h5 style='color: #000000;'>[-] Please add Hobbies.</h5>", unsafe_allow_html=True)

                if any(k in resume_text for k in ['INTERESTS', 'Interests']):
                    resume_score += 5
                    st.markdown("<h5 style='color: #1ed760;'>[+] Awesome! You have added your Interest</h5>", unsafe_allow_html=True)
                else:
                    st.markdown("<h5 style='color: #000000;'>[-] Please add Interests.</h5>", unsafe_allow_html=True)

                if any(k in resume_text for k in ['ACHIEVEMENTS', 'Achievements']):
                    resume_score += 13
                    st.markdown("<h5 style='color: #1ed760;'>[+] Awesome! You have added your Achievements</h5>", unsafe_allow_html=True)
                else:
                    st.markdown("<h5 style='color: #000000;'>[-] Please add Achievements.</h5>", unsafe_allow_html=True)

                if any(k in resume_text for k in ['CERTIFICATIONS', 'Certifications', 'Certification']):
                    resume_score += 12
                    st.markdown("<h5 style='color: #1ed760;'>[+] Awesome! You have added your Certifications</h5>", unsafe_allow_html=True)
                else:
                    st.markdown("<h5 style='color: #000000;'>[-] Please add Certifications.</h5>", unsafe_allow_html=True)

                if any(k in resume_text for k in ['PROJECTS', 'PROJECT', 'Projects', 'Project']):
                    resume_score += 19
                    st.markdown("<h5 style='color: #1ed760;'>[+] Awesome! You have added your Projects</h5>", unsafe_allow_html=True)
                else:
                    st.markdown("<h5 style='color: #000000;'>[-] Please add Projects.</h5>", unsafe_allow_html=True)

                st.subheader("**Resume Score 📝**")
                st.markdown("""
                    <style>
                        .stProgress > div > div > div > div { background-color: #d73b5c; }
                    </style>""", unsafe_allow_html=True)

                my_bar = st.progress(0)
                score = 0
                for percent_complete in range(resume_score):
                    score += 1
                    time.sleep(0.05)
                    my_bar.progress(percent_complete + 1)

                st.success('** Your Resume Writing Score: ' + str(score) + '**')
                st.warning("** Note: This score is calculated based on the content that you have in your Resume. **")

                ts = time.time()
                cur_date = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
                cur_time = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
                timestamp = str(cur_date + '_' + cur_time)

                try:
                    insert_data(str(sec_token), str(ip_add), host_name, dev_user, os_name_ver,
                                latlong, city, state, country, act_name, act_mail, act_mob,
                                resume_data.get('name', ''), resume_data.get('email', ''),
                                str(resume_score), timestamp, str(resume_data.get('no_of_pages', 1)),
                                reco_field, cand_level, str(resume_data.get('skills', [])),
                                str(recommended_skills), str(rec_course), pdf_name)
                except Exception as e:
                    st.warning(f"Data logging error (non-critical): {e}")

                st.header("**Bonus Video for Resume Writing Tips💡**")
                resume_vid = random.choice(resume_videos)
                st.video(resume_vid)

                st.header("**Bonus Video for Interview Tips💡**")
                interview_vid = random.choice(interview_videos)
                st.video(interview_vid)

                st.balloons()
            else:
                st.error('Something went wrong while parsing the resume..')

    ###### FEEDBACK ######
    elif choice == 'Feedback':
        ts = time.time()
        cur_date = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
        cur_time = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
        timestamp = str(cur_date + '_' + cur_time)

        with st.form("my_form"):
            st.write("Feedback form")
            feed_name  = st.text_input('Name')
            feed_email = st.text_input('Email')
            feed_score = st.slider('Rate Us From 1 - 5', 1, 5)
            comments   = st.text_input('Comments')
            Timestamp  = timestamp
            submitted  = st.form_submit_button("Submit")
            if submitted:
                insertf_data(feed_name, feed_email, feed_score, comments, Timestamp)
                st.success("Thanks! Your Feedback was recorded.")
                st.balloons()

        conn = get_connection()
        plotfeed_data = pd.read_sql("SELECT * FROM user_feedback", conn)
        conn.close()

        if not plotfeed_data.empty:
            labels = plotfeed_data.feed_score.unique()
            values = plotfeed_data.feed_score.value_counts()
            st.subheader("**Past User Rating's**")
            fig = px.pie(values=values, names=labels, title="Chart of User Rating Score From 1 - 5",
                         color_discrete_sequence=px.colors.sequential.Aggrnyl)
            st.plotly_chart(fig)

            conn2 = get_connection()
            plfeed_cmt_data = pd.read_sql("SELECT feed_name, comments FROM user_feedback", conn2)
            conn2.close()
            st.subheader("**User Comment's**")
            st.dataframe(plfeed_cmt_data, use_container_width=True)

    ###### ABOUT ######
    elif choice == 'About':
        st.subheader("**About The Tool - RESUME ANALYSER**")
        st.markdown('''
        <p align='justify'>
            A tool which parses information from a resume using natural language processing and finds the keywords,
            cluster them onto sectors based on their keywords. And lastly show recommendations, predictions,
            analytics to the applicant based on keyword matching.
        </p>
        <p align="justify">
            <b>How to use it: -</b><br/><br/>
            <b>User -</b><br/>
            In the Side Bar choose yourself as user and fill the required fields and upload your resume in pdf format.<br/>
            Just sit back and relax our tool will do the magic on its own.<br/><br/>
            <b>Feedback -</b><br/>
            A place where user can suggest some feedback about the tool.<br/><br/>
            <b>Admin -</b><br/>
            For login use <b>admin</b> as username and <b>admin@resume-analyzer</b> as password.<br/>
            It will load all the required stuffs and perform analysis.
        </p><br/>

        ''', unsafe_allow_html=True)

    ###### ADMIN ######
    else:
        st.success('Welcome to Admin Side')
        ad_user     = st.text_input("Username")
        ad_password = st.text_input("Password", type='password')

        if st.button('Login'):
            if ad_user == 'admin' and ad_password == 'admin@resume-analyzer':
                conn = get_connection()

                datanalys = pd.read_sql("SELECT ID, ip_add, resume_score, Predicted_Field, User_level, city, state, country FROM user_data", conn)
                values = datanalys.ID.count()
                st.success("Welcome Admin! Total %d " % values + " User's Have Used Our Tool :)")

                df = pd.read_sql("SELECT * FROM user_data", conn)
                st.header("**User's Data**")
                st.dataframe(df)
                st.markdown(get_csv_download_link(df, 'User_Data.csv', 'Download Report'), unsafe_allow_html=True)

                dff = pd.read_sql("SELECT * FROM user_feedback", conn)
                st.header("**User's Feedback Data**")
                st.dataframe(dff)

                if not dff.empty:
                    labels = dff.feed_score.unique()
                    values = dff.feed_score.value_counts()
                    st.subheader("**User Rating's**")
                    fig = px.pie(values=values, names=labels, title="Chart of User Rating Score From 1 - 5 🤗",
                                 color_discrete_sequence=px.colors.sequential.Aggrnyl)
                    st.plotly_chart(fig)

                if not datanalys.empty:
                    labels = datanalys.Predicted_Field.unique()
                    values = datanalys.Predicted_Field.value_counts()
                    st.subheader("**Pie-Chart for Predicted Field Recommendation**")
                    fig = px.pie(values=values, names=labels, title='Predicted Field according to the Skills 👽',
                                 color_discrete_sequence=px.colors.sequential.Aggrnyl_r)
                    st.plotly_chart(fig)

                    labels = datanalys.User_level.unique()
                    values = datanalys.User_level.value_counts()
                    st.subheader("**Pie-Chart for User's Experienced Level**")
                    fig = px.pie(values=values, names=labels, title="Pie-Chart for User's Experienced Level",
                                 color_discrete_sequence=px.colors.sequential.RdBu)
                    st.plotly_chart(fig)

                    labels = datanalys.resume_score.unique()
                    values = datanalys.resume_score.value_counts()
                    st.subheader("**Pie-Chart for Resume Score**")
                    fig = px.pie(values=values, names=labels, title='From 1 to 100 💯',
                                 color_discrete_sequence=px.colors.sequential.Agsunset)
                    st.plotly_chart(fig)

                conn.close()
            else:
                st.error("Wrong ID & Password Provided")


run()
