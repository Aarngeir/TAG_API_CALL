import requests
import pandas as pd
import time
import datetime
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

def closest(lst, K):
    min_abs=100

    for i,j in enumerate(lst):
        if abs(len(j[0])-len(K))<min_abs:
            min_abs=abs(len(j[0])-len(K))
            idx=i
    
    return lst[idx]


def find_closest_coordinates(df, user_lat, user_lon, radius=500,stop=None):
    if stop!=None:
        df=df.drop(df.loc[df['name']==stop].index)
    close_coordinates = []
    for index, row in df.iterrows():
        distance = geodesic((user_lat, user_lon), (row['lat'], row['lon'])).meters
        
        if distance <= radius and row['name']!=stop:
            close_coordinates.append((index,row['lat'], row['lon'],distance,row['ville']+' / '+row['name']))
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

    if 'List_all_stops.csv' not in os.listdir():
        all_transports=['A','B','C','D','E','C1','C2','C3','C4','C5','C6','C7']
        List_all_stops=pd.DataFrame(columns=['name','Code','lat','lon','ligne','ville'])
        for transport in all_transports:
            response=requests.get("https://data.mobilites-m.fr/api/routers/default/index/routes/SEM:"+transport+"/clusters",headers=headers)
            for item in response.json():
                new_row={'name':item['name'],'Code':item['code'],'lat':item['lat'],'lon':item['lon'],'ligne':transport,'ville':item['city']}
                
                List_all_stops.loc[len(List_all_stops)]=new_row

        for i in range(10,74):
            response=requests.get("https://data.mobilites-m.fr/api/routers/default/index/routes/SEM:"+str(i)+"/clusters",headers=headers)
            if response.text!='Unknown route code':
                for item in response.json():
                    new_row={'name':item['name'],'Code':item['code'],'lat':item['lat'],'lon':item['lon'],'ligne':str(i),'ville':item['city']}
                    List_all_stops.loc[len(List_all_stops)]=new_row

        List_all_stops.to_csv('List_all_stops.csv')

    else:
        List_all_stops=pd.read_csv('List_all_stops.csv',header=0,index_col=0)
       
    graph = {}
    #ToDo Fix graph to add city in the stop name
    for index, row in List_all_stops.iterrows():
        stop = row['name']
        line = row['ligne']
        lat = row['lat']
        lon = row['lon']
        city = row['ville']
        if city+' / '+stop not in graph:
            graph[city + ' / '+stop] = {'data': (lat, lon), 'lines': set(), 'neighbors':set()}
        
        graph[city + ' / ' +stop]['lines'].add(line)
    
    for stop in graph:
        graph[stop]['lines']=set(sorted(graph[stop]['lines'],reverse=True))
        for line in graph[stop]['lines']:
            
            graph[stop]['neighbors'].update(i+' / '+j for i,j in zip(List_all_stops[List_all_stops['ligne'] == line]['ville'].to_list(),List_all_stops[List_all_stops['ligne'] == line]['name'].to_list()))
    

    priority_order={'A','B','C','D','E','C1','C2','C3','C4','C5','C6','C7'}

    rayon_adresse=20
    grenoble_lat = 45.1885
    grenoble_lon = 5.7245
    shortest_path=[]
    lines_used=[]
    dis_list_arret=['']
    city_stops_list=[i+' / '+j for i,j in zip(List_all_stops.drop_duplicates(subset=['Code'])['ville'].to_list(),List_all_stops.drop_duplicates(subset=['Code'])['name'].to_list())]
    dis_list_arret.extend(city_stops_list)
    
    full_address = st.selectbox("Entrez un arrêt de départ",dis_list_arret)
    
    full_destination = st.selectbox("Entrez un arrêt de destination",dis_list_arret)
    Calc_iti=st.button("Calculer l'itinéraire")
    
    if full_address!='' and full_destination!='' and Calc_iti:
        city_input,address = full_address.split(' / ')
        city_dest,destination = full_destination.split(' / ')

        index_input=List_all_stops.loc[(List_all_stops['name']==address) & (List_all_stops['ville']==city_input)].index
        lat_input,lon_input=List_all_stops.loc[index_input,'lat'].values[0],List_all_stops.loc[index_input,'lon'].values[0]
        

        index_dest=List_all_stops.loc[(List_all_stops['name']==destination) & (List_all_stops['ville']==city_dest)].index
        lat_dest,lon_dest=List_all_stops.loc[index_dest,'lat'].values[0],List_all_stops.loc[index_dest,'lon'].values[0]
        
        #On récupère les arrêts les plus proches depuis notre rayon de recherche
        radius=320
        
        closest_stops=find_closest_coordinates(List_all_stops.drop_duplicates(subset=['Code']),lat_input,lon_input,radius,address)

        closest_stops.insert(0,(index_input[0],lat_input,lon_input,0,full_address))
        
        closest_stops.sort(key=lambda x:x[3])
        
        closest_dest = find_closest_coordinates(List_all_stops.drop_duplicates(subset=['Code']),lat_dest,lon_dest,radius,destination)

        closest_dest.insert(0,(index_dest[0],lat_dest,lon_dest,0,full_destination))

        closest_dest.sort(key=lambda x:x[3])
        
        for i,stops in enumerate(closest_stops):
            for j,stops_dest in enumerate(closest_dest):
                s,l=astar(graph, stops[4], stops_dest[4], priority_order)
                shortest_path.append(s)
                lines_used.append(l)
                if i==0 and j==0:
                    shortest_from_start=s
        # st.markdown(shortest_path)
        # st.markdown(lines_used)
        
        shortest=min(shortest_path,key=len)
        if len(shortest)==len(shortest_from_start):
            shortest=shortest_from_start
        idx_shortest=shortest_path.index(shortest)
        line=list(lines_used[idx_shortest])
        shortest=[i.split(' / ')[1] for i in shortest]
        #This loop is necessary to intervert bus lines that are not in the correct order when creating the list
        for i in range(len(line)):
            
            if not any(List_all_stops.loc[List_all_stops['name']==shortest[i],'ligne']==line[i]):
                for j in range(i,len(shortest)):
                    if any(List_all_stops.loc[List_all_stops['name']==shortest[j],'ligne']==line[i]):
                        break
                line[i],line[j]=line[j],line[i]

        st.markdown('Le chemin le plus court est le suivant :')
        for i in range(len(shortest)-1):
            st.markdown('Prendre la ligne {} à {} et descendre à {}'.format(line[i],shortest[i],shortest[i+1]))

        if len(closest_stops)!=0 and False:
            st.markdown('Les arrêts contenus dans un rayon de {} mètres sont les suivants :'.format(radius))
            closest_index=list(list(zip(*closest_stops))[0])
            
            #On gère l'affichage sur la carte
            fig=px.scatter_mapbox(List_all_stops.loc[closest_index],lat='lat',lon='lon',text=List_all_stops.loc[closest_index,'name'],width=800, height=800)
            fig.update_traces(marker=dict(color='green',size=15))
            fig.update_layout(mapbox_style="open-street-map")
            fig.add_trace(px.scatter_mapbox(lat=[lat_input], lon=[lon_input]).data[0])
            fig.update_layout(mapbox=dict(center=dict(lat=lat_input, lon=lon_input),zoom=15))
            st.plotly_chart(fig,use_container_witdh=True)
        elif len(closest_stops)==0 and False:
            st.markdown('Aucun arrêt dans les {} mètres'.format(radius))