import requests
import os
import pandas as pd
from geopy.distance import geodesic
import heapq

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


def create_list_all_stops(headers):
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

    return List_all_stops

def create_graph(List_all_stops):
    graph = {}
    
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
    
    return graph

def create_list_arret(List_all_stops):
    dis_list_arret=['']
    city_stops_list=[i+' / '+j for i,j in zip(List_all_stops.drop_duplicates(subset=['Code'])['ville'].to_list(),List_all_stops.drop_duplicates(subset=['Code'])['name'].to_list())]
    dis_list_arret.extend(city_stops_list)
    return dis_list_arret

def find_shortest_path(full_address, full_destination, List_all_stops, graph):
    priority_order={'A','B','C','D','E','C1','C2','C3','C4','C5','C6','C7'}

    rayon_adresse=20
    grenoble_lat = 45.1885
    grenoble_lon = 5.7245
    shortest_path=[]
    lines_used=[]
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

    return shortest, line