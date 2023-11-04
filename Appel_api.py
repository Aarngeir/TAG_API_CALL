import requests
import pandas as pd
import time
import datetime
import streamlit as st

st.sidebar.title('Outil de recherche TAG')

tool=st.sidebar.selectbox('Choix du mode de recherche',options=['Ligne et arrêt','Carte'])
if tool=='Ligne et arrêt':
    st.markdown('Cet outil permet de rechercher pour une ligne et un arrêt le prochain transport qui passera')
    headers={"referer":"https://data.mobilites-m.fr/donnees"}


    network=st.selectbox('Réseau',['Tram','Chrono'])


        
    response=requests.get("https://data.mobilites-m.fr/api/routers/default/index/routes?reseaux="+network.upper(),headers=headers)

    list_ligne={}
    for item in response.json():
        list_ligne[item['shortName']]=item['id']

    ligne=st.selectbox('Ligne',list_ligne.keys())


    response=requests.get("https://data.mobilites-m.fr/api/routers/default/index/routes/"+list_ligne[ligne]+"/clusters",headers=headers)

    list_arret={}
    for item in response.json():
        list_arret[item['name']]=item['code']
    arret=st.selectbox("Arrêt",list_arret.keys())

    if st.button('Valider'):
        response=requests.get("https://data.mobilites-m.fr/api/routers/default/index/clusters/"+list_arret[arret]+"/stoptimes?route="+list_ligne[ligne].replace(':','%3A'),headers=headers)
        if len(response.json())>0:
            st.markdown('A {}, le prochain {} de la ligne {} passe :\n'.format(arret,network,ligne))
            
            for item in response.json():
                
                terminus=item['pattern']['lastStopName']
                occupancy=item['times'][0]['occupancy'].lower()
                seconds_bus=item['times'][0]['realtimeArrival']
                minutes, seconds = divmod(seconds_bus, 60)
                hours, minutes = divmod(minutes, 60)
                time_arrival="%d:%02d:%02d" % (hours, minutes, seconds)
                t=datetime.datetime.now()
                now_seconds=t.hour*3600+t.minute*60+t.second
                second_to_bus=seconds_bus-now_seconds
                time_to_bus=str(datetime.timedelta(seconds=second_to_bus))
                st.markdown('En direction de {}, le transport passera à {}, soit dans {}, et le nombre de passagers est {}'.format(terminus,time_arrival,time_to_bus,occupancy.lower()))
                
        else:
            st.markdown('Ce transport ne passe pas')

elif tool=='Carte':
    pass