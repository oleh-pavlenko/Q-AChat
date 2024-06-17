import streamlit as st
import pandas as pd
import json
import base64
from google.oauth2 import service_account
from google.cloud import storage

ENCODED_SERVICE_ACCOUNT_KEY = st.secrets['GCP_SERVICE_ACCOUNT']
BUCKET_NAME = st.secrets['GCP_BUCKET_NAME']
SERVICE_ACCOUNT_INFO = json.loads(base64.b64decode(ENCODED_SERVICE_ACCOUNT_KEY))

st.markdown("""
        <style>
               .block-container {
                    padding-top: 2rem;
                    padding-bottom: 2rem;
                    padding-left: 5rem;
                    padding-right: 5rem;
                }
                h1 {
                  text-align: center;
                  color: #4CAF50;
                }
                h3 {
                  color: #4CAF50;
                }
                [data-testid="stSidebar"] {
                    min-width: 400px;
                }
                [data-testid="stSidebarHeader"] {
                    padding: 1rem;
                }
                [data-testid="stSidebarUserContent"] {
                    padding-top: 0;
                }
        </style>
        """, unsafe_allow_html=True)

# Set the title of the application
st.title("Excel Data Q&A Application")

# Authenticate with Google Cloud Storage
@st.cache_resource
def get_gcs_client():
    credentials = service_account.Credentials.from_service_account_info(SERVICE_ACCOUNT_INFO)
    client = storage.Client(credentials=credentials)
    return client

client = get_gcs_client()
bucket = client.bucket(BUCKET_NAME)

# Function to upload file to Google Cloud Storage
def upload_to_gcs(file_name, file_data):
    blob = bucket.blob(file_name)
    blob.upload_from_file(file_data, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    blob.make_public()
    return blob.public_url

# Function to process the uploaded file and store it in the session state
def process_file():
    try:
        # Read the Excel file into a DataFrame
        df = pd.read_excel(st.session_state['file_uploader'])
        # Store the DataFrame in the session state
        st.session_state['data'] = df
        st.session_state['file_uploaded'] = True
        # Clear previous dialogue and reset system messages
        st.session_state['dialogue'] = []
        st.session_state['messages'] = [
            {"sender": "system", "text": "Your file has been uploaded successfully. You can now ask questions."}
        ]
        # Upload file to Google Cloud Storage
        st.session_state['file_uploader'].seek(0)
        file_url = upload_to_gcs(st.session_state['file_uploader'].name, st.session_state['file_uploader'])
        st.session_state['messages'].append(
            {"sender": "system", "text": f"File uploaded to Google Cloud Storage: {file_url}"}
        )
    except Exception as e:
        st.session_state['messages'].append(
            {"sender": "system", "text": f"Error processing file: {e}"}
        )

# Function to handle user questions and generate responses based on the data
def handle_question(question):
    df = st.session_state.get('data')
    if df is not None and question:
        # Example logic for handling questions (this should be replaced with actual logic)
        response = "Sorry, I can't answer that question."
        if "total sales" in question.lower():
            response = f"The total sales are {df['Sales Amount'].sum()}"
        elif "top products" in question.lower():
            top_products = df.nlargest(5, 'Sales Amount')[['Product Name', 'Sales Amount']]
            response = f"Top 5 products by revenue: {top_products.to_dict(orient='records')}"

        # Append the user question and system response to the dialogue
        st.session_state['dialogue'].append({"sender": "user", "text": question})
        st.session_state['dialogue'].append({"sender": "system", "text": response})
        del st.session_state['question_input']

# Initialize session state variables
if 'dialogue' not in st.session_state:
    st.session_state['dialogue'] = []
if 'file_uploaded' not in st.session_state:
    st.session_state['file_uploaded'] = False
if 'data' not in st.session_state:
    st.session_state['data'] = None
if 'messages' not in st.session_state:
    st.session_state['messages'] = [{"sender": "system", "text": "Please upload an Excel file to start."}]
if 'question_input' not in st.session_state:
    st.session_state['question_input'] = ""

# Use a sidebar for file upload section
st.sidebar.title("File Upload")
st.sidebar.file_uploader("Choose an Excel file", type=["xlsx"], on_change=process_file, key='file_uploader')

# Function to apply the desired style to the DataFrame
def style_dataframe(df):
    def highlight_odd_even(row):
        return ['background-color: #f9f9f9' if i % 2 == 0 else 'background-color: #f0f0f0' for i in range(len(row))]
    return df.style.apply(highlight_odd_even, axis=0)

# Display the table or data in the sidebar if file is uploaded
if st.session_state['file_uploaded']:
    styled_df = style_dataframe(st.session_state['data'])
    st.sidebar.dataframe(styled_df, height=500, width=500)

# Display system messages in the main section
for message in st.session_state['messages']:
    st.markdown(f"<div style='padding: 10px; border-radius: 5px; background-color: #E8F5E9; color: #1B5E20; margin-bottom: 8px;'>{message['text']}</div>", unsafe_allow_html=True)

# Display the chat interface in the main section
for message in st.session_state['dialogue']:
    if message["sender"] == "system":
        st.markdown(f"<div style='padding: 10px; border-radius: 5px; background-color: #E8F5E9; color: #1B5E20; margin-bottom: 8px;'>{message['text']}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div style='padding: 10px; border-radius: 5px; background-color: #E3F2FD; color: #0D47A1; margin-bottom: 8px;'><b>You:</b> {message['text']}</div>", unsafe_allow_html=True)

# Display the table or data in the main section if file is uploaded
if st.session_state['file_uploaded']:
    # Question input section
    st.text_input("Ask a question...", key='question_input')
    if st.button("Send"):
        handle_question(st.session_state['question_input'])
        st.rerun()
