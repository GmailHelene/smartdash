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

# Oppdater sidetittelen og ikonet i st.set_page_config:
st.set_page_config(
    layout="wide",
    page_title="SmartDash",
    page_icon="🚀"  # eks. et alternativt emoji-ikon
)
st.markdown("""
# Legg til CSS for å gjøre fanene scrollbare
     <style>
     /* Gjør fanene scrollbare */
     div[data-testid="stTabs"] > div {
         overflow-x: auto;
         white-space: nowrap;
         scrollbar-width: thin; /* Gjør scrollbaren tynnere */
     }
     div[data-testid="stTabs"]::-webkit-scrollbar {
         height: 12px; /* Øk høyden på scrollbaren */
     }
     div[data-testid="stTabs"]::-webkit-scrollbar-thumb {
         background-color: #888; /* Farge på scrollbaren */
         border-radius: 10px; /* Gjør scrollbaren rundere */
     }
     div[data-testid="stTabs"]::-webkit-scrollbar-thumb:hover {
         background-color: #555; /* Farge når man holder over scrollbaren */
     }
     div[data-testid="stTabs"] button {
         flex-shrink: 0;
     }
     </style>
 """, unsafe_allow_html=True)

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
    sales_df = load_sales_data("./standardized_sales.csv")

if uploaded_cost is not None:
    cost_df = read_standard_csv(uploaded_cost, date_col="date")
else:
    cost_df = read_standard_csv("./standardized_cost.csv", date_col="date")

if uploaded_traffic is not None:
    traffic_df = read_standard_csv(uploaded_traffic, date_col="date")
else:
    traffic_df = read_standard_csv("./standardized_traffic.csv", date_col="date")

if uploaded_prod is not None:
    product_sales_df = read_standard_csv(uploaded_prod, date_col="date")
else:
    product_sales_df = read_standard_csv("./standardized_product_sales.csv", date_col="date")

if "Produktnavn" in product_sales_df.columns:
    product_sales_df.rename(columns={"Produktnavn": "product_name"}, inplace=True)
if "SKU" in product_sales_df.columns:
    product_sales_df.rename(columns={"SKU": "sku"}, inplace=True)

# ----------------------------
# 3. Navigasjon / Tabs
# ----------------------------
tabs = st.tabs([
    "Salgsdata",  
    "Kostnadsanalyse & Budsjett", 
    "Lagerinnsikt & Innkjøpsstrategi", 
    "Digital Analyse & SEO", 
    "Konkurrentanalyse", 
    "Bedriftsråd (Oppsummering)", 
    "Verdivurdering", 
    "Analytics Live-data"
])

# ----------------------------
# FANE 1 – Salgsdata med templatemaler og info om SmartDash
with tabs[0]:
    st.markdown("### Slik bruker dere SmartDash")
    st.markdown("""
**Templatemaler for opplasting**  
Her finner dere eksempelfiler for opplasting, basert på Luxushair sine data som vises som standard/eksempler her i Dashboardet.  
Last ned eksempelfilene, og erstatt med egne data. Følg nøyaktig samme struktur og ha nøyaktig samme navn på filene når de lastes opp igjen i venstre sidebar.  
- [Standardisert salgsdata CSV](standardized_sales.csv)  
- [Standardisert kostnadsdata CSV](standardized_cost.csv)  
- [Standardisert trafikkdata CSV](standardized_traffic.csv)  
- [Standardisert produktdata CSV](standardized_product_sales.csv)  
- [Standardisert innkjøpspriser CSV](standardized_prices.csv)
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
    st.markdown(f"""
**Forklaring:**  
Her brukes en fortjenestemargin på {selected_margin:.0f}% (desimalverdi {margin}) for å beregne optimal budsjettert omsetning.  
Formelen er:  
  Total kostnad / (1 – margin)  
Altså, dersom de totale kostnadene er {total_cost:,.0f} kr,  
må omsetningen være minst {optimal_revenue:,.0f} kr for å oppnå ønsket fortjeneste.
    """)

# ----------------------------
# FANE 3 – Lagerinnsikt & Innkjøpsstrategi (Filtrering på produktnavn og lengde)
with tabs[2]:
    st.header("Lagerinnsikt & Innkjøpsstrategi (Filtrering på produktnavn og lengde)")

    # Available product names
    product_options = sorted(product_sales_df["product_name"].dropna().unique())
    default_products = ["Clip On", "Keratin", "Tape Extensions"]
    valid_default_products = [p for p in default_products if p in product_options]

    # Velg produktnavn med standardverdi
    selected_products = st.multiselect(
        "Velg produktnavn (opptil 3)",
        options=product_options,
        default=valid_default_products,
        key="product_name_filter"
    )

    # Available lengths
    length_options = ["40 cm", "50 cm", "55 cm", "60 cm"]
    default_lengths = ["40 cm", "50 cm", "55 cm"]
    valid_default_lengths = [l for l in default_lengths if l in length_options]

    # Velg lengde med standardverdi
    selected_lengths = st.multiselect(
        "Velg lengde (cm)",
        options=length_options,
        default=valid_default_lengths,
        key="length_filter"
    )

    # Velg datoer med standardverdier
    inv_start_date = st.date_input("Startdato", value=datetime(2024, 1, 1), key="sku_start")
    inv_end_date = st.date_input("Sluttdato", value=datetime(2024, 12, 31), key="sku_end")

    # Filtrer data basert på dato
    mask = (product_sales_df["date"] >= pd.to_datetime(inv_start_date)) & \
           (product_sales_df["date"] <= pd.to_datetime(inv_end_date))
    df = product_sales_df.loc[mask].copy()

    # Filtrer data for valgte produktnavn (hvis noen er valgt)
    if selected_products:
        df = df[df["product_name"].isin(selected_products)]

    # Filtrer data for valgte lengder (hvis noen er valgt)
    if selected_lengths:
        pattern = re.compile(rf"\b({'|'.join([re.escape(length.strip()) for length in selected_lengths])})\b", re.IGNORECASE)
        df = df[df["sku"].str.contains(pattern, na=False)]

    # Sjekk om df er tom
    if df.empty:
        st.error("Ingen data tilgjengelig for de valgte filtrene.")
    else:
        # Sorter data etter ønsket kolonne (f.eks. "antallsolgt")
        df_sorted = df.sort_values(by="antallsolgt", ascending=False)

        # Fyll inn NaN-verdier i "antallsolgt" med 0
        df_sorted["antallsolgt"] = df_sorted["antallsolgt"].fillna(0)

        # Beregn "Anbefalt innkjøp"
        df_sorted["Anbefalt innkjøp"] = (df_sorted["antallsolgt"] / 4).apply(lambda x: max(1, round(x)))

        # Beregn total kostnad for anbefalt innkjøp
        total_cost = 0
        st.markdown("### Anbefalt innkjøpsstrategi")
        st.markdown("Her er en oversikt over anbefalte innkjøp basert på salgsdata av valgt hovedprodukt i filtreringen over:")

        for index, row in df_sorted.iterrows():
            # Anta en standard innkjøpspris for hver SKU (kan tilpasses)
            purchase_price = 300  # Eksempel: 300 kr per enhet
            total_cost += row["Anbefalt innkjøp"] * purchase_price
            st.markdown(f"- **{row['sku']}**: Anbefalt innkjøp {row['Anbefalt innkjøp']} enheter")

        st.markdown(f"**Total kostnad for anbefalt innkjøp:** {total_cost:,.0f} kr")

        # Begrens antall rader i diagrammet til maks 25
        df_chart = df_sorted.head(25)

        # Visualisering – stolpediagram med Plotly dark-tema (blå/mørkt diagram)
        fig = px.bar(
            df_chart,
            x="sku",
            y="antallsolgt",
            title=f"Antall solgt for valgt produkt og lengde",
            hover_data=["product_name", "sku"],
            template="plotly_dark"
        )

        st.plotly_chart(fig, use_container_width=True)
        st.markdown("**Filtrerte SKU-er sortert etter antall solgt:**")

        # Oppdatert tabellvisning (vis 40 rader uten scrolling, skjul første kolonne)
        st.dataframe(
            df_sorted[["sku", "product_name", "antallsolgt"]].head(40),
            height=800  # Juster høyden for å vise 40 rader uten scrolling
        )

    # Seksjon for lagerinnkjøp og anbefalinger
    st.markdown("### Lagerinnkjøp og anbefalinger")
    st.markdown("""
    Visningen over viser antall solgt og anbefalt innkjøpsstrategi for valgt hovedprodukt (filtreringen øverst) , endre for å se innkjøpsstrategi for andre produkter.
    Basert på salgsdata anbefaler vi varebestilling ca hver 3. uke, og overstående produktmiks/lagerinnkjøp av valgt produktvisning for de neste 3 ukene.
    (LuxusHair har 3 ukers leveringstid fra bestilling til varer ankommer lageret):
    """)
    
    # Beregn anbefalt innkjøp (4 ukers buffer)
    # Sørg for at "antallsolgt" kun inneholder numeriske verdier

    # Beregn "Anbefalt innkjøp"
    st.markdown(f"**Total kostnad for anbefalt innkjøp:** {total_cost:,.0f} kr")

## ----------------------------
# FANE 4 – SEO & Konkurrentanalyse
# ----------------------------
with tabs[3]:
    st.header("SEO & Konkurrentanalyse")
    st.markdown("""
# Combine "Konkurrentanalyse" with "Digital Analyse & SEO"""
    """)
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
 Beste Keywords: luxushair behandling, premium extensions, keratin behandling  
 Meta-tittel forslag: "LuxusHair  Eksklusive Hårbehandlinger og Premium Extensions"  
 Meta-beskrivelse forslag: "Opplev luksus med våre profesjonelle hårbehandlinger. Bestill nå for en eksklusiv hårtransformation!"  
 Annonseringsstrategi: Google Ads, Facebook Ads, Instagram Ads, YouTube, Pinterest  
 Postingsplan: Instagram; 3 til 4 innlegg/uke, Facebook; 2 til 3 innlegg/uke, YouTube; 1 video/uke), Blogg; 2 til 3 innlegg/måned, Pinterest; daglige pins
    """, unsafe_allow_html=True)

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
    # Konkurrentanalyse section
    st.header("Konkurrentanalyse")
    competitor_data = pd.DataFrame({
        "Firma": ["LuxusHair", "HairLux", "StylePro", "GlamourHair"],
        "Omsetning": [6600000, 4300000, 2900000, 3500000]
    })
    fig_comp = px.bar(competitor_data, x="Firma", y="Omsetning", title="Konkurrentanalyse")
    st.plotly_chart(fig_comp, use_container_width=True, key="fig_comp_chart")
    st.markdown("Estimerte omsetningstall for hovedkonkurrentene i 2024. Dette hjelper med å vurdere vår markedsposisjon.")

# Remove "Optimal budsjettert omsetning" section from "Bedriftsråd"
# ----------------------------
# FANE 5 – Konkurrentanalyse
# ----------------------------
with tabs[4]:
    st.header("Konkurrentanalyse")
    competitor_data = pd.DataFrame({
        "Firma": ["LuxusHair", "HairLux", "StylePro", "GlamourHair"],
        "Omsetning": [6600000, 4300000, 2900000, 3500000]
    })
    fig_comp = px.bar(competitor_data, x="Firma", y="Omsetning", title="Konkurrentanalyse")
    st.plotly_chart(fig_comp, use_container_width=True, key="fig_comp_chart")
    st.markdown("Estimerte omsetningstall for hovedkonkurrentene i 2024. Dette hjelper med å vurdere vår markedsposisjon.")

# ----------------------------
#  FANE 6 – Bedriftsråd (Oppsummering)
with tabs[5]:
    st.header("Optimale produktpriser")
    st.markdown("""
    Her kan bedriften få innsikt i optimal produktpriser basert på egne data og ønskede marginer.
    """)
                
 Optimaliser lagerstyring: Juster vareinnkjøp etter faktisk etterspørsel.  
 Reduser kostnader: Forhandle med leverandører og effektiviser interne prosesser.  
 Forbedre markedsføring: Følg SEO-strategien og publiser jevnlig i SoMe-kanaler.  
 Øk konverteringsrate: Optimaliser brukeropplevelsen på nettsiden.  
 Overvåk jevnlig: Følg nøkkeltall og handle raskt ved budsjettavvik.
    """)

     
    st.markdown("### Optimale produktpriser & Optimal budsjettering")
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
            "Clip On Extension Virgin 50 cm": 500,
            "Tape On Extension Virgin 40 cm": 290,
            "Tape On Extension Virgin 50 cm": 330,
            "Tape On Extension Virgin 60 cm": 400,
            "Keratin Extension Virgin 40 cm": 220,
            "Keratin Extension Virgin 50 cm": 270,
            "Keratin Extension Virgin 60 cm": 350,
            "Keratin Treatment": 100
        }
    fallback_tekst = "\n".join([f"- {produkt}: {pris:,} kr" for produkt, pris in purchase_prices.items()])
    st.markdown(f"**Standard innkjøpspriser (fallback):**\n\n{fallback_tekst}")
    
    # Bygg liste med hovedproduktalternativer
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
    
     # Budsjettert omsetning for FANE 6:
    if total_cost is not None:
        user_margin_budget = st.number_input(
            "Angi ønsket fortjenestemargin (%) for budsjettert omsetning", 
            min_value=0.0, 
            max_value=100.0, 
            value=30.0, 
            step=1.0, 
            key="margin_budget_tab6"
        ) / 100.0
        optimal_revenue = total_cost / (1 - user_margin_budget)
        st.header(f"Optimal budsjettert omsetning: {int(optimal_revenue):,} kr")
        st.markdown("""
**Forklaring:**  
Optimal budsjettert omsetning beregnes slik:  
Total kostnad / (1 – fortjenestemargin)
Denne fanen presenterer en samlet oversikt over optimale utsalgspriser for hovedprodukter og budsjettert omsetning.  
Dataene er basert på standarddata fra LuxusHair og oppdateres når egne priser og kostnadsdata lastes opp.
    else:
        st.info("Kostnadsdata utilgjengelig for beregning av optimal budsjettert omsetning.")
    st.markdown("""
    )
# ----------------------------
# FANE 7 – Verdivurdering & Bedriftsråd
# ----------------------------
    st.header("Verdivurdering & Bedriftsråd")
    st.markdown("""
    Her oppsummeres bedriftsråd, samt en en enkel verdivurdering.
                
    - Optimaliser lagerstyring: Juster vareinnkjøp etter faktisk etterspørsel.  
    - Reduser kostnader: Forhandle med leverandører og effektiviser interne prosesser.  
    - Forbedre markedsføring: Følg SEO-strategien og publiser jevnlig i SoMe-kanaler.  
    - Øk konverteringsrate: Optimaliser brukeropplevelsen på nettsiden.  
    - Overvåk jevnlig: Følg nøkkeltall og handle raskt ved budsjettavvik.
    """)

    st.header("Verdivurdering")
    ebitda = 755000
    try:
        cost_data = pd.read_csv("./standardized_cost.csv")
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
    ga_start_date = st.date_input("Velg GA startdato", value=datetime(2023, 1, 1), key="ga_start_date")
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
            property="properties/283157216",
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
