import requests
import streamlit as st
import pandas as pd
import datetime
import pytz

def get_list_ligne(network,headers):
    
    if network != 'Proximo':
        response=requests.get("https://data.mobilites-m.fr/api/routers/default/index/routes?reseaux="+network.upper(),headers=headers)
        
        list_ligne={}
        for item in response.json():
            list_ligne[item['shortName']]=item['id']
    else:
        list_ligne={'12':'SEM:12','13':'SEM:13','14':'SEM:14','15':'SEM:15','16':'SEM:16','19':'SEM:19','20':'SEM:20','21':'SEM:21','22':'SEM:22','23':'SEM:23','25':'SEM:25','26':'SEM:26'}
    return list_ligne

def get_list_arret(list_ligne,ligne,headers):
    response=requests.get("https://data.mobilites-m.fr/api/routers/default/index/routes/"+list_ligne[ligne]+"/clusters",headers=headers)

    list_arret={}
    for item in response.json():
        list_arret[item['name']]=item['code']
    dis_list_arret=['']
    dis_list_arret.extend(list(list_arret.keys()))

    return dis_list_arret,list_arret

def calculate_time_arrival(real_time):
    seconds_bus=real_time
    minutes, seconds = divmod(seconds_bus, 60)
    hours, minutes = divmod(minutes, 60)
    time_arrival="%d:%02d:%02d" % (hours, minutes, seconds)
    t=datetime.datetime.now(pytz.timezone('Europe/Paris'))
    now_seconds=t.hour*3600+t.minute*60+t.second
    second_to_bus=seconds_bus-now_seconds
    if second_to_bus>=0:
        time_to_bus=str(datetime.timedelta(seconds=second_to_bus))
    else:
        time_to_bus='0:00:00'
    return time_arrival,time_to_bus

def get_next_transport(list_arret,arret,list_ligne,ligne,headers):
    response=requests.get("https://data.mobilites-m.fr/api/routers/default/index/clusters/"+list_arret[arret]+"/stoptimes?route="+list_ligne[ligne].replace(':','%3A'),headers=headers)
    df = pd.DataFrame(columns=['Terminus','Time','Remaining','Occupancy'])
    
    if len(response.json())>0:
            
            
            for i,item in enumerate( response.json()):
                
                terminus=item['pattern']['lastStopName']
                
                if len(df.loc[df['Terminus'].str.contains(terminus)])==0:
                    df.loc[i,'Terminus']=terminus
                    occupancy=None
                    try:
                        occupancy=item['times'][0]['occupancy'].lower()
                    except:
                        pass
                    df.loc[i,'Occupancy'] = occupancy
                    time_arrival,time_to_bus=calculate_time_arrival(item['times'][0]['realtimeArrival'])
                    
                    
                    df.loc[i,'Time']=time_arrival
                    df.loc[i,'Remaining']=time_to_bus
                    if len(item['times'])>1:
                        
                        for next_bus in range(1,len(item['times'])):
                            time_arrival,_=calculate_time_arrival(item['times'][next_bus]['realtimeArrival'])
                            
                            df.loc[i,next_bus]=time_arrival
                else:
                    index=df.loc[df['Terminus'].str.contains(terminus)].index
                    time_arrival,_=calculate_time_arrival(item['times'][0]['realtimeArrival'])
                    
                    if len(df.columns)==4 or pd.isna(df.loc[index,1].values[0])==True:
                        
                        df.loc[index,1]=time_arrival
                    else:
                        last_col=None
                        for col in df.columns:
                            if col not in ['Terminus','Time','Remaining','Occupancy'] and pd.isna(df.loc[index,col].values[0])==True:
                                last_col=col
                                break
                        if last_col!=None:
                            
                            df.loc[index,last_col]=time_arrival
                        else:
                            df.loc[index,col+1]=time_arrival
                    # Reorganize the timestamps in the columns
                    t_cols=[j for j in df.columns if j not in ['Terminus','Time','Remaining','Occupancy']]
                    
                    df.loc[index,t_cols]=df.loc[index,t_cols].apply(pd.to_datetime).sort_values(by=t_cols)
    
    return df