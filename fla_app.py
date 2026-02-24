"""
App FLA - Fiche de Lancement d'Achat
Interface ultra-simple : 1 champ texte + upload documents + bouton Générer.
Lancer avec : streamlit run fla_app.py
"""

import os
import sys
from pathlib import Path
import streamlit as st
from datetime import date
from dotenv import load_dotenv

# Charger .env depuis le dossier de l'app (pas le cwd)
APP_DIR = Path(__file__).parent
load_dotenv(APP_DIR / ".env", override=True)

# Ajouter le dossier au path pour les imports
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from fla_engine import build_fla_data, generate_summary
from llm_service import (
    extract_facts_from_text,
    generate_motivation,
    generate_rentabilite,
    is_available as llm_available,
)
from document_extractor import extract_from_file
from excel_generator import generate_excel

load_dotenv()

# --- Configuration page ---
st.set_page_config(
    page_title="FLA - Fiche de Lancement d'Achat",
    page_icon="🧪",
    layout="centered",
)

st.title("Fiche de Lancement d'Achat")
st.caption("Laboratoire de biologie clinique — CHR Citadelle, Liège")

# Status LLM
if llm_available():
    st.sidebar.success("Claude API connectée")
else:
    st.sidebar.error("Claude API non disponible")
    st.sidebar.caption("Ajoutez ANTHROPIC_API_KEY dans .env")

# --- Zone de saisie unique ---
st.markdown("")

demande = st.text_area(
    "Décrivez votre demande d'achat",
    height=180,
    placeholder=(
        "Exemple : Je voudrais acheter une centrifugeuse Eppendorf 5430R "
        "pour la section chimie spécialisée. C'est pour remplacer notre ancienne "
        "centrifugeuse de 2015 qui est en panne. Le devis est à 12 500€ TVAC "
        "chez Eppendorf. On a besoin de formation pour le personnel."
    ),
)

# --- Upload de documents ---
uploaded_files = st.file_uploader(
    "Joindre un devis, fiche technique ou capture d'écran (optionnel)",
    type=["pdf", "png", "jpg", "jpeg", "gif", "webp"],
    accept_multiple_files=True,
)

# --- Bouton Générer ---
st.markdown("")

if st.button("Générer la FLA", type="primary", use_container_width=True):
    if not demande.strip() and not uploaded_files:
        st.error("Décrivez votre demande ou uploadez un document.")
    else:
        with st.spinner("Analyse en cours..."):

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

            # 2. Extraire les faits du texte libre via Claude
            facts = extract_facts_from_text(demande.strip(), doc_info_str)

            # 3. Préparer les inputs pour le moteur de règles
            form_inputs = {
                "objet": facts.get("objet", demande.strip()),
                "contexte": facts.get("contexte", ""),
                "categorie": "",
                "quantite": facts.get("quantite") or 1,
                "prix_unitaire": facts.get("prix_unitaire", ""),
                "montant_total": facts.get("montant_total", ""),
                "date_souhaitee": facts.get("date_souhaitee", ""),
                "site": facts.get("site", ""),
                "local": "",
                "is_remplacement": facts.get("is_remplacement", False),
                "remplacement_info": facts.get("remplacement_info", ""),
                "reprise": "",
                "fournisseurs": facts.get("fournisseurs", ""),
                "devis_disponible": has_devis,
                "compatibilite": facts.get("compatibilite", ""),
                "budget_prevu": "",
                "consommables": "",
                "estimation_consommables": "",
                "maintenance": "",
                "has_devis_maintenance": False,
                "estimation_maintenance": "",
                "commentaires_budget": "",
                "subside": "",
                "nb_patients": "",
                "code_inami": "",
                "montant_inami": "",
                "pct_hopital_inami": "",
                "ressources_humaines": "",
                "categories_rh": "",
                "travaux": "",
                "estimation_travaux": "",
                "it": "",
                "estimation_it": "",
                "rgpd": "",
                "sipp": "",
                "hygiene": "",
                "autres_parties": "",
                "nom_demandeur": facts.get("nom_demandeur", ""),
            }

            # 4. Moteur de règles déterministe → tous les champs
            fla_data = build_fla_data(form_inputs)

            # 5. Générer les textes narratifs via Claude (ou fallback)
            fla_data["motivation"] = generate_motivation(
                fla_data["objet"],
                facts.get("contexte", ""),
                fla_data["raison"],
                facts.get("is_remplacement", False),
            )
            fla_data["rentabilite"] = generate_rentabilite(
                fla_data["objet"],
                facts.get("contexte", ""),
                fla_data["categorie"],
                fla_data["montant_total"],
            )

            # 6. Générer l'Excel
            excel_bytes = generate_excel(fla_data)

            # 7. Résumé
            summary = generate_summary(fla_data)

        # --- Affichage résultat ---
        st.success("FLA générée !")
        st.markdown("---")

        st.subheader("Résumé")
        st.markdown(summary)

        with st.expander("Motivation de l'achat"):
            st.write(fla_data["motivation"])
        with st.expander("Rentabilité"):
            st.write(fla_data["rentabilite"])
        with st.expander("Tous les champs remplis"):
            for k, v in fla_data.items():
                if v:
                    st.markdown(f"**{k.replace('_', ' ').title()}** : {v}")

        # Bouton téléchargement
        safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in fla_data["objet"][:30])
        filename = f"FLA_{safe_name}_{date.today().strftime('%Y%m%d')}.xlsx"

        st.markdown("")
        st.download_button(
            label="Télécharger le fichier Excel complété",
            data=excel_bytes,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True,
        )
