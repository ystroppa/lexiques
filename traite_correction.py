# ------------------------------------------------------------------------------------------------
# Script de traitement et de remise en conformité 
# Lecture du fichier de corection au format csv 
# lecture du répertoire courant pour trouver tous les fichiers avec une extension eaf 
# Y. Stroppa    ASTN/LLL/CNRS 
# Novembre 2023 
# ------------------------------------------------------------------------------------------------
import os
import csv
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
log_file = open("messages.log","w")
log_error_file = open("messages_erreurs.log","w")
_file="CorrectionsAFaire_v1.csv"
# -------------------------------------
# Fonctions utilitaires 
# -------------------------------------
def write_log(*args):
    line = ' '.join([str(a) for a in args])
    log_file.write(line+'\n')


def write_error(*args):
    line = ' '.join([str(a) for a in args])
    log_error_file.write(line+'\n')

def return_key(val,current_dict):
    result=[]
    for elem in current_dict:
        #print(current_dict[elem])
        if "mot" in  current_dict[elem]:
            #print(val+"   "+current_dict[elem]["mot"])
            if current_dict[elem]["mot"]==val:
                result.append(elem)
    return result

# Chargement du fichier des correctifs sous format csv 
corrections=[]

with open(_file, newline='') as csvfile:
    #reader = csv.reader(csvfile, delimiter='#', quoting=csv.QUOTE_NONE)
    reader = csv.reader(csvfile, delimiter='#')
    motif=""
    ligne=dict()
    for row in reader:
        motif_courant=row[0]
        if motif_courant==motif:
            #ligne[row[0]].append([row[1],row[2]])
            ligne[row[0]][row[1]]=row[2]
        else:
            if len(ligne)>0: 
                corrections.append(ligne)
            ligne=dict()
            ligne[row[0]]={}
            ligne[row[0]][row[1]]=row[2]
        motif=motif_courant


# constitution de la cle à partir des differents mb 
def construct_cle(tab_cle):
    elem_c=""
    for elem in tab_cle:
        elem_c+=elem+"/"
    return elem_c[0:-1]

# exemple de modification à effectuer dans  le tableau du fichier  
#           <REF_ANNOTATION ANNOTATION_ID="a510" ANNOTATION_REF="a494">
#                <ANNOTATION_VALUE>nom ?</ANNOTATION_VALUE>
#            </REF_ANNOTATION>
def application_chg(datalignes, ref, nouveau) :
   # recherche la ligne de référence 
   ref_='ANNOTATION_ID="'+ref
   tab_cle=[i+1 for i in range(0,len(datalignes)) if datalignes[i].find(ref_)>0]    
   numero=tab_cle[0]
   #print(tab_cle[0])   # a priori on a une seule ligne
   # transformer la ligne juste en dessous par la nouvelle expression 
   print(datalignes[numero])
   datalignes[numero]="<ANNOTATION_VALUE>"+nouveau+"</ANNOTATION_VALUE>"
   print(datalignes[numero])


# ---------------------------------------------------------------
# Fonction de traitement d'un fichier eaf
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
   tab=_file[2:].split(".")
   output_fichier =tab[0]+"output.json"
   new_file=tab[0]+"_correction.goeaf"
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
   for indice in list(list_enfants_rx):
      for indice2 in list(indice):
         ref_mb= indice2.attrib['ANNOTATION_REF']
         ref_rx= indice2.attrib['ANNOTATION_ID']
         for indice3 in list(indice2):
            valeur= indice3.text
         mb[ref_mb]["ref_rx"]=ref_rx
         mb[ref_mb]["rx_value"]=valeur


   write_log("# Synthèses du nombre des elements: mots, mb, ge et rx")
   write_log("\tnb de mots :" + str(len(list_enfants)))
   write_log("\tnb de mb :" + str(len(list_enfants_mb)))
   write_log("\tnb de ge :" + str(len(list_enfants_ge)))
   write_log("\tnb de rx :" + str(len(list_enfants_rx)))
   
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
   #
   # structure de la variable corrections pour le stockage des éléments
   #   element |- forme trouvée dans eaf || forme de remplacement 
   # {'à': {
   # 'à||*||PL': 'à||gram nominal||PL'], 
   # 'à||pronom||celui\\\\INAN': 'à||pronom||celui\\\\IAN'], 
   # 'à||pronom||3\\\\INDEP":': 'à||pronom||3\\\\INDP":'], 
   # 'à||pronom||3INDF\\\\SUJ': 'à||pronom||INDF\\\\SUJ'], 
   # 'à||pronom||3.INDF\\\\SBJ': 'à||pronom||INDF\\\\SUJ'], 
   # 'à||pronom||3INDEFINI/COLLECTIF\\\\SUJET': 'à||pronom||INDF\\\\SUJ'], 
   # 'à||*||NEG': 'à||gram verbal||NEG'], 
   # 'à||prosod||*': 'à||prosodie||*'], 
   # 'à||TAM||INJONCTIF(2SG)': 'à||*||IMPERATIF (SUJ)'], 
   # 'à||*||OBLIGATION': 'à||*||IMPERATIF (SUJ)'], 
   # 'à||pronom||3\\\\INDEP': 'à||pronom||3\\\\IND']
   # }}
   # autre exemple 
   #{'nə̄': {
   # 'nə̄||*||DEF': 'nə̄||gram nominal||DEF'], 
   # 'nə̄||*||DEFINI': 'nə̄||gram nominal||DEF'], 
   # 'nə̄||pronom||3INAN\\\\ASSO1': 'nə̄||pronom||3\\\\ASSO1'], 
   # 'nə̄||pronom||3INAN': 'nə̄||pronom||3\\\\ASSO1'], 
   # 'nə̄||pronom||3INAN\\\\CMPL': 'nə̄||pronom||3\\\\ASSO1'], 
   # 'nə̄||pronom||ASSO': 'nə̄||pronom||3\\\\ASSO1'], 
   # 'nə̄||pronom||3\\\\INDEP': 'nə̄||pronom||3\\\\IND']
   # }}
   # on peut poursuivre avec les corrections 
   #print(mots.keys())
   # pour chaque resultat il faut extraire la combinaison mb_value+"||"+rx_value + "||" + ge_value
   for correc in corrections:
       for motif in correc.keys():
         resultats=return_key(motif,mots)
         if len(resultats)>0:    # motif trouve dans les mots
             # on peut avoir plusieurs valeurs de mb et detail est un tableau
             for res in resultats:
               #print(mots[res])
               el_courant=mots[res]
               # regarder si on a plusieurs mb 
               if len(el_courant["mb"].keys())> 1 : 
                  print("***************   plusieurs mb a traiter ***************************************")   
               else: 
                  mb_=el_courant["mb"]
                  mb_ref=list(mb_.keys())
                  mb_value=list(mb_.values())
                  #il faut explorer le tableau detail et controler chaque entree : reconstruire la combi qu'il faut comparer
                  for det in el_courant["detail"]:
                     combi=det["mb_value"]+"||"+det["rx_value"] + "||" + det["ge_value"]
                     ref_rx=det["ref_rx"]
                     ref_ge=det["ref_ge"]
                     #print(combi)
                     #print(correc)
                     # si pas conforme il faut changer les réf 
                     if combi in correc[motif]:
                        write_log(ref_rx + "   " + ref_ge )
                        write_log("changement :" , combi +" --> " +  correc[motif][combi])
                        tab_correc=correc[motif][combi].split("||")
                        write_log("\tchangement :" , ref_rx +" --> " +  tab_correc[1])
                        application_chg(Data_lignes, ref_rx, tab_correc[1])
                        write_log("\tchangement :" , ref_ge +" --> " +  tab_correc[2])
                     else: 
                        print("Pas trouve :" , combi +" --> ")

   print("***************   Fin  de traitement fichier ********************") 
   # on peut ecrire la nouvelle version du fichier  
   with open(new_file, 'w') as f:
    for line in Data_lignes:
        f.write(f"{line}\n")
   

   #print(corrections[0])
# resultat obtenu :
# nə̄
# ['a163', 'a169', 'a179', 'a187', 'a192', 'a200', 'a203', 'a215', 'a223', 'a226', 'a232', 'a235', 'a242', 'a247', 'a250', 'a256', 'a260', 'a263', 'a266', 'a270', 'a274', 'a280', 'a284', 'a293', 'a312', 'a315', 'a319', 'a340', 'a357', 'a365', 'a373']

# ---------------
# ETAPE 1 
# ---------------

# ----------------------------------------------------------------------------------------------
# partie principale de traitement : liste de tous les fichiers et appel du traitement de chacun 
# à la lecture des fichiers, on complète la structure globale : forme_cumul_unicite
# ----------------------------------------------------------------------------------------------
path = r'./*.eaf'
dir_list=glob.glob(path)
#print(corrections)
for fichier in dir_list:
   fonction_traitement(fichier)


