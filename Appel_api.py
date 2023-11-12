import requests
import pandas as pd
import time
import datetime
import streamlit as st
import os

st.sidebar.title('Outil de recherche TAG')
headers={"referer":"https://data.mobilites-m.fr/donnees"}
tool=st.sidebar.selectbox('Choix du mode de recherche',options=['Ligne et arrêt','Carte'])
if tool=='Ligne et arrêt':
    st.markdown('Cet outil permet de rechercher pour une ligne et un arrêt le prochain transport qui passera')
    


    network=st.selectbox('Réseau',['Tram','Chrono','Flexo','Proximo'])


    if network != 'Proximo':
        response=requests.get("https://data.mobilites-m.fr/api/routers/default/index/routes?reseaux="+network.upper(),headers=headers)
        list_ligne={}
        for item in response.json():
            list_ligne[item['shortName']]=item['id']
    else:
        list_ligne={'12':'SEM:12','13':'SEM:13','14':'SEM:14','15':'SEM:15','16':'SEM:16','19':'SEM:19','20':'SEM:20','21':'SEM:21','22':'SEM:22','23':'SEM:23','25':'SEM:25','26':'SEM:26'}     
    
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
                occupancy=None
                try:
                    occupancy=item['times'][0]['occupancy'].lower()
                except:
                    pass
                seconds_bus=item['times'][0]['realtimeArrival']
                minutes, seconds = divmod(seconds_bus, 60)
                hours, minutes = divmod(minutes, 60)
                time_arrival="%d:%02d:%02d" % (hours, minutes, seconds)
                t=datetime.datetime.now()
                now_seconds=t.hour*3600+t.minute*60+t.second
                second_to_bus=seconds_bus-now_seconds
                time_to_bus=str(datetime.timedelta(seconds=second_to_bus))
                st.markdown('En direction de {}, à {}, soit dans {}.'.format(terminus,time_arrival,time_to_bus))
                if occupancy!=None:
                    st.markdown('Le nombre de passagers est {}'.format(occupancy.lower()))
                if len(item['times'])>1:
                    st.markdown('Les suivants sont à :')
                    for next_bus in range(1,len(item['times'])):
                        seconds_bus=item['times'][next_bus]['realtimeArrival']
                        minutes, seconds = divmod(seconds_bus, 60)
                        hours, minutes = divmod(minutes, 60)
                        time_arrival="%d:%02d:%02d" % (hours, minutes, seconds)
                        st.markdown(time_arrival)
                
        else:
            st.markdown('Ce transport ne passe pas')

elif tool=='Carte':

    if 'List_all_stops.csv' not in os.listdir():
        all_transports=['C1','C2','C3','C4','C5','C6','C7','A','B','C','D','E']
        List_all_stops=pd.DataFrame()
        for transport in all_transports:
            response=requests.get("https://data.mobilites-m.fr/api/routers/default/index/routes/SEM:"+transport+"/clusters",headers=headers)
            for item in response.json():
                List_all_stops.loc[item['name'],'Code']=item['code']
                List_all_stops.loc[item['name'],'lat']=item['lat']
                List_all_stops.loc[item['name'],'lon']=item['lon']

        for i in range(15,74):
            response=requests.get("https://data.mobilites-m.fr/api/routers/default/index/routes/SEM:"+str(i)+"/clusters",headers=headers)
            if response.text!='Unknown route code':
                for item in response.json():
                    List_all_stops.loc[item['name'],'Code']=item['code']
                    List_all_stops.loc[item['name'],'lat']=item['lat']
                    List_all_stops.loc[item['name'],'lon']=item['lon']

        List_all_stops.to_csv('List_all_stops.csv')

    else:
        List_all_stops=pd.read_csv('List_all_stops.csv',header=0,index_col=0)

    st.map(List_all_stops,latitude='lat',longitude='lon',size=10)