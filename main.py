import streamlit as st
import cv2
import easyocr
import numpy as np
import pandas as pd
import mysql.connector
import base64
from streamlit_option_menu import option_menu


st.set_page_config(page_title="TEXT EXTRACTOR",
                   layout="wide",
                   initial_sidebar_state="expanded",
                   )
st.markdown("<h1 style='text-align: center; color: red;'>Business Card Data Extraction</h1>", unsafe_allow_html=True)

# SETTING-UP BACKGROUND IMAGE
st.markdown(f""" 
            <style>
            .stApp {{
            background: #bba0db;
            background-size: cover;
            transition: background 0.5s ease;
            }}
            .stFileUploader label{{
            color: red;
        }}
            .stButton>button {{
            color: white;
            background-color: red;
        }}
            </style>
            """,unsafe_allow_html=True)

# Create an EasyOCR reader object
reader = easyocr.Reader(['en'])

# Define MySQL database connection details
db_host = 'localhost'
db_user = 'root'
db_password = 'root@1234'
db_name = 'Bcard_detail'

# Connect to the MySQL database
db_connection = mysql.connector.connect(
    host=db_host,
    user=db_user,
    password=db_password
)

# Create a cursor object to interact with the database
cursor = db_connection.cursor()
cursor.execute("CREATE DATABASE IF NOT EXISTS {}".format(db_name))
print('Database created successfully')
# Switching to the new database
cursor.execute("USE {}".format(db_name))

# Create the table if it doesn't exist
cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS business_cards (
        id INT AUTO_INCREMENT PRIMARY KEY,
        text VARCHAR(255) NOT NULL,
        image LONGBLOB NOT NULL,
        file_name VARCHAR(255) NOT NULL
    )
    """
)


options = option_menu(None, ["Upload File","View DataBase"],
                       default_index=0,
                       orientation="horizontal",
                       styles={"nav-link": {"font-size": "25px", "text-align": "centre", "margin": "0px", "--hover-color": "red", "transition": "color 0.3s ease, background-color 0.3s ease"},
                               "container" : {"max-width": "6000px", "padding": "10px", "border-radius": "5px"},
                               "nav-link-selected": {"background-color": "red", "color": "white"}})


edit_text=""
extracted_text = ""
if options=="Upload File":
    uploaded_file = st.file_uploader("Choose an image", type=["jpg", "jpeg", "png"])
    # Perform OCR and store extracted text and image in MySQL when the extraction button is clicked
    if uploaded_file is not None:
        #Display the uploaded image
        st.markdown("<h2 style='text-align: center; color: red;'>Uploaded Image</h2>", unsafe_allow_html=True)
        image = np.array(bytearray(uploaded_file.read()), dtype=np.uint8)
        img = cv2.imdecode(image, cv2.IMREAD_COLOR)
        st.image(img, channels="BGR")

        # Add an extraction button
        extraction_button = st.button("Extract Text")

        if extraction_button:
            with st.spinner("Please wait processing image..."):
                # Perform OCR on the image
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                blurred = cv2.GaussianBlur(gray, (5, 5), 0)
                _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
                results = reader.readtext(thresh)

                # Extract the text and store it in the database along with the image
                for result in results:
                    extracted_text += result[1] + "\n"

                # Convert the image to base64 string
                image_base64 = base64.b64encode(img).decode('utf-8')
                # Get the uploaded file name
                file_name = uploaded_file.name

        
                # Store the extracted text and image in the database
                cursor.execute("INSERT INTO business_cards (text, image, file_name) VALUES (%s, %s, %s)", (extracted_text, image.tobytes(), file_name))
                db_connection.commit()

                st.success("Text extracted and stored in the database successfully!")
                
    st.markdown("<h2 style='text-align: center; color: red;'>Extracted Data</h2>", unsafe_allow_html=True)     
    # Allow the user to edit the text
    edit_text = st.text_area("Extracted Text", value=extracted_text)

    # Retrieve the latest data from the database
    cursor.execute("SELECT id, text, image FROM business_cards ORDER BY id DESC LIMIT 1")
    data = cursor.fetchone()

    # Display the extracted text and image
    if data is not None:
        card_id = data[0]
        image_data = data[2]

        # Convert the image data to base64 format
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        # Update the text in the database when the user clicks the Update button
        update_button = st.button("Update")
        if update_button:
            cursor.execute("UPDATE business_cards SET text = %s WHERE id = %s", (edit_text, card_id))
            db_connection.commit()
            st.success("Text updated successfully!")

        if extracted_text!="":
            # Display the image
            st.image(image_data, channels="BGR")

if options=="View DataBase":
    st.markdown("<h2 style='text-align: center; color: red;'>Data Base</h2>", unsafe_allow_html=True) 
    col1,col2 = st.columns(2)
    # Execute the SQL query
    query = "SELECT file_name FROM business_cards"
    cursor.execute(query)
    # Fetch all the values from the column
    result = cursor.fetchall()
    column_values = [row[0] for row in result]
    with col1:
        selected_data=st.selectbox("List",column_values)
    flag=0
    if st.button("Delete Data"):
        cursor.execute("DELETE FROM business_cards WHERE file_name = %s LIMIT 1", (selected_data,))
        db_connection.commit()
        st.error("Data Deleted Refesh the Page")
        flag=1
    if flag!=1:
        cursor.execute("SELECT id, text, image FROM business_cards WHERE file_name = %s LIMIT 1", (selected_data,))
        data = cursor.fetchone()
        card_id = data[0]
        extracted_text = data[1]
        image_data = data[2]
        # Convert the image data to base64 format
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        edit_text = st.text_area("Text", value=extracted_text)
        if st.button("Update"):
            cursor.execute("UPDATE business_cards SET text = %s WHERE id = %s", (edit_text, card_id))
            db_connection.commit()
            st.success("Text updated successfully!")
        # Display the image
        st.image(image_data, channels="BGR")

# Close the cursor and database connection
cursor.close()
db_connection.close()