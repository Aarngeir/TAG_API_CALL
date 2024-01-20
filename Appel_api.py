import requests
import pandas as pd
import time
import datetime
import streamlit as st
import json
import os
import numpy as np
import heapq
import plotly.express as px
from geopy.distance import geodesic
from fuzzywuzzy import fuzz,process

def closest(lst, K):
    min_abs=100

    for i,j in enumerate(lst):
        if abs(len(j[0])-len(K))<min_abs:
            min_abs=abs(len(j[0])-len(K))
            idx=i
    
    return lst[idx]


def find_closest_coordinates(df, user_lat, user_lon, radius=500):
    close_coordinates = []
    for index, row in df.iterrows():
        distance = geodesic((user_lat, user_lon), (row['lat'], row['lon'])).meters
        if distance <= radius:
            close_coordinates.append((index,row['lat'], row['lon']))
    return close_coordinates

def geocode_nominatim(grenoble_lat, grenoble_lon, query):
    base_url = "https://nominatim.openstreetmap.org/search"

    params = {
        'format': 'json',
        'q': query,
        'county': 'Isère',
        'limit': 10
    }

    headers = {
        'User-Agent': 'votre-application'  # Ajoutez un en-tête User-Agent pour respecter les politiques d'utilisation
    }

    response = requests.get(base_url, params=params, headers=headers)
    result = response.json()
    print(result)
    if len(result) > 0:
        for i, found_address in enumerate (result):
            distance = geodesic((float(found_address['lat']), float(found_address['lon'])), (grenoble_lat, grenoble_lon)).km
            if distance<20:
                return float(found_address['lat']), float(found_address['lon'])
    else:
        print(f"Coordonnées introuvables pour {query}.")
        return None, None

# Calcul de l'heuristique pour l'algorithme A*
def heuristic(node, goal,graph):
    return geodesic(graph[node]['data'], graph[goal]['data']).km

# Algorithme A*
def astar(graph, start, end, priority_order):
    heap = [(0, start, [], set())]
    visited = set()

    while heap:
        (total_cost, current, path, lines) = heapq.heappop(heap)
        
        if current in visited:
            continue

        visited.add(current)
        path = path + [current]
        
        if current == end:
            return path, lines

        for neighbor in graph[current]['neighbors']:
            #change_cost = 1 if neighbor not in graph[path[-1]]['lines'] else 0
            change_cost = -4 if end in graph[neighbor]['neighbors'] else 1
            line_priority = 0 if graph[neighbor]['lines'].intersection(priority_order) else 1
            g_cost = total_cost + 1 + change_cost + line_priority
            h_cost = heuristic(neighbor, end,graph)
            f_cost = g_cost + h_cost

            if neighbor==end:
                f_cost=0
            
            heapq.heappush(heap, (f_cost, neighbor, path, lines.union({graph[neighbor]['lines'].intersection(graph[path[-1]]['lines']).pop()})))

st.sidebar.title('Outil de recherche TAG')
headers={"referer":"https://data.mobilites-m.fr/donnees"}
# with open('config.json') as f:
#     data = json.load(f)
# Open_cage_API_Key=data['Key']

tool=st.sidebar.selectbox('Choix du mode de recherche',options=['Ligne et arrêt','Itinéraire'])
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

elif tool=='Itinéraire':

    if 'List_all_stops.csv' not in os.listdir():
        all_transports=[]
        List_all_stops=pd.DataFrame(columns=['name','Code','lat','lon','ligne'])
        for transport in all_transports:
            response=requests.get("https://data.mobilites-m.fr/api/routers/default/index/routes/SEM:"+transport+"/clusters",headers=headers)
            for item in response.json():
                new_row={'name':item['name'],'Code':item['code'],'lat':item['lat'],'lon':item['lon'],'ligne':transport}
                List_all_stops.loc[len(List_all_stops)]=new_row

        for i in range(10,74):
            response=requests.get("https://data.mobilites-m.fr/api/routers/default/index/routes/SEM:"+str(i)+"/clusters",headers=headers)
            if response.text!='Unknown route code':
                for item in response.json():
                    new_row={'name':item['name'],'Code':item['code'],'lat':item['lat'],'lon':item['lon'],'ligne':i}
                    List_all_stops.loc[len(List_all_stops)]=new_row

        List_all_stops.to_csv('List_all_stops.csv')

    else:
        List_all_stops=pd.read_csv('List_all_stops.csv',header=0,index_col=0)
       
    graph = {}

    for index, row in List_all_stops.iterrows():
        stop = row['name']
        line = row['ligne']
        lat = row['lat']
        lon = row['lon']
        
        if stop not in graph:
            graph[stop] = {'data': (lat, lon), 'lines': set(), 'neighbors':set()}
        
        graph[stop]['lines'].add(line)
    # Exemple d'utilisation
    for stop in graph:
        graph[stop]['lines']=set(sorted(graph[stop]['lines'],reverse=True))
        for line in graph[stop]['lines']:
            
            graph[stop]['neighbors'].update(List_all_stops[List_all_stops['ligne'] == line]['name'])
    
    start_stop = 'Stalingrad-Alliés'
    end_stop = 'Seyssinet-Pariset Hôtel de Ville'
    priority_order={'A','B','C','D','E','C1','C2','C3','C4','C5','C6','C7'}
    shortest_path, lines_used = astar(graph, start_stop, end_stop, priority_order)

    # print(shortest_path,lines_used)
    rayon_adresse=20
    grenoble_lat = 45.1885
    grenoble_lon = 5.7245
    shortest_path=[]
    lines_used=[]
    adress = st.text_input("Entrez un arrêt de départ")
    
    destination = st.text_input("Entrez un arrêt d'arrivée")
    Calc_iti=st.button("Calculer l'itinéraire")
    
    if adress and destination and Calc_iti:
        #latitude, longitude =  geocode_nominatim(grenoble_lat, grenoble_lon, adress)
        
        scores = process.extract(adress,List_all_stops.drop_duplicates(subset=['Code'])['name'],scorer=fuzz.ratio)
        if len(scores)>1 and scores[0][1]*0.95<scores[1][1]: #If two scores are almost identical
            
            best_input=closest([scores[0],scores[1]],adress)[2]
            
        else:
            best_input = scores[0][2]
        lat_input,lon_input=List_all_stops.loc[best_input,'lat'],List_all_stops.loc[best_input,'lon']

        
        scores = process.extract(destination,List_all_stops.drop_duplicates(subset=['Code'])['name'],scorer=fuzz.ratio)
        
        if len(scores)>1 and scores[0][1]*0.95<scores[1][1]: #If two scores are almost identical
            
            best_dest=closest([scores[0],scores[1]],destination)[2]
            
        else:
            best_dest = scores[0][2]
        lat_dest,lon_dest=List_all_stops.loc[best_dest,'lat'],List_all_stops.loc[best_dest,'lon']
        
        #On récupère les arrêts les plus proches depuis notre rayon de recherche
        radius=200
        closest_stops=find_closest_coordinates(List_all_stops.drop_duplicates(subset=['Code']),lat_input,lon_input,radius)
        
        if len(closest_stops)!=0 :
            for stops in closest_stops:
                
                s,l=astar(graph, List_all_stops.loc[stops[0],'name'], List_all_stops.loc[best_dest,'name'], priority_order)
                shortest_path.append(s)
                lines_used.append(l)
            # st.markdown(shortest_path)
            # st.markdown(lines_used)
            shortest=min(shortest_path,key=len)
            idx_shortest=shortest_path.index(shortest)
            line=list(lines_used[idx_shortest])
            #This loop is necessary to intervert bus lines that are not in the correct order when creating the list
            for i in range(len(line)):
                if not any(List_all_stops.loc[List_all_stops['name']==shortest[i],'ligne'].str.contains(line[i])):
                    for j in range(i,len(shortest)):
                        if any(List_all_stops.loc[List_all_stops['name']==shortest[j],'ligne'].str.contains(line[i])):
                            break
                    line[i],line[j]=line[j],line[i]

            st.markdown('Le chemin le plus court est le suivant :')
            for i in range(len(shortest)-1):
                st.markdown('Prendre la ligne {} à {} et descendre à {}'.format(line[i],shortest[i],shortest[i+1]))

        elif len(closest_stops)!=0 and 1==0:
            st.markdown('Les arrêts contenus dans un rayon de {} mètres sont les suivants :'.format(radius))
            closest_index=list(list(zip(*closest_stops))[0])
            
            #On gère l'affichage sur la carte
            fig=px.scatter_mapbox(List_all_stops.loc[closest_index],lat='lat',lon='lon',text=List_all_stops.loc[closest_index,'name'],width=800, height=800)
            fig.update_traces(marker=dict(color='green',size=15))
            fig.update_layout(mapbox_style="open-street-map")
            fig.add_trace(px.scatter_mapbox(lat=[lat_input], lon=[lon_input]).data[0])
            fig.update_layout(mapbox=dict(center=dict(lat=lat_input, lon=lon_input),zoom=15))
            st.plotly_chart(fig,use_container_witdh=True)
        elif len(closest_stops)==0:
            st.markdown('Aucun arrêt dans les {} mètres'.format(radius))