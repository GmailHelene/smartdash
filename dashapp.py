import os
import json
from dash import dash_table
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from io import BytesIO
import re
import base64
from dash import html, dcc, Dash
from dash.dependencies import Output, Input
from google.analytics.data_v1beta import BetaAnalyticsDataClient, RunReportRequest, Dimension, DateRange, Metric  # type: ignore
import math
from dash import no_update

# Hent innholdet fra Streamlit Secrets
key_content = st.secrets["GOOGLE_APPLICATION_CREDENTIALS_CONTENT"]

# Konverter AttrDict til en vanlig Python-ordbok
key_content_dict = dict(key_content)

# Konverter innholdet til en JSON-streng
key_content_str = json.dumps(key_content_dict)

# Lagre innholdet midlertidig som en fil
with open("key.json", "w") as key_file:
    key_file.write(key_content_str)

# Sett miljøvariabelen for Google Analytics
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "key.json"

# Konfigurer siden
st.set_page_config(
    layout="wide",
    page_title="SmartDash",
    page_icon="🚀"  # eks. et alternativt emoji-ikon
)


# Google Analytics (frontend-script)
st.markdown("""
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-Q4PWWTXBB4"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-Q4PWWTXBB4');
</script>
""", unsafe_allow_html=True)

# Legg til CSS for å gjøre fanene scrollbare
st.markdown("""
    <style>
    div[data-testid="stTabs"] > div {
        overflow-x: auto;
        white-space: nowrap;
    }
    div[data-testid="stTabs"] button {
        flex-shrink: 0;
    }
    </style>
""", unsafe_allow_html=True)

# Forbedret CSS for horisontal scrollbar
st.markdown("""
    <style>
    div[data-testid="stTabs"] > div {
        overflow-x: auto;
        white-space: nowrap;
        scrollbar-width: thin; /* For smal scrollbar */
        scrollbar-color: #007bff #e6e6e6; /* Farge på scrollbar */
    }
    div[data-testid="stTabs"]::-webkit-scrollbar {
        height: 8px; /* Høyde på scrollbar */
    }
    div[data-testid="stTabs"]::-webkit-scrollbar-thumb {
        background-color: #007bff; /* Farge på scrollbar-tommel */
        border-radius: 10px; /* Runde kanter */
    }
    div[data-testid="stTabs"]::-webkit-scrollbar-track {
        background: #e6e6e6; /* Bakgrunnsfarge for scrollbar */
    }
    div[data-testid="stTabs"] button {
        flex-shrink: 0;
    }
    </style>
""", unsafe_allow_html=True)

# Forbedret CSS for horisontal scrollbar kun for fanene
st.markdown("""
    <style>
    div[data-testid="stTabs"] > div {
        overflow-x: auto;
        white-space: nowrap;
        scrollbar-width: thin; /* For smal scrollbar */
        scrollbar-color: #007bff #e6e6e6; /* Farge på scrollbar */
    }
    div[data-testid="stTabs"]::-webkit-scrollbar {
        height: 8px; /* Høyde på scrollbar */
    }
    div[data-testid="stTabs"]::-webkit-scrollbar-thumb {
        background-color: #007bff; /* Farge på scrollbar-tommel */
        border-radius: 10px; /* Runde kanter */
    }
    div[data-testid="stTabs"]::-webkit-scrollbar-track {
        background: #e6e6e6; /* Bakgrunnsfarge for scrollbar */
    }
    </style>
""", unsafe_allow_html=True)

# Legg til CSS for å style appen
st.markdown("""
    <style>
    /* Bakgrunnsfarge */
    body {
        background-color: #f5f5f5;
    }

    /* Tilpasset font */
    * {
        font-family: 'Arial', sans-serif;
    }

    /* Header-styling */
    h1, h2, h3 {
        color: #333333;
    }

    /* Tab-knapper */
    div[data-testid="stTabs"] button {
        background-color: #ffffff;
        border: 1px solid #cccccc;
        border-radius: 5px;
        padding: 10px;
        margin-right: 5px;
        color: #333333;
        font-weight: bold;
    }

    /* Hover-effekt på tab-knapper */
    div[data-testid="stTabs"] button:hover {
        background-color: #e6e6e6;
        color: #000000;
    }

    /* Aktiv tab */
    div[data-testid="stTabs"] button[aria-selected="true"] {
        background-color: #007bff;
        color: #ffffff;
    }

    /* Dataframe-styling */
    .stDataFrame {
        border: 1px solid #cccccc;
        border-radius: 5px;
    }
    </style>
""", unsafe_allow_html=True)

# ----------------------------
# 2. Dataopplasting og standarddata
# ----------------------------
st.sidebar.header("📂 Last opp dine data")
uploaded_sales = st.sidebar.file_uploader("Last opp Salgsdata", type="csv", key="sales")
uploaded_cost = st.sidebar.file_uploader("Last opp Kostnadsdata", type="csv", key="cost")
uploaded_traffic = st.sidebar.file_uploader("Last opp Trafikkdata", type="csv", key="traffic")
uploaded_prod = st.sidebar.file_uploader("Last opp Produktdata", type="csv", key="prod")
uploaded_prices = st.sidebar.file_uploader("Last opp Innkjøpspriser", type="csv", key="prices")

@st.cache_data
def load_sales_data(filepath):
    df = pd.read_csv(filepath)
    df.columns = df.columns.str.strip().str.lower()
    rename_map = {"date": "dato", "sales": "omsetning", "antallsolgt": "antallordre"}
    df = df.rename(columns=rename_map)
    if "dato" in df.columns:
        df["Dato"] = pd.to_datetime(df["dato"], errors="coerce").dt.date
    if "omsetning" in df.columns:
        df["Omsetning"] = pd.to_numeric(df["omsetning"].astype(str).str.replace(" ", ""), errors="coerce")
    if "antallordre" in df.columns:
        df["Ant. ordre"] = pd.to_numeric(df["antallordre"], errors="coerce")
    return df

def read_standard_csv(filepath, date_col="date"):
    df = pd.read_csv(filepath)
    df.columns = df.columns.str.strip()
    if date_col in df.columns:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    elif "dato" in df.columns:
        df.rename(columns={"dato": date_col}, inplace=True)
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    else:
        st.error("Ingen dato-kolonne funnet.")
    return df

if uploaded_sales is not None:
    sales_df = load_sales_data(uploaded_sales)
else:
    sales_df = load_sales_data("standardized_sales.csv")

if uploaded_cost is not None:
    cost_df = read_standard_csv(uploaded_cost, date_col="date")
else:
    cost_df = read_standard_csv("standardized_cost.csv", date_col="date")

if uploaded_traffic is not None:
    traffic_df = read_standard_csv(uploaded_traffic, date_col="date")
else:
    traffic_df = read_standard_csv("standardized_traffic.csv", date_col="date")

if uploaded_prod is not None:
    product_sales_df = read_standard_csv(uploaded_prod, date_col="date")
else:
    product_sales_df = read_standard_csv("standardized_product_sales.csv", date_col="date")

if "Produktnavn" in product_sales_df.columns:
    product_sales_df.rename(columns={"Produktnavn": "product_name"}, inplace=True)
if "SKU" in product_sales_df.columns:
    product_sales_df.rename(columns={"SKU": "sku"}, inplace=True)

# Eksempel på kolonneomdøping
if "varekostnad" in cost_df.columns:
    cost_df.rename(columns={"varekostnad": "cost"}, inplace=True)

# ----------------------------
# 3. Navigasjon / Tabs
# ----------------------------
tabs = st.tabs([
    "Salgsdata",  
    "Kostnadsanalyse & Budsjett", 
    "Lagerinnsikt & Innkjøpsstrategi", 
    "Digital Analyse & SEO", 
    "Konkurrentanalyse", 
    "Optimale produktpriser & Bedriftsråd", 
    "Verdivurdering", 
    "Analytics Live-data"
])

# ----------------------------
# FANE 1 – Salgsdata med templatemaler og info om SmartDash
with tabs[0]:
    st.markdown("### Slik bruker dere SmartDash")
    st.markdown("""
**Templatemaler for opplasting**  
Se nederst i denne tabben for
 eksempelfiler for opplasting, basert på Luxushair sine data som vises som standard/eksempler her i Dashboardet.  
Last ned eksempelfilene, og erstatt med egne data. Følg nøyaktig samme struktur og ha nøyaktig samme navn på filene når de lastes opp igjen i 
venstre sidebar.  

    """)
    st.header("Salgsdata")
    st.markdown("Her kan du se salgsdata for valgte perioder. Velg om du vil se data daglig eller aggregert per måned, og hvilken visualisering du ønsker.")
    
    filter_mode = st.radio("Filtermodus", ("Daglig", "Månedlig"))
    vis_type = st.selectbox("Velg visualiseringsmetode", ("Stolpediagram", "Linjediagram", "Kakediagram"))
    
    if filter_mode == "Daglig":
        start_date = st.date_input("Velg startdato", value=datetime(2024, 1, 1))
        end_date = st.date_input("Velg sluttdato", value=datetime(2024, 12, 31))
        mask = (pd.to_datetime(sales_df["Dato"]) >= pd.to_datetime(start_date)) & \
               (pd.to_datetime(sales_df["Dato"]) <= pd.to_datetime(end_date))
        filtered_sales = sales_df.loc[mask]
        st.write("Filtrerte salgsdata (daglig):", filtered_sales)
        if vis_type == "Stolpediagram":
            fig = px.bar(filtered_sales, x="Dato", y="Omsetning", title="Omsetning per dag")
        elif vis_type == "Linjediagram":
            fig = px.line(filtered_sales, x="Dato", y="Omsetning", title="Omsetning per dag")
        else:
            agg = filtered_sales.groupby("Dato", as_index=False)["Omsetning"].sum()
            fig = px.pie(agg, names="Dato", values="Omsetning", title="Andel omsetning daglig")
        st.plotly_chart(fig, use_container_width=True, key="fig_sales_daily")
    else:
        sales_df["YearMonth"] = pd.to_datetime(sales_df["Dato"]).dt.to_period("M").astype(str)
        start_month = st.text_input("Startmåned (YYYY-MM)", value="2024-01")
        end_month = st.text_input("Sluttmåned (YYYY-MM)", value="2024-12")
        mask = (sales_df["YearMonth"] >= start_month) & (sales_df["YearMonth"] <= end_month)
        filtered_sales = sales_df.loc[mask].copy()
        agg_sales = filtered_sales.groupby("YearMonth", as_index=False)["Omsetning"].sum()
        st.write("Aggregert salgsdata per måned:", agg_sales)
        if vis_type == "Stolpediagram":
            fig = px.bar(agg_sales, x="YearMonth", y="Omsetning", title="Omsetning per måned")
        elif vis_type == "Linjediagram":
            fig = px.line(agg_sales, x="YearMonth", y="Omsetning", title="Omsetning per måned")
        else:
            fig = px.pie(agg_sales, names="YearMonth", values="Omsetning", title="Andel omsetning per måned")
        st.plotly_chart(fig, use_container_width=True, key="fig_sales_monthly")
        
    st.markdown("**Merk:** Dataene kan filtreres både på daglig og månedlig basis.")

    # Templatemaler for nedlasting
    st.markdown("### Templatemaler for opplasting")
    st.markdown("Her finner dere eksempelfiler for opplasting. Last ned filene nedenfor:")

    # Opprett nedlastingsknapper for hver fil
    template_files = {
        "Standardisert salgsdata CSV": "standardized_sales.csv",
        "Standardisert kostnadsdata CSV": "standardized_cost.csv",
        "Standardisert trafikkdata CSV": "standardized_traffic.csv",
        "Standardisert produktdata CSV": "standardized_product_sales.csv",
        "Standardisert innkjøpspriser CSV": "standardized_prices.csv"
    }

    for label, filepath in template_files.items():
        try:
            with open(filepath, "rb") as file:
                st.download_button(
                    label=f"Last ned {label}",
                    data=file,
                    file_name=filepath,
                    mime="text/csv"
                )
        except FileNotFoundError:
            st.error(f"Filen {filepath} ble ikke funnet.")

# ----------------------------
# FANE 2 – Kostnadsanalyse & Budsjett
# ----------------------------
with tabs[1]:
    st.header("Kostnadsanalyse & Budsjett")
    st.markdown("**Kostnadsdata for hele 2024**")
    st.write(cost_df)
    cost_columns = [col for col in ["varekostnad", "driftskostnader", "finansielle_kostnader", "lønnskostnad", "totale_kostnader"] if col in cost_df.columns]
    if cost_columns:
        fig_cost = px.bar(cost_df, x="date", y=cost_columns, 
                          title="Kostnader per måned",
                          barmode="group",
                          labels={"value": "Kostnader (kr)", "variable": "Kostnadstype"})
        st.plotly_chart(fig_cost, use_container_width=True, key="fig_cost_chart")
    else:
        st.error("Ingen kostnadskolonner funnet for å lage diagram.")
    st.markdown("#### Kostnadstall per kategori:")
    for col in cost_columns:
        if col in cost_df.columns:
            total = cost_df[col].sum()
            st.markdown(f"- **{col.capitalize()}**: {total:,.0f} kr")
    selected_margin = st.number_input("Angi ønsket fortjenestemargin (%)", min_value=0.0, max_value=100.0, 
                                      value=30.0, step=1.0, key="margin_kostnad")
    margin = selected_margin / 100.0
    if "totale_kostnader" in cost_df.columns:
        total_cost = cost_df["totale_kostnader"].iloc[0]
    else:
        total_cost = sum(cost_df[col].sum() for col in cost_columns)
    optimal_revenue = total_cost / (1 - margin)
    
    st.markdown(f"**Total kostnad:** {total_cost:,.0f} kr")
    st.markdown(f"**Optimal budsjettert omsetning:** {optimal_revenue:,.0f} kr")
    st.subheader(f"Optimal budsjettert omsetning: {optimal_revenue:,.0f} kr")
    st.markdown(f"""
**Forklaring:**  
Her brukes en fortjenestemargin på {selected_margin:.0f}% (desimalverdi {margin}) for å beregne optimal budsjettert omsetning.  
Formelen er:  
  Total kostnad / (1 – margin)  
Altså, dersom de totale kostnadene er {total_cost:,.0f} kr,  
må omsetningen være minst {optimal_revenue:,.0f} kr for å oppnå ønsket fortjeneste.
    """)

# ----------------------------
# FANE 3 – Lagerinnsikt & Innkjøpsstrategi
# ----------------------------
with tabs[2]:
    st.header("Lagerinnsikt & Innkjøpsstrategi")

    # Velg SKU-filtrering
    selected_sku_filter = st.text_input(
        "Filtrer etter SKU (f.eks. '40 cm', 'Clip On')",
        value="",
        key="sku_filter"
    )

    # Velg datoer
    inv_start_date = st.date_input("Startdato", value=datetime(2023, 11, 7), key="sku_start")
    inv_end_date = st.date_input("Sluttdato", value=datetime(2024, 12, 31), key="sku_end")

    # Filtrer data basert på dato
    mask = (product_sales_df["date"] >= pd.to_datetime(inv_start_date)) & \
           (product_sales_df["date"] <= pd.to_datetime(inv_end_date))
    df = product_sales_df.loc[mask].copy()

    # Filtrer data basert på SKU
    if selected_sku_filter.strip():
        pattern = re.compile(rf"\b{re.escape(selected_sku_filter.strip())}\b", re.IGNORECASE)
        df = df[df["sku"].str.contains(pattern, na=False)]

    # Sjekk om df er tom
    if df.empty:
        st.error("Ingen data tilgjengelig for de valgte filtrene.")
    else:
        # Gruppere data basert på SKU
        grouped = df.groupby("sku", as_index=False).agg({
            "antallsolgt": "sum",
            "product_name": "first"
        })

        # Beregn gjennomsnittlig solgt per måned og anbefalt varelager
        start_dt = pd.to_datetime(inv_start_date)
        end_dt = pd.to_datetime(inv_end_date)
        n_months = (end_dt - start_dt).days / 30
        if n_months <= 0:
            n_months = 1
        grouped["Gj.sn. solgt per måned"] = grouped["antallsolgt"] / n_months
        grouped["Anbefalt varelager"] = grouped["Gj.sn. solgt per måned"].apply(lambda x: math.ceil(x * 4 * 1.2))

        # Visualisering – stolpediagram
        fig = px.bar(
            grouped,
            x="sku",
            y="antallsolgt",
            title="Antall solgt per SKU",
            labels={"antallsolgt": "Antall solgt", "sku": "SKU"},
            hover_data=["product_name", "Gj.sn. solgt per måned", "Anbefalt varelager"]
        )
        st.plotly_chart(fig, use_container_width=True)

        # Sorter tabellen basert på "Anbefalt varelager" i synkende rekkefølge
        grouped = grouped.sort_values(by="Anbefalt varelager", ascending=False)

        # Vis tabell med data
        st.markdown("### Detaljert lagerinnsikt")
        st.dataframe(
            grouped[["sku", "product_name", "antallsolgt", "Gj.sn. solgt per måned", "Anbefalt varelager"]],
            height=600
        )

        # Legg til forklarende tekst nederst i fanen
        st.markdown("""
        ### Forklaring:
        - **Gj.sn. solgt per måned**: Gjennomsnittlig antall solgte enheter per måned basert på valgt datoperiode.
        - **Anbefalt varelager**: Beregnet ut i fra salgsstatistikk og 3 uker leverings/produksjonstid med 20 % sikkerhetsmargin for å sikre tilgjengelighet. Bestill varer ca hver 3. uke.
        - **Filtrering**: Du kan filtrere etter SKU (produktvariant) ved å bruke nøkkelord som "40 cm" eller "Clip On".
        - **Visualisering**: Diagrammet viser antall solgte enheter per SKU, og tabellen gir detaljert innsikt i lagerbehovet.
        """)

# ----------------------------
# FANE 4 – Digital Analyse & SEO
# ----------------------------
with tabs[3]:
    st.header("Digital Analyse & SEO")
    st.markdown("""
    **SEO-Analyse med annonseforslag**  
    Dette er LuxusHair sin integrasjon – standarddata benyttes, men denne løsningen kan custom-integreres for den enkelte bedrift.
    """)
    
    # Annonseforslag
    st.markdown("### Annonseforslag")
    ad_suggestions = [
        {
            "title": "LuxusHair – Premium Extensions for Eksklusiv Stil",
            "description": "Oppdag våre førsteklasses hårforlengelser for en luksuriøs look. Bestill nå!",
            "prompt": "En kvinne med langt, glansfullt hår i naturlige omgivelser."
        },
        {
            "title": "Få drømmehåret med LuxusHair",
            "description": "Langt, fyldig hår på minutter. Se vårt utvalg av Clip-On Extensions.",
            "prompt": "En kvinne som styler håret sitt foran et speil."
        },
        {
            "title": "LuxusHair – Naturlig skjønnhet",
            "description": "Premium hårforlengelser for enhver anledning. Handle nå!",
            "prompt": "En kvinne med elegant hår i en festlig setting."
        },
        {
            "title": "LuxusHair – Din hårforlengelsesekspert",
            "description": "Oppdag hvorfor tusenvis velger LuxusHair. Bestill i dag!",
            "prompt": "En kvinne med langt hår som smiler utendørs."
        },
        {
            "title": "LuxusHair – Kvalitet du kan stole på",
            "description": "Hårforlengelser som varer. Se vårt utvalg nå!",
            "prompt": "En kvinne som viser frem sitt lange, glansfulle hår."
        }
    ]
    
    for ad in ad_suggestions:
        st.markdown(f"**Tittel:** {ad['title']}")
        st.markdown(f"**Beskrivelse:** {ad['description']}")
        st.markdown(f"**Bildeprompt:** {ad['prompt']}")
        st.markdown("---")

    if "date" not in traffic_df.columns:
        st.error("Ingen 'date' kolonne funnet i trafikkdata.")
    else:
        if traffic_df.empty:
            traffic_df = pd.DataFrame({
                "søkeord": ["luxushair behandling", "premium extensions", "keratin behandling"],
                "antallvisninger": [1000, 800, 600]
            })
        seo_agg = traffic_df.groupby("søkeord", as_index=False)["antallvisninger"].sum()
        seo_agg = seo_agg.sort_values(by="antallvisninger", ascending=False).head(35)
        st.markdown("#### Top 35 søkeord (sortert fra høy til lav visning):")
        st.table(seo_agg)
        fig_traffic = px.bar(seo_agg, x="søkeord", y="antallvisninger", 
                             title="Topp søkeord (visninger)", template="plotly_white")
        st.plotly_chart(fig_traffic, use_container_width=True, key="fig_traffic_chart")
    st.markdown("""
**SEO-ekspertise og annonseplan:**  
- Beste Keywords: luxushair behandling, premium extensions, keratin behandling  
- Meta-tittel forslag: "LuxusHair – Eksklusive Hårbehandlinger og Premium Extensions"  
- Meta-beskrivelse forslag: "Opplev luksus med våre profesjonelle hårbehandlinger. Bestill nå for en eksklusiv hårtransformation!"  
- Annonseringsstrategi: Google Ads, Facebook Ads, Instagram Ads, YouTube, Pinterest  
- Postingsplan: Instagram (3–4 innlegg/uke), Facebook (2–3 innlegg/uke), YouTube (1 video/uke), Blogg (2–3 innlegg/måned), Pinterest (daglige pins)
    """, unsafe_allow_html=True)

# ----------------------------
# FANE 5 – Konkurrentanalyse
# ----------------------------
with tabs[4]:
    st.header("Konkurrentanalyse")
    competitor_data = pd.DataFrame({
        "Firma": ["LuxusHair", "HairLux", "StylePro", "GlamourHair"],
        "Omsetning (kr)": [6600000, 4300000, 2900000, 3500000],
        "Markedsandel (%)": [40, 26, 18, 16]
    })
    
    # Vis data som tabell
    st.markdown("### Konkurrentanalyse – Omsetning og Markedsandeler")
    st.dataframe(competitor_data)
    
    # Visualisering av omsetning
    fig_comp = px.bar(
        competitor_data, 
        x="Firma", 
        y="Omsetning (kr)", 
        title="Konkurrentanalyse – Omsetning",
        text="Markedsandel (%)"
    )
    fig_comp.update_traces(textposition="outside")
    st.plotly_chart(fig_comp, use_container_width=True)
    
    st.markdown("""
    **Forklaring:**  
    Dataene viser estimerte omsetningstall og markedsandeler for hovedkonkurrentene i 2024.  
    Dette hjelper med å vurdere vår markedsposisjon og hvor vi kan forbedre kostnadseffektivitet og marginer.
    """)

# ----------------------------
# I FANE 6 – Bedriftsråd (Oppsummering)
with tabs[5]:
    st.header("Optimale produktpriser & Bedriftsråd")
    st.markdown("""
Her oppsummeres bedriftsråd, samt nøkkeltall knyttet til optimal budsjettering og produktprising.
                
✅ Optimaliser lagerstyring: Juster vareinnkjøp etter faktisk etterspørsel.  
✅ Reduser kostnader: Forhandle med leverandører og effektiviser interne prosesser.  
✅ Forbedre markedsføring: Følg SEO-strategien og publiser jevnlig i SoMe-kanaler.  
✅ Øk konverteringsrate: Optimaliser brukeropplevelsen på nettsiden.  
✅ Overvåk jevnlig: Følg nøkkeltall og handle raskt ved budsjettavvik.
    """)

    st.markdown("### Optimale produktpriser")
    st.markdown("""
Her beregnes optimal utsalgspris basert på reelle innkjøpspriser (LuxusHair sine fallback-priser brukes dersom ingen fil er lastet opp).  
Du kan angi fortjenestemargin og overhead, og den resulterende utsalgsprisen vises (inkludert mva.).  
Velg hvilket hovedprodukt du vil se optimal utsalgspris for ved å bruke dropdownen nedenfor.
    """)

    # Last inn innkjøpspriser (bruk standarddata hvis ingen fil er lastet opp)
    if uploaded_prices is not None:
        df_prices = pd.read_csv(uploaded_prices)
        purchase_prices = dict(zip(df_prices["Produkt"], df_prices["Pris"]))
    else:
        purchase_prices = {
            "Clip On Extension Virgin 55 cm": 1300,
            "Clip On Extension Virgin 60 cm": 3900,
            "Clip On Extension Virgin 40 cm": 400,
            "Clip On Extension Virgin 50 cm": 500
        }
    fallback_tekst = "\n".join(["- {}: {} kr".format(produkt, pris) for produkt, pris in purchase_prices.items()])  # Bygg liste med hovedproduktalternativer
    lengths = ["40", "50", "55", "60"]
    main_product_options = []
    for typ in ["Clip On Extension Virgin", "Tape On Extension Virgin", "Keratin Extension Virgin"]:
        for l in lengths:
            main_product_options.append(f"{typ} {l} cm")
    default_main = "Clip On Extension Virgin 40 cm"
    default_main_index = main_product_options.index(default_main) if default_main in main_product_options else 0

    # Drop-down for valg av hovedprodukt med unik key (kun i FANE 6)
    selected_main_product = st.selectbox(
        "Velg hovedprodukt for optimal prisberegning (anbefalt utsalgspris vises lenger ned på siden)",
        options=main_product_options,
        index=default_main_index,
        key="main_product_select_unique_f6"
    )
    normalized_main_product = selected_main_product.replace("Extensions ", "Extension ")

    # Brukerinput for margin og overhead (unike keys)
    user_margin_tab6 = st.number_input(
        "Angi fortjenestemargin (%)", 
        min_value=0.0, 
        max_value=100.0,
        value=30.0, 
        step=1.0, 
        key="margin_bedriftsrad_tab6"
    ) / 100.0
    user_overhead_tab6 = st.number_input(
        "Angi overhead (%)", 
        min_value=0.0, 
        max_value=100.0,
        value=25.0, 
        step=1.0, 
        key="overhead_bedrads_tab6"
    ) / 100.0

    st.markdown(
        """
**Forklaring - Optimal utsalgspris:**  
Optimal utsalgspris beregnes slik:  
((Innkjøpspris × (1 + overhead)) / (1 – fortjenestemargin))  
Her brukes en overhead på {0:.0f}% og en fortjenestemargin på {1:.0f}%.  
Utsalgsprisen inkluderer merverdiavgift.
Velg hovedprodukt du ønsker se anbefalt utsalgspris for i dropdownen over.
        """.format(user_overhead_tab6 * 100, user_margin_tab6 * 100)
    )

    # Hent fallback-innkjøpspris for det valgte hovedproduktet og beregn optimal pris
    fallback_price = purchase_prices.get(normalized_main_product, None)
    if fallback_price is not None:
        totalkost = fallback_price * (1 + user_overhead_tab6)
        computed_price = totalkost / (1 - user_margin_tab6)
        optimal_price = (computed_price // 10) * 10 + 9
        st.markdown(
            f"### Optimale produktpriser\n**Optimal produktpris for {normalized_main_product}: {int(optimal_price):,} kr**"
        )
    else: 
        st.info(
            "Ingen standard innkjøpspris funnet for det valgte hovedproduktet. "
            "Dataene er basert på LuxusHair sine standarddata, og oppdateres når din bedrift laster opp egne priser."
        )
    
    
# ----------------------------
# FANE 7 – Verdivurdering
with tabs[6]:
    st.header("Verdivurdering")
    ebitda = 755000
    try:
        cost_data = pd.read_csv("standardized_cost.csv")
        if "driftsresultat" in cost_data.columns:
            driftsresultat = pd.to_numeric(cost_data["driftsresultat"], errors="coerce").sum()
        else:
            driftsresultat = None
    except Exception as e:
        driftsresultat = None
    value_df = pd.DataFrame({
        "Metode": ["EBITDA-metoden", "DCF-modellen"],
        "Verdi (kr)": [ebitda * 8, ebitda * 11]
    })
    fig_value = px.bar(value_df, x="Metode", y="Verdi (kr)", title="Estimert selskapsverdi")
    extra = ""
    if driftsresultat is not None:
        extra = f"\n- Faktisk driftsresultat: {int(driftsresultat):,} kr (basert på kostnadsdatafilen)."
    explanation = (
        "Bransjefaktoren, satt til 8 for EBITDA-metoden, er basert på historiske data og markedsforventninger. "
        "Faktoren reflekterer forhold som vekstpotensial, risiko og lønnsomhet."
    )
    text = f"""
    **Verdivurdering – Forklaring:**

    - EBITDA: {ebitda:,.0f} kr  
    - EBITDA x 8 = {ebitda * 8:,.0f} kr  
    - DCF x 11 = {ebitda * 11:,.0f} kr  

    Forutsetter stabil drift og kontantstrøm.{extra}

    {explanation}
    """
    st.plotly_chart(fig_value, use_container_width=True, key="fig_value_chart")
    st.markdown(text)

# ----------------------------
# FANE 8 – Analytics Live-data (med datovelger)
with tabs[7]:
    st.header("Analytics Live-data")
    st.markdown("""
    **SmartDash Analytics Integrasjon**  
    Tilpass spørringen ved å velge datoperiode. Standarddata benyttes – løsningen kan skreddersys med egne KPI-er.
    """)
    
    # Legg til datovelger for Analytics (start- og sluttdato)
    ga_start_date = st.date_input("Velg GA startdato", value=datetime(2025, 1, 1), key="ga_start_date")
    ga_end_date = st.date_input("Velg GA sluttdato", value=datetime.today(), key="ga_end_date")
    
    available_metrics = {
        "Active Users": "activeUsers",
        "New Users": "newUsers",
        "Sessions": "sessions",
        "Conversions": "conversions"
    }
    selected_display_metrics = st.multiselect("Velg metrikker", list(available_metrics.keys()),
                                              default=["Active Users", "New Users"],
                                              key="ga_metric_live")
    selected_metrics = [Metric(name=available_metrics[m]) for m in selected_display_metrics]
    
    def get_live_analytics(selected_metrics, start_date, end_date):
        client = BetaAnalyticsDataClient()
        metric_names = [m.name for m in selected_metrics]
        request = RunReportRequest(
            property="properties/2750762604", 
            dimensions=[{"name": "date"}],
            metrics=[{"name": name} for name in metric_names],
            date_ranges=[{"start_date": start_date.strftime("%Y-%m-%d"), "end_date": end_date.strftime("%Y-%m-%d")}]
        )
        response = client.run_report(request)
        data = {"Dato": [row.dimension_values[0].value for row in response.rows]}
        for i, name in enumerate(metric_names):
            data[name] = [int(row.metric_values[i].value) for row in response.rows]
        df = pd.DataFrame(data)
        fig = px.line(
            df, 
            x="Dato", 
            y=metric_names, 
            title="Live Analytics Data",
            color_discrete_sequence=px.colors.qualitative.Bold  # Forbedrede farger
        )
        return fig
    
    try:
        fig_live = get_live_analytics(selected_metrics, ga_start_date, ga_end_date)
        fig_live.update_layout(
            title_font_size=24,
            xaxis=dict(title="Dato", tickangle=45),
            yaxis=dict(title="Måleverdi"),
            margin=dict(l=50, r=50, t=80, b=50),
            template="plotly_white"
        )
        st.plotly_chart(fig_live, use_container_width=True, key="fig_live_chart")
    except Exception as e:
        st.error(f"Kunne ikke hente live data: {e}")

