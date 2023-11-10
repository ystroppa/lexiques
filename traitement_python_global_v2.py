# ------------------------------------------------------------------------------------------------
# Traitement des données issues des fichiers eaf  de transcription de galla 
# ASTN/LLL/CNRS : Y. Stroppa
# Septembre 2023 
# Objectif du script : 
#  Etape 1 : 
#     Extraire le lexique constitué à partir des fichiers eaf d'annotation produits par ELANPro
#     Lecture de la structure XML au niveau des tag TIER tx, mot, mb, ge et rx
#     Reconstruction des lines entre ces différents éléments pour la reconstruction du lexique 
#  Etape 2 : 
#     Chargement du lexique de référence à partir du ficheir eafl dans une structure appropriée
#  Etape 3: 
#     Comparaison entre les deux lexiques et fourniture de différents fichiers résultats des différences
#     Trois cas sont analysés : cas1: clé multiple 
#                               cas2: mb --> mot 
#                               cas3: mb --> mots 
# ------------------------------------------------------------------------------------------------
# entrée : sur le même répertoire des fichiers avec l'extension eaf 
# sortie : 
#  global_output.json
#  cas1_verif.json           alignement des résultats des deux lexiques pour comparaison
#  cas1_erreurs.json         erreurs dans cette comparaison 
#  cas2_verif.json
#  cas2_erreurs.json
#  cas3_verif.json
#  cas3_erreurs.json
#  messages.log              toutes les sorties console de l'exécution 
# ------------------------------------------------------------------------------------------------
# modifications : 
# 06/11/2023 : génération des clés composites à partir des mb --> mot 
#         il faut recomposer les mb ensemble si ils pointent sur le même mot
#      exemple : 'mot': 'tó', 'mb': {'a925': 'tó', 'a926': 'ʁə́'}, 'cle': 'tó/ʁə́'
# 07/11/2023
#      façon d'explorer les structures XML sans getchildren car deprecated je passe
#      recommandation python : utiliser des list() 
# ------------------------------------------------------------------------------------------------
import os
import sys,getopt
import re
import json
import collections
import numpy as np
import xml.etree.ElementTree as ET
import glob

# -------------------------------------
# Declarations des variables globales 
# -------------------------------------
forme_cumul_unicite={}
log_file = open("messages.log","w")
log_error_file = open("messages_erreurs.log","w")

# -------------------------------------
# Fonctions utilitaires 
# -------------------------------------
def write_log(*args):
    line = ' '.join([str(a) for a in args])
    log_file.write(line+'\n')


def write_error(*args):
    line = ' '.join([str(a) for a in args])
    log_error_file.write(line+'\n')


# constitution de la cle à partir des differents mb 
def construct_cle(tab_cle):
    elem_c=""
    for elem in tab_cle:
        elem_c+=elem+"/"
    return elem_c[0:-1]

# ---------------------------------------------------------------
# Fonction de traitement d'un fichier   eaf
# input : nom du fichier 
# output : alimente la variable forme_cumul_unicite
# ---------------------------------------------------------------
def fonction_traitement(fichier):
   global forme_cumul_unicite
   _file=fichier 
   file = open(_file, encoding="utf8")
   data=file.read()
   file.close()
   write_log("fichier en cours de traitement " + fichier)
   Data_lignes=data.splitlines()
   nb_lignes=len(Data_lignes)
   write_log("nb de lignes " + str(nb_lignes))
   tab=_file.split(".")
   output_fichier =tab[0]+"output.json"
   # ----------------------------------------------------------------------------
   # fonction de traitement des paragraphes des fichiers eaf : tx, mot ....
   # retourne au format texte l'ensemble des lignes correspond à un bloc XML
   # ----------------------------------------------------------------------------
   def fonction_remplir(expression):
      paragraphe_=""
      _a_remplir=1
      expression_=expression+"@"
      for ligne in Data_lignes:
         # pour regler les problèmes avec les fichiers incomplets
         if "TIER_ID" in ligne  and expression_ in ligne and "/>" in ligne:
            paragraphe_=None
            return paragraphe_
         # parcourir le buffer à la rechercher de TIER et LINGUISTIQUE_TYPE_REF="mot"
         if "TIER" in ligne and expression in ligne and expression_ not in ligne:
            paragraphe_+=ligne
            _a_remplir=0
            continue
         #if _a_remplir==0 and ("</TIER>" in ligne or "/>" in ligne):
         if _a_remplir==0 and "</TIER>" in ligne:
            paragraphe_+=ligne
            _a_remplir=1
            return paragraphe_
         if _a_remplir==0:
               paragraphe_+=ligne
   
   # -----------------------------------------------------------
   # chargement de tous les blocs XML dans une structure dédiée 
   # -----------------------------------------------------------
   paragraphe_tx=fonction_remplir("tx")
   paragraphe_mot=fonction_remplir("mot")
   paragraphe_mb=fonction_remplir("mb")
   paragraphe_ge=fonction_remplir("ge")
   paragraphe_rx=fonction_remplir("rx") 
   if paragraphe_mot==None or paragraphe_mb==None or paragraphe_ge==None or paragraphe_rx==None:
      write_log("!!!!!!!!!!!")   
      write_log("problème dans la structure du fichier : il manque des paragraphes")   
      write_log("!!!!!!!!!!!")   
      return   
   
   # -----------------------------------------
   # chargement des expressions de reference "tx"
   # ==> structure tx[cle]--> "ref_mot", "value" 
   # -----------------------------------------
   tree = ET.ElementTree(ET.fromstring(paragraphe_tx))
   root=tree.getroot()
   tx=dict()
   list_enfants_tx=root#.getchildren()
   #for indice in range(0,len(list_enfants_tx)):
   #   ref_mot=list_enfants_tx[indice].getchildren()[0].attrib['ANNOTATION_REF']
   #   ref_ID=list_enfants_tx[indice].getchildren()[0].attrib['ANNOTATION_ID']
   #   valeur=list_enfants_tx[indice].getchildren()[0].getchildren()[0].text
   #   tx[ref_ID]={"ref_mot":ref_mot,"value":valeur}
   #print(tx)
   # reecriture pour eviter les deprecateds avec getchildren()[0]
   for indice in list(list_enfants_tx):
      #print(dir(indice))
      for indice2 in list(indice):
         ref_anno=indice2.attrib['ANNOTATION_REF']
         ref_ID=indice2.attrib['ANNOTATION_ID']
         for indice3 in list(indice2):
            valeur=indice3.text
         tx[ref_ID]={"ref_annotation":ref_anno,"value":valeur}
   #print(tx)
   
   # -----------------------------------------------------------------------------------------
   # chargement des expressions de reference "mot"
   # ==> structure mots[cle]--> "mot":valeur, "mb":{}
   # si on a plusieurs formes identiques tó définies plusieurs fois, donc pour une même forme 
   # on stocke les mb 
   # -----------------------------------------------------------------------------------------
   tree = ET.ElementTree(ET.fromstring(paragraphe_mot))
   root=tree.getroot()
   mots=dict() 
   list_enfants=root#.getchildren()
   for indice in list(list_enfants):
      for indice2 in list(indice):
         ref_=indice2.attrib['ANNOTATION_REF']
         ref_mot= indice2.attrib['ANNOTATION_ID']
         for indice3 in list(indice2):
            valeur= indice3.text
         mots[ref_mot]={"mot":valeur,"ref":ref_}
         mots[ref_mot]["mb"]={}

   # ----------------------------------------------
   # chargement des expressions de reference "mb"
   # ==> structure mb[cle]--> "ref_mot":valeur, "mb_value":{}
   #   et on complete mots[ref_mot]["mb"][ref_mb]=valeur
   #      on ajoute la référence de mb 
   # ----------------------------------------------
   tree = ET.ElementTree(ET.fromstring(paragraphe_mb))
   root=tree.getroot()
   mb=dict() 
   list_enfants_mb=root#.getchildren()
   #for indice in range(0,len(list_enfants_mb)):
   #   ref_mot= list_enfants_mb[indice].getchildren()[0].attrib['ANNOTATION_REF']
   #   ref_mb= list_enfants_mb[indice].getchildren()[0].attrib['ANNOTATION_ID']
   #   valeur= list_enfants_mb[indice].getchildren()[0].getchildren()[0].text
   #   mb[ref_mb]={"ref_mot":ref_mot,"mb_value":valeur}
   # il faut memoriser egalement le lien mot -- mb pour la recomposition et voir si il y a plusieus mb pour un même mot 
   #   mots[ref_mot]["mb"][ref_mb]=valeur

   for indice in list(list_enfants_mb):
      for indice2 in list(indice):
         ref_mot= indice2.attrib['ANNOTATION_REF']
         ref_mb= indice2.attrib['ANNOTATION_ID']
         for indice3 in list(indice2):
            valeur= indice3.text
         mb[ref_mb]={"ref_mot":ref_mot,"mb_value":valeur}
         # il faut memoriser egalement le lien mot -- mb pour la recomposition et voir si il y a plusieus mb pour un même mot 
         mots[ref_mot]["mb"][ref_mb]=valeur


   # ------------------------------------------------------------------
   # chargement des expressions de reference "ge" dans la structure mb 
   # -----------------------------------------------------------------
   tree = ET.ElementTree(ET.fromstring(paragraphe_ge))
   root=tree.getroot()
   list_enfants_ge=root#.getchildren()
   #for indice in range(0,len(list_enfants_ge)):
   #   ref_mb= list_enfants_ge[indice].getchildren()[0].attrib['ANNOTATION_REF']
   #   ref_ge= list_enfants_ge[indice].getchildren()[0].attrib['ANNOTATION_ID']
   #   valeur= list_enfants_ge[indice].getchildren()[0].getchildren()[0].text
   #   mb[ref_mb]["ref_ge"]=ref_ge
   #   mb[ref_mb]["ge_value"]=valeur

   for indice in list(list_enfants_ge):
      for indice2 in list(indice):
         ref_mb= indice2.attrib['ANNOTATION_REF']
         ref_ge= indice2.attrib['ANNOTATION_ID']
         for indice3 in list(indice2):
            valeur= indice3.text
         mb[ref_mb]["ref_ge"]=ref_ge
         mb[ref_mb]["ge_value"]=valeur


   # ------------------------------------------------------------------
   # chargement des expressions de reference "rx" dans la structure mb 
   # -----------------------------------------------------------------   
   tree = ET.ElementTree(ET.fromstring(paragraphe_rx))
   root=tree.getroot()
   list_enfants_rx=root#.getchildren()
   #for indice in range(0,len(list_enfants_rx)):
   #   ref_mb= list_enfants_rx[indice].getchildren()[0].attrib['ANNOTATION_REF']
   #   ref_rx= list_enfants_rx[indice].getchildren()[0].attrib['ANNOTATION_ID']
   #   valeur= list_enfants_rx[indice].getchildren()[0].getchildren()[0].text
   #   mb[ref_mb]["ref_rx"]=ref_rx
   #   mb[ref_mb]["rx_value"]=valeur
   #print(mb)

   for indice in list(list_enfants_rx):
      for indice2 in list(indice):
         ref_mb= indice2.attrib['ANNOTATION_REF']
         ref_rx= indice2.attrib['ANNOTATION_ID']
         for indice3 in list(indice2):
            valeur= indice3.text
         mb[ref_mb]["ref_rx"]=ref_rx
         mb[ref_mb]["rx_value"]=valeur


   # affichage des synthèses du nombre des elements
   write_log("nb de mots :" + str(len(list_enfants)))
   write_log("nb de mb :" + str(len(list_enfants_mb)))
   write_log("nb de ge :" + str(len(list_enfants_ge)))
   write_log("nb de rx :" + str(len(list_enfants_rx)))
   
   # --------------------------------------------------
   # Analyse et construction des cles si besoin 
   # --------------------------------------------------
   # afficher les mots pour lesquels le nombre de mb est supérieur à 1 
   # pour constituer de nouvelles cles 
   # --------------------------------------------------
   for mot in mots:
       if len(mots[mot]["mb"])>1:  # plusieurs mb il faut composer la CLE 
            tab_cle=[mots[mot]["mb"][i] for i in mots[mot]["mb"].keys()]
            Cle= construct_cle(tab_cle)
            mots[mot]["cle"]=Cle
            #print("----"+mot+"------\n")
            mots[mot]["detail"]=[]
            tab_que_cle=[i for i in mots[mot]["mb"].keys()]
            for nb_ele in range(0,len(tab_que_cle)):
               mots[mot]["detail"].append(mb[tab_que_cle[nb_ele]])
            #print(mots[mot])
       else:                      # la cle c'est MB 
            k=[i for i in mots[mot]["mb"].keys()]
            #print("----"+mot+"------\n")
            if len(k)>0:
                Cle=mb[k[0]]["mb_value"]
                mots[mot]["detail"]=[]
                mots[mot]["detail"].append(mb[k[0]])
                mots[mot]["cle"]=Cle
                #print(mots[mot])
            else:
                write_log("mots sans info mb "+  mot)

   # on a fini de completer la structure mots avec les éléments complémentaires mb, ge, rx
   # cas recomposition de la clé 
   # {'mot': 'to᷄', 'ref':'a151', 'mb': {'a2235': 'tō', 'a2236': 'ʁə́'}, 
   #               'cle': 'tō/ʁə́', 
   #           'detail': [
   #                   {'ref_mot': 'a616', 'mb_value': 'tō', 'ref_ge': 'a2251', 'ge_value': 'dire\\M', 'ref_rx': 'a2267', 'rx_value': 'verbe'}, 
   #                   {'ref_mot': 'a616', 'mb_value': 'ʁə́', 'ref_ge': 'a2252', 'ge_value': '3INAN\\CMPL', 'ref_rx': 'a2268', 'rx_value': 'pronom'}
   #           ]
   # }
   # cas simple : un seul mb 
   # {'mot': 'kə́', 'ref':'a152', 'mb': {'a2244': 'kə́'}, 
   #               'detail': [{'ref_mot': 'a624', 'mb_value': 'kə́', 'ref_ge': 'a2260', 'ge_value': 'TAM', 'ref_rx': 'a2276', 'rx_value': '*'}], 
   #               'cle': 'kə́'
   # }

   # traitement des donnees du fichier en cours et stockage dans la structure globale forme_cumul_unicite
   # on relit la structure mots et on stocke les éléments en fonction de la clé trouvée 
   for m_ in mots:
      mot=mots[m_]
      #print(mot)
      if "cle" in mot: 
         Cle=mot["cle"]
         if Cle==None:
            continue
         if Cle not in forme_cumul_unicite: 
            forme_cumul_unicite[Cle]={} 
            forme_cumul_unicite[Cle]["mot"]={} 
         if mot["mot"] not in forme_cumul_unicite[Cle]["mot"]:
            forme_cumul_unicite[Cle]["mot"][mot["mot"]]=dict()
            forme_cumul_unicite[Cle]["mot"][mot["mot"]]["expression"]=[]
            forme_cumul_unicite[Cle]["mot"][mot["mot"]]["gloss"]=dict()
         # on stocke l'expression associée au mot 
         forme_cumul_unicite[Cle]["mot"][mot["mot"]]["expression"].append(tx[mot["ref"]]["value"]+"||"+fichier)
         # il faut regarder le contenu du tableau detail associé au mot 
         #cle=version["mb_value"]+version["ge_value"]+rx_value
         for ind_detail in range(0,len(mot["detail"])):
            version=mot["detail"][ind_detail]
            if "rx_value" not in version or "ge_value" not in version:
               #print(version)
               write_log("probleme de structure manque rx ou ge")
               continue            
            rx_value=version["rx_value"]
            if version["rx_value"]==None:
               rx_value='None'
            ge_value=version["ge_value"]
            if version["ge_value"]==None:
               ge_value="None"
            #print(version["mb_value"])               
            mb_value=version["mb_value"]
            if version["mb_value"]==None:
               mb_value="None"
            cle_detail=mb_value+"||"+rx_value + "||" + ge_value
            if cle_detail not in forme_cumul_unicite[Cle]["mot"][mot["mot"]]["gloss"]:
               forme_cumul_unicite[Cle]["mot"][mot["mot"]]["gloss"][cle_detail]=1
            else:
               forme_cumul_unicite[Cle]["mot"][mot["mot"]]["gloss"][cle_detail]+=1

# ---------------
# ETAPE 1 
# ---------------

# ----------------------------------------------------------------------------------------------
# partie principale de traitement : liste de tous les fichiers et appel du traitement de chacun 
# à la lecture des fichiers, on complète la structure globale : forme_cumul_unicite
# ----------------------------------------------------------------------------------------------
path = r'./*.eaf'
dir_list=glob.glob(path)
for fichier in dir_list:
   fonction_traitement(fichier)

with open("global_output.json", "w", encoding='utf8') as outfile:
   json.dump(forme_cumul_unicite,outfile,ensure_ascii=False,indent=4)

# ---------------
# ETAPE 2
# ---------------

# ------------------------------------------------
# lecture du lexique et chargement dans lexique 
# ------------------------------------------------
f_lexique = open("./lexique_ngbg.eafl", encoding="utf8")
lexique=f_lexique.read()
f_lexique.close()

Lexique_lignes=lexique.splitlines()  
# chargement du lexique dans la structure correspondante 
lexique_struc=dict()
"""
type d'entree dans le fichier lexique eafl en exemple 
  <lexicalEntry id="2275" dt="06/Mar/2023">
    <Lexeme typ="lem">fʁō</Lexeme>
    <sense>
      <Gloss lang="en" der="M" tierX="verbe">frotter</Gloss>
    </sense>
    <form />
  </lexicalEntry>
  <lexicalEntry id="2276" dt="06/Mar/2023">
    <Lexeme typ="wf">jě</Lexeme>
    <form />
    <sense />
    <morph>
      <Segment ref="948">jì</Segment>
      <Segment ref="82">ʁə́</Segment>
    </morph>
  </lexicalEntry>
"""
def traite_localEntre(bloc_local_entry):
    # chargement d'une entree dans lexique_struc, l'entree est une chaine de caractères 
   tree = ET.ElementTree(ET.fromstring(bloc_local_entry))
   root=tree.getroot()
   local_entry=root
   for indice in range(0,len(local_entry)):  
      if  local_entry[indice].tag=="Lexeme":
         # si lexeme --> text 
         lexeme=local_entry[indice].text
         lexique_struc[lexeme]=dict()
      elif  local_entry[indice].tag=="sense":
         # si sense ==> Gloss -->  attribut:tierX et text 
         gloss=local_entry[indice]
         lexique_struc[lexeme]["gloss"]=[]
         for ind_gloss in range(0,len(gloss)):
            tierX=gloss[ind_gloss].attrib['tierX']
            text=gloss[ind_gloss].text
            der=""
            if "der" in gloss[ind_gloss].keys():
               print(dir(gloss[ind_gloss]))
               der="\\"+ gloss[ind_gloss].attrib['der']
            lexique_struc[lexeme]["gloss"].append({"tierX":tierX, "text":text+der})
      elif  local_entry[indice].tag=="morph":
         # si morph ==> Segment --> text 
         morph=local_entry[indice]
         lexique_struc[lexeme]["segments"]=[]
         for ind_morph in range(0,len(morph)):
            ref=morph[ind_morph].text
            lexique_struc[lexeme]["segments"].append(ref)
      elif  local_entry[indice].tag=="form":
         # si form ==> altForm ==> WForm --> text
         form=local_entry[indice]
         lexique_struc[lexeme]["altForms"]=[]
         for ind_form in range(0,len(form)):
            altForm=form[ind_form]
            for ind_altform in range(0,len(form[ind_form])):
               elem=altForm[ind_altform].text
               lexique_struc[lexeme]["altForms"].append(elem)

_a_remplir=1
paragraphe_=""
for ligne in Lexique_lignes:
      if "<lexicalEntry" in ligne:
         paragraphe_+=ligne
         _a_remplir=0
         continue
      if "</lexicalEntry>" in ligne:
         paragraphe_+=ligne
         _a_remplir=1
         traite_localEntre(paragraphe_)
         paragraphe_=""
      if _a_remplir==0:
            paragraphe_+=ligne

# ---------------
# ETAPE 3
# ---------------

# -----------------------------------------------------------------------
# comparaison structure lexique reconstitue avec le lexique référence 
# -----------------------------------------------------------------------
# prendre les différents éléments de la structure cumulative forme_cumul_unicite et la comparer 
# au lexique : lexique_struc
# on a trois cas :
# On va créer les structures CAS1, CAS2 et CAS3 pour stocker les différentes situations 
CAS1=[]
CAS1_erreurs=dict()  # on va indexer par nature de l'erreur 
CAS1_erreurs["CAS1_error_1"]={"description":"Absent du lexique", "errors":[]}
cas1_errors1=CAS1_erreurs["CAS1_error_1"]["errors"]
CAS1_erreurs["CAS1_error_2"]={"description":"Pas de segment dans le lexique", "errors":[]}
cas1_errors2=CAS1_erreurs["CAS1_error_2"]["errors"]
CAS1_erreurs["CAS1_error_3"]={"description":"Comparaison non conforme", "errors":[]}
cas1_errors3=CAS1_erreurs["CAS1_error_3"]["errors"]

CAS2=[]
CAS2_erreurs=dict()
CAS2_erreurs["CAS2_error_1"]={"description":"Absent du lexique", "errors":[]}
cas2_errors1=CAS2_erreurs["CAS2_error_1"]["errors"]
CAS2_erreurs["CAS2_error_2"]={"description":"Pas de gloss", "errors":[]}
cas2_errors2=CAS2_erreurs["CAS2_error_2"]["errors"]
CAS2_erreurs["CAS2_error_3"]={"description":"Comparaison non conforme", "errors":[]}
cas2_errors3=CAS2_erreurs["CAS2_error_3"]["errors"]

CAS3=[]
CAS3_erreurs=dict()
CAS3_erreurs["CAS3_error_1"]={"description":"Absent du lexique", "errors":[]}
cas3_errors1=CAS3_erreurs["CAS3_error_1"]["errors"]
CAS3_erreurs["CAS3_error_2"]={"description":"Pas de gloss", "errors":[]}
cas3_errors2=CAS3_erreurs["CAS3_error_2"]["errors"]
CAS3_erreurs["CAS3_error_3"]={"description":"Comparaison liste mots non conforme", "errors":[]}
cas3_errors3=CAS3_erreurs["CAS3_error_3"]["errors"]
CAS3_erreurs["CAS3_error_4"]={"description":"Comparaison gloss non conforme", "errors":[]}
cas3_errors4=CAS3_erreurs["CAS3_error_4"]["errors"]

for entree_lex_recomp in forme_cumul_unicite:
   if len (entree_lex_recomp)>1 and "/" in entree_lex_recomp:  # on peut avoir plusieurs / dans une expression
      # cas 1 composite --> plusieurs mots
      cas1="" # "cas 1: entree composite"
      tab_=entree_lex_recomp.split("\\")
      # on cherche tous les mots associés
      a_verif=[i for i in forme_cumul_unicite[entree_lex_recomp]["mot"].keys()]
      # et pour chaque mot il faut vérifier dans le lexique qu'il est fourni avec les différents segments
      for mot in a_verif:
         if mot in lexique_struc:
            if "segments" in lexique_struc[mot]:
               ref_lexique_recompose=""
               for ref1 in lexique_struc[mot]["segments"]:
                  ref_lexique_recompose+=ref1
               mb_recomposite=entree_lex_recomp.replace("/","")
               if (mb_recomposite==ref_lexique_recompose):
                  CAS1.append({"mb_composite":mb_recomposite,"mot":mot,"Ref_lexique_segments":ref_lexique_recompose})
               else:
                  cas1_errors3.append({"mb_composite":mb_recomposite,"Ref_lexique_segments":ref_lexique_recompose,"entree":mot})   
            else:
               cas1_errors2.append({"mb_composite":entree_lex_recomp,"entree":mot})
         else:
            cas1_errors1.append({"mb_composite":entree_lex_recomp,"entree":mot})
   else : 
      long=len(forme_cumul_unicite[entree_lex_recomp]["mot"])
      if long==1:
         # cas 2 simple --> un seul mot 
         if entree_lex_recomp in lexique_struc:
            if "gloss" not in  lexique_struc[entree_lex_recomp]:
               cas2_errors2.append({"type":"Pas de gloss","entree":entree_lex_recomp})
            else: 
               verif_ref=""
               for ref1 in lexique_struc[entree_lex_recomp]["gloss"]:
                  verif_ref+=ref1["tierX"]+"||" +ref1["text"]+"||"
               #verif_ref=lexique_struc[entree_lex_recomp]["gloss"]["tierX"]+"||" +lexique_struc[entree_lex_recomp]["gloss"]["text"]             
               a_verif=""
               for key in forme_cumul_unicite[entree_lex_recomp]["mot"].keys():
                  a_verif=forme_cumul_unicite[entree_lex_recomp]["mot"][key]["gloss"]
               #CAS2.append({"mb":entree_lex_recomp,"gloss_recompose":a_verif,"gloss_lexique":verif_ref})
               # il faut comparer les resultats des gloss ensemble entre les deux lexiques 
               #  {
               #  "mb": "ɛ̄ʃē",
               #   "gloss_recompose": {"ɛ̄ʃē||nom||femme": 2},
               #   "gloss_lexique": "nom||femme||"
               #   },
               # il faut prendre chaque gloss et verifier si ils sont presents dans verif_ref sans la première partie
               presents=True
               for key_gloss in a_verif:
                  ch=""
                  tab_gloss=key_gloss.split("||")
                  for to in range(1,len(tab_gloss)):
                     ch+=tab_gloss[to]+"||"
                  if verif_ref.find(ch)!=0:
                     presents=False
               if presents==False:
                  cas2_errors3.append({"entree":entree_lex_recomp,"gloss_recompose":a_verif,"gloss_lexique":verif_ref})      
               else: 
                  CAS2.append({"mb":entree_lex_recomp,"gloss_recompose":a_verif,"gloss_lexique":verif_ref})
         else:
            cas2_errors1.append({"entree":entree_lex_recomp})
      else: 
         # cas 3 simple --> plusieurs mots
         if entree_lex_recomp in lexique_struc:
            # il faut les altForms et ajouter l'entree pour etre exhaustif
            verif_alforms=lexique_struc[entree_lex_recomp]["altForms"]
            verif_alforms.append(entree_lex_recomp)
            verif_ref=""
            if "gloss" not in  lexique_struc[entree_lex_recomp]:
               #print("C3=>Erreur pas de gloss dans le lexique pour : " + entree_lex_recomp )
               cas3_errors2.append({"entree":entree_lex_recomp})
            else: 
               # attention on peut avoir plusieurs gloss pour une même entrée
               gloss_ref=""
               for ref1 in lexique_struc[entree_lex_recomp]["gloss"]:
                  gloss_ref+=ref1["tierX"]+"||" +ref1["text"]+"||"
               gloss_a_verif=set()
               a_verif=[i for i in forme_cumul_unicite[entree_lex_recomp]["mot"].keys()]
               for cles in a_verif: # on peut avoir plusieurs cles et pour chaque cle plusieurs gloss
                  tab_=[i for i in forme_cumul_unicite[entree_lex_recomp]["mot"][cles]["gloss"].keys()]
                  for ele in tab_:
                     gloss_a_verif.add(ele)
               #CAS3.append({"mb":entree_lex_recomp,"liste_mots_recomposee":a_verif,"liste_mots_lexique":verif_alforms,"Gloss_recompose":list(gloss_a_verif),"Gloss_lexique":gloss_ref})
               # plusieurs cas a verifier : 
               # chaque element de la liste a_verif est present dans verif_alforms
               presents=True
               for mot in a_verif:
                  if mot not in verif_alforms:
                     presents=False
               if presents==False:
                  cas3_errors3.append({"entree":entree_lex_recomp,"liste_mots_recomposee":a_verif,"liste_mots_lexique":verif_alforms})
               else: # verification des gloss  gloss_a_verif --> gloss_ref 
                  presents_Gloss=True
                  for key_gloss in gloss_a_verif:
                     ch=""
                     tab_gloss=key_gloss.split("||")
                     for to in range(1,len(tab_gloss)):
                        ch+=tab_gloss[to]+"||"
                     if gloss_ref.find(ch)!=0:
                        presents_Gloss=False
                  if presents_Gloss==False:
                     cas3_errors4.append({"entree":entree_lex_recomp,"gloss_recompose":list(gloss_a_verif),"gloss_lexique":gloss_ref})      
                  else: 
                     CAS3.append({"mb":entree_lex_recomp,"liste_mots_recomposee":a_verif,"liste_mots_lexique":verif_alforms,"Gloss_recompose":list(gloss_a_verif),"Gloss_lexique":gloss_ref})
         else:
            cas3_errors1.append({"entree":entree_lex_recomp})

# Ecriture des resultats pour les recombinaisons de MB 
with open("cas1_verif.json", "w", encoding='utf8') as outfile:
   json.dump(CAS1,outfile,ensure_ascii=False,indent=4)
with open("cas1_erreurs.json", "w", encoding='utf8') as outfile:
   json.dump(CAS1_erreurs,outfile,ensure_ascii=False,indent=4)

# Ecriture des resultats pour les cas simples mb --> mot  
with open("cas2_verif.json", "w", encoding='utf8') as outfile:
   json.dump(CAS2,outfile,ensure_ascii=False,indent=4)
with open("cas2_erreurs.json", "w", encoding='utf8') as outfile:
   json.dump(CAS2_erreurs,outfile,ensure_ascii=False,indent=4)

# Ecriture des resultats pour les cas multiple  mb --> plusieurs mots  
with open("cas3_verif.json", "w", encoding='utf8') as outfile:
   json.dump(CAS3,outfile,ensure_ascii=False,indent=4)
with open("cas3_erreurs.json", "w", encoding='utf8') as outfile:
   json.dump(CAS3_erreurs,outfile,ensure_ascii=False,indent=4)


