"""
payroll_report_app.py — the quarter at a glance, for someone who never opens a terminal.

Every Friday since September the office manager at Salt City Coffee has downloaded
a payroll export from the Assignment 04 app; before that she typed the same file
by hand. The owner now wants to know where the hours went this quarter, the
accountant wants pay by month and department, and the manager wants to see who
has been missing shifts. This page answers all three from the pile of exports.

Same shape as Assignment 04: the page *assembles* the pipeline — one call to
`build_history` does the cleaning — and then shows the reports, filtered by the
department and dates the user picks.

Run it:  Run and Debug -> "Streamlit Run: Current File"
Test it: pytest tests/test_pipeline.py -k app
"""
import streamlit as st

from payroll import (
    build_history,
    hours_grid,
    load_employees,
    load_export,
    missed_weeks,
    pay_by_month,
    summarize_employees,
)


st.title("Salt City Coffee — Quarterly Payroll Report")
st.write("Upload weekly payroll exports to review hours, pay, and attendance.")

employees = load_employees()
uploads = st.file_uploader(
    "Payroll exports",
    type=["csv"],
    accept_multiple_files=True,
    key="exports",
)

if uploads:
    history = build_history([load_export(upload) for upload in uploads], employees)

    unmatched = history.loc[history["department"].isna(), "employeeid"].dropna()
    if not unmatched.empty:
        employee_ids = ", ".join(sorted(unmatched.astype(str).unique()))
        st.warning(
            "These employee IDs are not on the roster and are excluded from the "
            f"report: {employee_ids}"
        )

    history = history.loc[history["department"].notna()]
    dated_history = history.loc[history["pay_date"].notna()]

    if dated_history.empty:
        st.info("No rostered payroll rows with valid pay dates were found.")
    else:
        departments = ["All", *sorted(dated_history["department"].unique())]
        department = st.selectbox("Department", departments, key="department")

        first = dated_history["pay_date"].min().date()
        last = dated_history["pay_date"].max().date()
        dates = st.date_input(
            "Pay dates",
            value=(first, last),
            min_value=first,
            max_value=last,
            key="dates",
        )
        start, end = dates if len(dates) == 2 else (dates[0], dates[0])

        selected = dated_history.loc[
            dated_history["pay_date"].dt.date.between(start, end)
        ]
        if department != "All":
            selected = selected.loc[selected["department"] == department]

        st.subheader(f"{department} payroll: {start} to {end}")

        metrics = st.columns(4)
        metrics[0].metric("Weeks", f"{selected['week_ending'].nunique():,}")
        metrics[1].metric("Employees", f"{selected['employee_id'].nunique():,}")
        metrics[2].metric("Total hours", f"{selected['hours_worked'].sum():,.2f}")
        metrics[3].metric("Total gross pay", f"${selected['gross_pay'].sum():,.2f}")

        monthly = pay_by_month(selected)
        st.bar_chart(monthly, x="month")
        st.dataframe(summarize_employees(selected))

        grid = hours_grid(selected)
        st.dataframe(grid)
        st.dataframe(missed_weeks(grid))

        st.download_button(
            "Download monthly payroll CSV",
            data=monthly.to_csv(index=False),
            file_name="pay_by_month.csv",
            mime="text/csv",
            key="download",
        )
