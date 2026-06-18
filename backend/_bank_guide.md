# Banque originale de 200 items cognitifs — usage non clinique

Version: 1.0  
Date: 2026-06-17  
Langue: fr-FR  
Nombre d'items: 200

## Positionnement
Cette banque est une création originale pour application, entraînement ou test d'entrée non clinique. Elle s'inspire de grands domaines cognitifs couramment évalués en psychologie cognitive: compréhension verbale, raisonnement visuo-spatial, raisonnement fluide, mémoire de travail et vitesse de traitement/attention.

Elle ne reproduit pas le WAIS, ne remplace pas une passation encadrée et ne permet pas de calculer un QI clinique.

## Sources utilisées pour cadrer les domaines, pas pour copier des items
- Pearson France WAIS-IV: https://www.pearsonclinical.fr/wais-iv
- Pearson US WAIS-5 overview: https://www.pearsonassessments.com/en-us/Store/Professional-Assessments/Cognition-%26-Neuro/Wechsler-Adult-Intelligence-Scale-%7C-Fifth-Edition/p/P100071002
- Brochure WAIS-5: https://www.pearsonassessments.com/content/dam/school/global/clinical/us/assets/wais-5/wais-5-overview-brochure.pdf
- Recommandations Pearson France WAIS-IV à distance: https://www.pearsonclinical.fr/media/wysiwyg/FR_guidelines_WAIS_IV.pdf

## Recommandation d'affichage dans l'application
Texte conseillé: "Ce test est un parcours cognitif indicatif. Il ne s'agit pas du WAIS, ne remplace pas une évaluation psychologique et ne fournit pas de QI clinique. Les résultats décrivent uniquement vos réponses aux exercices proposés."

## Scoring conseillé
- Item QCM: 1 point si la clé sélectionnée correspond à `reponse_attendue`, 0 sinon.
- Réponse libre stricte: normaliser casse, espaces et tirets, puis comparer à `reponse_attendue`.
- Ne pas transformer les scores bruts en QI sans étude psychométrique, échantillon normatif, analyses de fidélité/validité et procédure standardisée.

## Contrôles qualité effectués
- 200 items générés.
- Identifiants uniques.
- Toutes les réponses QCM pointent vers une option existante.
- Aucune option QCM dupliquée dans un même item.
- Réponses attendues non vides.
