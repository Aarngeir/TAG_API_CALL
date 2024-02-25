import requests
import pandas as pd
import time
import datetime
from Itinerary import create_list_all_stops,create_graph,create_list_arret, find_shortest_path
import streamlit as st
import json
import os
import numpy as np
import heapq
import pytz
import plotly.express as px
from geopy.distance import geodesic
from fuzzywuzzy import fuzz,process
from Ligne_et_arret import get_list_ligne, get_list_arret,get_next_transport

#https://medium.com/@nilufarmohammadi1/find-the-best-route-with-openstreetmap-using-python-da70eff5b1ac



st.sidebar.title('Outil de recherche TAG')
headers={"referer":"https://data.mobilites-m.fr/donnees"}

tool=st.sidebar.selectbox('Choix du mode de recherche',options=['Ligne et arrêt','Itinéraire'])
if tool=='Ligne et arrêt':
    st.markdown('Cet outil permet de rechercher pour une ligne et un arrêt le prochain transport qui passera')
    


    network=st.selectbox('Réseau',['Tram','Chrono','Flexo','Proximo'])
    
    list_ligne=get_list_ligne(network,headers)
         
    
    ligne=st.selectbox('Ligne',list_ligne.keys())

    dis_list_arret, list_arret=get_list_arret(list_ligne,ligne,headers)
    
    arret=st.selectbox("Arrêt",dis_list_arret)

    if st.button('Valider') and arret!='':
        
        df = get_next_transport(list_arret,arret,list_ligne,ligne,headers)
        
        if len(df)!=0:
            st.markdown('A {}, le prochain {} de la ligne {} passe :\n'.format(arret,network,ligne))
            for i in range(len(df)):
                st.markdown('En direction de {}, à {}, soit dans {}.'.format(df.loc[i,'Terminus'].upper(),df.loc[i,'Time'],df.loc[i,'Remaining']))
                if df.loc[i,'Occupancy']!=None:
                    st.markdown('Le nombre de passagers est {}'.format(df.loc[i,'Occupancy'].lower()))

                t_cols=[j for j in df.columns if j not in ['Terminus','Time','Remaining','Occupancy']]
                st.markdown('Les suivants sont à :')
                for j,col in enumerate(t_cols):
                    if pd.isna(df.loc[i,col])==False and j<3:
                        st.markdown(df.loc[i,col])
        else:
            st.markdown("Le transport ne passe pas.")

elif tool=='Itinéraire':

    List_all_stops=create_list_all_stops(headers)
    graph=create_graph(List_all_stops)

    
    dis_list_arret=create_list_arret(List_all_stops)
    
    full_address = st.selectbox("Entrez un arrêt de départ",dis_list_arret)
    
    full_destination = st.selectbox("Entrez un arrêt de destination",dis_list_arret)
    Calc_iti=st.button("Calculer l'itinéraire")
    
    if full_address!='' and full_destination!='' and Calc_iti:
        
        shortest, line = find_shortest_path(full_address, full_destination, List_all_stops, graph)
        st.markdown('Le chemin le plus court est le suivant :')
        for i in range(len(shortest)-1):
            st.markdown('Prendre la ligne {} à {} et descendre à {}'.format(line[i],shortest[i],shortest[i+1]))

        # if len(closest_stops)!=0 and False:
        #     st.markdown('Les arrêts contenus dans un rayon de {} mètres sont les suivants :'.format(radius))
        #     closest_index=list(list(zip(*closest_stops))[0])
            
        #     #On gère l'affichage sur la carte
        #     fig=px.scatter_mapbox(List_all_stops.loc[closest_index],lat='lat',lon='lon',text=List_all_stops.loc[closest_index,'name'],width=800, height=800)
        #     fig.update_traces(marker=dict(color='green',size=15))
        #     fig.update_layout(mapbox_style="open-street-map")
        #     fig.add_trace(px.scatter_mapbox(lat=[lat_input], lon=[lon_input]).data[0])
        #     fig.update_layout(mapbox=dict(center=dict(lat=lat_input, lon=lon_input),zoom=15))
        #     st.plotly_chart(fig,use_container_witdh=True)
        # elif len(closest_stops)==0 and False:
        #     st.markdown('Aucun arrêt dans les {} mètres'.format(radius))