import io
import dateutil
import requests
import streamlit as st
import plotly.express as px
import pandas as pd
import warnings
import numpy as np
import plotly.graph_objs as go
from datetime import date

today = date.today()
COVID_CASES_DATASET = ["https://ckan0.cf.opendata.inter.prod-toronto.ca", {"id": "covid-19-cases-in-toronto"}]
OUTBREAK_CAREHOME_DATASET = ["https://ckan0.cf.opendata.inter.prod-toronto.ca", {"id": "outbreaks-in-toronto"
                                                                                       "-healthcare-institutions"}]

warnings.filterwarnings('ignore')

st.set_page_config(page_title="Our Healthcare Dashboard", page_icon=":bar_chart:", layout="wide")

st.title(" :bar_chart: Our Healthcare Dashboard")
st.info('This dashboard displays visualizations on outbreaks and Covid-19 data in care homes and other healthcare '
        'institutions.', icon="ℹ️")
st.markdown('<style>div.block-container{padding-top:1rem;}</style>', unsafe_allow_html=True)

def get_data(list_url_params):
    url = list_url_params[0] + "/api/3/action/package_show"
    package = requests.get(url, params=list_url_params[1]).json()
    df_list = []
    # To get resource data:
    for idx, resource in enumerate(package["result"]["resources"]):

        # for datastore_active resources:
        if resource["datastore_active"]:
            # To get all records in CSV format:
            url = list_url_params[0] + "/datastore/dump/" + resource["id"]
            resource_dump_data = requests.get(url).content
            c = pd.read_csv(io.StringIO(resource_dump_data.decode('utf-8')))
            if list_url_params[0] == OUTBREAK_CAREHOME_DATASET[0]:
                c.rename(
                    columns={"Causative Agent - 1": "Causative Agent-1", "Causative Agent - 2": "Causative Agent-2"},
                    inplace=True)
            df_list.append(c)
    dfs = pd.concat(df_list, ignore_index=True)
    return dfs


df_covid_cases = get_data(COVID_CASES_DATASET)
df_outbreaks_carehomes = get_data(OUTBREAK_CAREHOME_DATASET)
df_LTC_covid_summary = pd.read_csv("covidsummary.csv", encoding="ISO-8859-1")
df_LTC_vaccination_rates = pd.read_csv("ltc_immunization_data.csv", encoding="ISO-8859-1")

df_LTC_covid_summary.rename(columns={df_LTC_covid_summary.columns[0]: "Report Date"}, inplace=True)
df_LTC_vaccination_rates.rename(columns={df_LTC_vaccination_rates.columns[0]: "Report Date"}, inplace=True)
df_outbreaks_carehomes = df_outbreaks_carehomes.replace({'LTCH': 'Long-Term Care Home'}, regex=True)

col1, col2 = st.columns(2)
df_LTC_covid_summary["Report Date"] = pd.to_datetime(df_LTC_covid_summary["Report Date"])
df_LTC_vaccination_rates["Report Date"] = pd.to_datetime(df_LTC_vaccination_rates["Report Date"])
df_merged = df_LTC_covid_summary.merge(df_LTC_vaccination_rates, on='Report Date', how='left')

df_outbreaks_carehomes["Date Outbreak Began"] = pd.to_datetime(
    df_outbreaks_carehomes["Date Outbreak Began"])

filtered_df = df_outbreaks_carehomes

# Setting default start date to 2 months before most current date in dataset
endDateCarehomeData = pd.to_datetime(df_outbreaks_carehomes["Date Outbreak Began"]).max()
startDateCarehomeData = endDateCarehomeData - dateutil.relativedelta.relativedelta(months=2)
with col1:
    date1 = pd.to_datetime(st.date_input("Start Date", startDateCarehomeData))

with col2:
    date2 = pd.to_datetime(st.date_input("End Date", endDateCarehomeData))

mask = (filtered_df['Date Outbreak Began'] > date1) & (filtered_df['Date Outbreak Began'] <= date2)
df_filtered_by_date = filtered_df.loc[mask]

st.sidebar.header("Choose your filter: ")
# Create for Outbreak Setting
outbreak_setting = st.sidebar.radio("Select by Setting",
                                    np.append("--- View All ---", df_filtered_by_date["Outbreak Setting"].unique()),
                                    index=0,
                                    )
if not outbreak_setting or outbreak_setting == "--- View All ---":
    df_filtered_by_date = df_filtered_by_date.copy()
else:
    df_filtered_by_date = df_filtered_by_date[df_filtered_by_date["Outbreak Setting"] == outbreak_setting]

# Create for Institution Setting
institution_setting = st.sidebar.multiselect("Select by Location", df_filtered_by_date["Institution Name"].unique())
if not institution_setting:
    df_filtered_by_date = df_filtered_by_date.copy()
else:
    df_filtered_by_date = df_filtered_by_date[df_filtered_by_date["Institution Name"].isin(institution_setting)]

if not outbreak_setting and not institution_setting:
    df_filtered_by_date = df_filtered_by_date.copy()
elif outbreak_setting and institution_setting:
    df_filtered_by_date = df_filtered_by_date[
        (df_filtered_by_date["Outbreak Setting"] == outbreak_setting) & df_filtered_by_date["Institution Name"].isin(
            institution_setting)]

# Layout for Outbreak Type view data.
OutbreakType_ViewData_df = df_filtered_by_date.groupby(by=["Type of Outbreak"], as_index=False)[
    ['Type of Outbreak']].size().rename(columns={'size': 'Number of Outbreaks'})

# Layout for Causative Agent view data.
CausativeAgent_ViewData_df = df_filtered_by_date.groupby('Type of Outbreak')[
    'Causative Agent-1'].value_counts().reset_index(
    name='Number of Outbreaks')


def create_outbreaks_line_graph():
    st.subheader("Outbreaks Over Time")
    df_filtered_by_date['outbreak_count'] = df_filtered_by_date.groupby('Date Outbreak Began')[
        'Date Outbreak Began'].transform('count')

    df_outbreak_type_by_date = pd.pivot_table(df_filtered_by_date, values='outbreak_count',
                                              index=['Date Outbreak Began'],
                                              columns='Type of Outbreak')
    fig1 = px.line()
    for col in df_outbreak_type_by_date.columns:
        fig1.add_trace(go.Scatter(x=df_outbreak_type_by_date.index, y=df_outbreak_type_by_date[col].values,
                                  name=col,
                                  line=dict(shape='linear'),
                                  connectgaps=True,
                                  ))

    fig1['layout'].update(
        yaxis=dict(title="Number of Outbreaks", titlefont=dict(size=19)),
        margin=dict(l=10, r=10, t=30, b=20),
        hoverlabel=dict(
            bgcolor="white",
            font_color="black",
            font_size=15,
        ))
    fig1.update_traces(
        hovertemplate="<br>".join([
            "%{x}<br>" +
            "Number of Outbreaks: %{y}<extra></extra>"
        ]))

    st.plotly_chart(fig1, use_container_width=True, height=200)


def create_causative_agent_bar_graph():
    st.subheader("Causative Agent Per Outbreak Type")

    g = df_filtered_by_date.groupby('Type of Outbreak')['Causative Agent-1'].value_counts().reset_index(
        name='Number of Outbreaks')
    g['Percentage of Total Outbreaks'] = (g['Number of Outbreaks'] / g['Number of Outbreaks'].sum()) * 100

    fig2 = px.bar(g, x='Type of Outbreak', y='Number of Outbreaks', color="Causative Agent-1",
                  hover_name="Causative Agent-1",
                  hover_data={'Percentage of Total Outbreaks': ':.2f',
                              'Type of Outbreak': False,  # remove Type of Outbreak from hover data
                              'Causative Agent-1': False,
                              },
                  custom_data=['Percentage of Total Outbreaks', 'Causative Agent-1']
                  )
    fig2.update_traces(
        hovertemplate="<br>".join([
            "<b>%{customdata[1]}</b><br><br>"
            "Number of Outbreaks: %{y}<br>"
            "Percentage of Total Outbreaks: %{customdata[0]:.2f}% <extra></extra>",
        ])
    )

    fig2['layout'].update(
        xaxis={'categoryorder': 'total descending'},
        yaxis=dict(title="Total Outbreaks", titlefont=dict(size=19)),
        margin=dict(l=20, r=20, t=30, b=20),
        hoverlabel=dict(
            bgcolor="white",
            font_color="black",
            font_size=15,
        )

    )
    st.plotly_chart(fig2, use_container_width=True)


with col1:
    # Line chart for Active outbreak per outbreak type categories.
    create_outbreaks_line_graph()

with col2:
    # Bar chart for outbreak type categorized by causative agent.
    create_causative_agent_bar_graph()

cl1, cl2 = st.columns(2)

# Expander Outbreak Type View Data
with cl1:
    with st.expander("View Data (Outbreaks by Type)"):
        st.write(OutbreakType_ViewData_df.style.background_gradient(cmap="Blues"))
        csv = OutbreakType_ViewData_df.to_csv(index=False).encode('utf-8')
        st.download_button("Download Data", data=csv, file_name="OutbreakType.csv", mime="text/csv",
                           help='Click here to download the data as a CSV file')
# Causative Agent View Data
with cl2:
    with st.expander("View Data (Outbreaks by Causative Agent)"):
        st.write(CausativeAgent_ViewData_df.style.background_gradient(cmap="Oranges"))
        csv = CausativeAgent_ViewData_df.to_csv(index=False).encode('utf-8')
        st.download_button("Download Data", data=csv, file_name="CausativeAgents.csv", mime="text/csv",
                           help='Click here to download the data as a CSV file')


# line chart for various time series of Covid-19 data in Long term care homes
def load_time_series_graph():
    time_series_df = df_LTC_covid_summary
    time_series_df["month_year"] = time_series_df["Report Date"].dt.to_period("M")
    time_series_df2 = time_series_df
    text = ""
    st.subheader('Covid-19 Long Term Care Home Data from 2020 to 2023')
    options = ["Health Worker and Resident Cases", "Active Outbreaks", "Resident Deaths"]
    fig2 = px.line()
    sel_filter = st.selectbox('**Choose an option**', options)
    if sel_filter == options[1]:
        text = options[1]
        time_series_df = pd.DataFrame(time_series_df.groupby(time_series_df["month_year"].dt.strftime("%Y %b"))[
                                          "LTC_Homes_with_Active_Outbreak"].sum()).reset_index()
        fig2 = px.line(time_series_df, x="month_year", y="LTC_Homes_with_Active_Outbreak",
                       labels={"LTC_Homes_with_Active_Outbreak": "Active Outbreaks"}, height=500, width=1000,
                       template="gridon")
        fig2.update_traces(
            hovertemplate="<br>".join([
                "<b>%{x}</b><br>" +
                "Total Active Outbreaks: %{y}<extra></extra>"

            ]))
    elif sel_filter == options[2]:
        text = options[2]
        time_series_df["Daily Death Total"] = time_series_df.index
        time_series_df["Daily Death Total"] = (
                time_series_df['Total_LTC_Resident_Deaths'] - time_series_df['Total_LTC_Resident_Deaths'].shift())
        time_series_df3 = pd.DataFrame(time_series_df.groupby(time_series_df["month_year"].dt.strftime("%Y %b"))[
                                           "Daily Death Total"].sum())
        fig2 = px.line(time_series_df3,
                       labels={"value": "Resident Deaths"}, height=500, width=1000,
                       template="gridon")
        fig2.update_traces(
            hovertemplate="<br>".join([
                "<b>%{x}</b><br>" +
                "Total Resident Deaths: %{y}<extra></extra>"

            ]))
        fig2.update_layout(showlegend=False)

    elif sel_filter == options[0]:
        text = options[0]
        common_template = ('<b>%{customdata[0]} </b><br>' +
                           'Average Cases: %{customdata[1]:.0f}<br>'
                           )
        time_series_df = time_series_df.groupby(pd.PeriodIndex((time_series_df['month_year']), freq="M"))[
            'Confirmed_Active_LTC_HCW_Cases'].mean().rename('Average Health Worker Cases').reset_index()

        time_series_df2 = time_series_df2.groupby(pd.PeriodIndex((time_series_df2['month_year']), freq="M"))[
            'Confirmed_Active_LTC_Resident_Cases'].mean().rename('Average Resident Cases').reset_index()

        time_series_df['Average Resident Cases'] = \
            time_series_df2.groupby(pd.PeriodIndex((time_series_df['month_year']), freq="M"))[
                'Average Resident Cases'].transform('mean')

        time_series_df['month_year'] = time_series_df['month_year'].dt.strftime('%Y %b')
        time_series_df2['month_year'] = time_series_df2['month_year'].dt.strftime('%Y %b')

        fig2.add_trace(go.Scatter(
            x=time_series_df['month_year'],
            y=time_series_df['Average Health Worker Cases'],
            name="Health Workers",
            customdata=time_series_df,
            hovertemplate=common_template,

        ))
        fig2.add_trace(go.Scatter(
            x=time_series_df['month_year'],
            y=time_series_df['Average Resident Cases'],
            name="Residents",
            customdata=time_series_df2,
            hovertemplate=common_template,

        ))

    fig2['layout'].update(
        xaxis=dict(title="Date", titlefont=dict(size=19)),
        yaxis=dict(titlefont=dict(size=19)),
        margin=dict(l=20, r=20, t=30, b=20),
        hoverlabel=dict(
            bgcolor="white",
            font_color="black",
            font_size=15,
        ),

    )

    fig2.add_annotation(
        text=f"Ontario Long-Term Care Home COVID-19 Data (open.canada.ca) / {today}<br>Source: Government of Canada"
        , showarrow=False
        , x=0
        , y=-0.15
        , xref='paper'
        , yref='paper'
        , xanchor='left'
        , yanchor='bottom'
        , xshift=-10
        , yshift=-60
        , font=dict(size=10, color="grey")
        , align="left"
        ,
    )

    st.plotly_chart(fig2, use_container_width=True)

    with st.expander(("View Data (" + text + ")")):
        st.write(time_series_df.T.style.background_gradient(cmap="Blues"))
        csv = time_series_df.to_csv(index=False).encode("utf-8")
        st.download_button('Download Data', data=csv, file_name="TimeSeries.csv", mime='text/csv')


load_time_series_graph()


def load_outbreaks_by_institution():
    df_filtered_by_date['total_outbreak_institution'] = df_filtered_by_date.groupby('Institution Name')[
        'Institution Name'].transform('count')

    dfi = df_outbreaks_carehomes['Institution Name'].value_counts().to_frame().reset_index().rename(
        #columns={'index': 'Institution Name', 'Institution Name': 'total outbreaks'})
        columns={'outbreak count': 'Institution Name', 'count': 'total outbreaks'})

    fig = px.bar(dfi.head(20), x="total outbreaks", y="Institution Name", color="total outbreaks")
    #fig.update_traces(text=dfi["total outbreaks"])
    fig['layout'].update(
        title='Top 20 Outbreak Numbers by Institution <br>'
              '(2016-Present)',
        titlefont=dict(size=20),
        xaxis=dict(title="Total Outbreaks", titlefont=dict(size=19), visible=False),
        yaxis=dict(title="Institution Name", titlefont=dict(size=19), autorange='reversed'),
        margin=dict(l=20, r=20, t=100, b=20),

        hoverlabel=dict(
            bgcolor="white",
            font_color="black",
            font_size=15,
        ))
    fig.update_traces(
        hovertemplate="<br>".join([
            "%{y}<br>" +
            "<b>Total Outbreaks: %{x}</b><extra></extra>"

        ]))

    st.plotly_chart(fig, use_container_width=True)


def load_case_comparison_graph():
    # Create a scatter plot
    data1 = px.scatter(df_LTC_covid_summary, x="Confirmed_Active_LTC_Resident_Cases",
                       y="Confirmed_Active_LTC_HCW_Cases",
                       size="Total_LTC_Resident_Deaths")

    data1['layout'].update(
        title="Resident Covid-19 Cases and Resident Deaths",
        titlefont=dict(size=20), xaxis=dict(title="LTCH Resident Cases", titlefont=dict(size=19)),
        yaxis=dict(title="LTCH Healthcare Worker Cases", titlefont=dict(size=19)),
        margin=dict(l=20, r=20, t=100, b=20),

        hoverlabel=dict(
            bgcolor="white",
            font_color="black",
            font_size=15,
        ))
    st.plotly_chart(data1, use_container_width=True)


chart1, chart2 = st.columns(2)
# Bar chart for health care institution and total outbreaks
with chart1:
    load_outbreaks_by_institution()
# Bubble graph for comparing resident cases with health worker cases
with chart2:
    load_case_comparison_graph()


# Horizontal bar chart showing covid cases distribution with various filters
def update_covid_demographics_bar_chart():
    df2 = pd.DataFrame(df_covid_cases, columns=['Age Group', 'Assigned_ID', 'Client Gender', 'Source of Infection',
                                                'Ever Hospitalized'])
    options = ['Gender', 'Source of Infection', 'Hospitalizations']
    df2.rename(columns={'Client Gender': 'Gender'}, inplace=True)
    df2.rename(columns={'Client Gender': 'Gender'}, inplace=True)
    df2.rename(columns={'Ever Hospitalized': 'Hospitalizations'}, inplace=True)
    df2['Hospitalizations'].replace('Yes', 'Hospitalized', inplace=True)
    df2['Hospitalizations'].replace('No', 'Not Hospitalized', inplace=True)
    df2.drop(df2[df2['Source of Infection'] == 'No Information'].index, inplace=True)
    df2.drop(df2[df2['Source of Infection'] == 'Pending'].index, inplace=True)
    df2.drop(df2[df2['Gender'] == 'UNKNOWN'].index, inplace=True)
    df2.drop(df2[df2['Gender'] == 'NOT LISTED, PLEASE SPECIFY'].index, inplace=True)

    st.subheader("Covid-19 Case Distribution by Age (2020 to Present)")

    sel_filter = st.selectbox('**Choose an option**', options)
    df4 = (df2.groupby(['Age Group', sel_filter])['Assigned_ID']
           .count().unstack(sel_filter)
           )

    fig6 = px.bar(df4, orientation='h')
    for data in fig6.data:
        template = data.hovertemplate
        template = template.replace(sel_filter + "=", "<b>") \
            .replace("value=", "</b>Total Cases: ") \
            .replace("Age Group=", "Age Group: ")
        data.hovertemplate = template

    fig6['layout'].update(
        xaxis=dict(title="Number of Cases", titlefont=dict(size=19)),
        yaxis=dict(title="Age Group", titlefont=dict(size=19), autorange="reversed"),
        margin=dict(l=20, r=20, t=30, b=20),

        hoverlabel=dict(
            bgcolor="white",
            font_color="black",
            font_size=15,
        )

    )

    fig6.add_annotation(
        text=f"COVID-19 Cases in Toronto (open.toronto.ca) / {today}<br>Source: Toronto Public Health"
        , showarrow=False
        , x=0
        , y=-0.15
        , xref='paper'
        , yref='paper'
        , xanchor='left'
        , yanchor='bottom'
        , xshift=-75
        , yshift=-15
        , font=dict(size=10, color="grey")
        , align="left"
        ,
    )

    st.plotly_chart(fig6, use_container_width=True)


update_covid_demographics_bar_chart()
