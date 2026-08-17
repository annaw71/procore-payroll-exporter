import streamlit as st

st.title("Procore Payroll Exporter")

st.write("Pull Procore timesheet data and create a Sage 100 Contractor payroll import file.")

start_date = st.date_input("Pay Period Start")
end_date = st.date_input("Pay Period End")

if st.button("Pull Timesheets"):
    st.write("Eventually, Procore timesheet data will appear here.")