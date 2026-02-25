"""
App FLA - Fiche de Lancement d'Achat
Un champ texte libre + upload/coller images + bouton Générer → Excel complété.
Lancer avec : streamlit run fla_app.py
"""

import os
import sys
import base64
from pathlib import Path
import streamlit as st
from datetime import date
from dotenv import load_dotenv

# Charger .env depuis le dossier de l'app
APP_DIR = Path(__file__).parent
load_dotenv(APP_DIR / ".env", override=True)

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from fla_engine import build_fla_data, generate_summary
from llm_service import analyze_request, generate_fallback, is_available as llm_available
from document_extractor import extract_from_file
from excel_generator import generate_excel

# --- Page config ---
st.set_page_config(
    page_title="FLA - Lancement d'Achat",
    page_icon="🧪",
    layout="centered",
)

# Titre
st.title("Fiche de Lancement d'Achat")
st.caption("Laboratoire de biologie clinique — CHR Citadelle, Liège")
st.caption("**Dr. SG**")

# Disclaimer / Avertissement légal
st.markdown("""
---
⚠️ **Avertissement légal** : En utilisant cet outil, vous confirmez que :
- Vous l'utilisez en accord avec les règles RGPD de votre établissement
- Vous assumez l'entière responsabilité de son utilisation

Le créateur se dégage de toute responsabilité en cas de mauvais usage.
---
""")

# Sidebar
if llm_available():
    st.sidebar.success("Claude API connectée")
else:
    st.sidebar.error("Claude API non disponible")
    st.sidebar.caption("Ajoutez ANTHROPIC_API_KEY dans .env")

# --- Champ texte unique ---
demande = st.text_area(
    "Décrivez votre demande d'achat (en vrac, comme vous voulez)",
    height=180,
    placeholder=(
        "Exemple : centrifugeuse Eppendorf 5430R, remplacement ancienne 2015, "
        "devis 12500€ TVAC, formation nécessaire, pour section chimie spécialisée"
    ),
)

# --- Upload classique (fichiers) ---
uploaded_files = st.file_uploader(
    "Ou joindre un devis / capture d'écran (fichier)",
    type=["pdf", "png", "jpg", "jpeg", "gif", "webp"],
    accept_multiple_files=True,
)

# --- Bouton Générer ---
st.markdown("")

if st.button("Générer la FLA", type="primary", use_container_width=True):
    if not demande.strip() and not uploaded_files:
        st.error("Décrivez votre demande ou joignez un document.")
    else:
        with st.spinner("Claude analyse votre demande..."):

            # 1. Extraire infos des documents uploadés
            doc_info_parts = []
            has_devis = False
            if uploaded_files:
                has_devis = True
                for uf in uploaded_files:
                    extracted = extract_from_file(uf.getvalue(), uf.name)
                    if extracted:
                        doc_info_parts.append(
                            "\n".join(f"{k}: {v}" for k, v in extracted.items())
                        )
            doc_info_str = "\n".join(doc_info_parts)

            # 2. UN seul appel Claude → tous les champs
            llm_result = analyze_request(demande.strip(), doc_info_str)

            if not llm_result or llm_result.get("_error"):
                # Fallback sans API
                fallback = generate_fallback(demande.strip(), "")
                llm_result = fallback

            # 3. Injecter devis_disponible
            llm_result["devis_disponible"] = has_devis

            # 4. Passer au moteur de règles pour combler les trous
            #    (le moteur ne touche pas aux champs déjà remplis par Claude)
            form_inputs = {
                "objet": llm_result.get("objet", demande.strip()),
                "contexte": llm_result.get("contexte", ""),
                "categorie": llm_result.get("categorie", ""),
                "quantite": llm_result.get("quantite") or 1,
                "prix_unitaire": llm_result.get("prix_unitaire", ""),
                "montant_total": llm_result.get("montant_total", ""),
                "date_souhaitee": llm_result.get("date_mise_en_service", ""),
                "site": llm_result.get("site", ""),
                "local": llm_result.get("local", ""),
                "is_remplacement": llm_result.get("is_remplacement", False),
                "remplacement_info": llm_result.get("remplacement_info", ""),
                "reprise": llm_result.get("reprise", ""),
                "fournisseurs": llm_result.get("fournisseurs", ""),
                "devis_disponible": has_devis,
                "compatibilite": llm_result.get("compatibilite", ""),
                "budget_prevu": llm_result.get("budget_prevu", ""),
                "consommables": llm_result.get("consommables", ""),
                "estimation_consommables": llm_result.get("estimation_consommables", ""),
                "maintenance": llm_result.get("maintenance", ""),
                "has_devis_maintenance": False,
                "estimation_maintenance": llm_result.get("estimation_maintenance", ""),
                "commentaires_budget": llm_result.get("commentaires_budget", ""),
                "subside": llm_result.get("subside", ""),
                "nb_patients": llm_result.get("nb_patients", ""),
                "code_inami": llm_result.get("code_inami", ""),
                "montant_inami": llm_result.get("montant_inami", ""),
                "pct_hopital_inami": llm_result.get("pct_hopital_inami", ""),
                "ressources_humaines": llm_result.get("ressources_humaines", ""),
                "categories_rh": llm_result.get("categories_rh", ""),
                "travaux": llm_result.get("travaux", ""),
                "estimation_travaux": llm_result.get("estimation_travaux", ""),
                "it": llm_result.get("it", ""),
                "estimation_it": llm_result.get("estimation_it", ""),
                "rgpd": llm_result.get("rgpd", ""),
                "sipp": llm_result.get("sipp", ""),
                "hygiene": llm_result.get("hygiene", ""),
                "autres_parties": llm_result.get("autres_parties", ""),
                "nom_demandeur": llm_result.get("nom_demandeur", ""),
                "motivation": llm_result.get("motivation", ""),
                "rentabilite": llm_result.get("rentabilite", ""),
            }

            fla_data = build_fla_data(form_inputs)

            # Écraser motivation/rentabilité avec ceux de Claude (plus intelligents)
            if llm_result.get("motivation"):
                fla_data["motivation"] = llm_result["motivation"]
            if llm_result.get("rentabilite"):
                fla_data["rentabilite"] = llm_result["rentabilite"]

            # Écraser les champs que Claude a rempli et que le moteur a peut-être écrasé
            for key in ["raison", "categorie", "consommables", "maintenance", "it",
                        "rgpd", "travaux", "sipp", "hygiene", "formation", "tests",
                        "site", "local", "remplacement_info", "reprise"]:
                if llm_result.get(key):
                    fla_data[key] = llm_result[key]

            # 5. Générer l'Excel
            excel_bytes = generate_excel(fla_data)

        # --- Résultat : juste le téléchargement ---
        st.success("FLA générée !")

        safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in fla_data.get("objet", "FLA")[:30])
        filename = f"FLA_{safe_name}_{date.today().strftime('%Y%m%d')}.xlsx"

        st.download_button(
            label="Télécharger le fichier Excel complété",
            data=excel_bytes,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True,
        )
