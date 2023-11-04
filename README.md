# TAG_API_CALL
This repository centers around calling the public transport MTAG API to know when the next transport comes

# Start the application

This app has been built using Python in it's 3.8.18 version, but newer version will work. After creating a Python virtual environment, just use :
```bash
pip install -r requirements.txt
```

The application uses Streamlit and a direct connection to the MTAG API to show the results obtained. Once the requirements is installed, the starting of the application is done with :
```bash
streamlit run Appel_api.py --server.port 1105
```

# Usage

The application is composed of two main parts, the research by bus line and bus stops, and the map research.

## Bus lines and stops
By simply choosing a network, a bus line and a stop, you will be able to know when, in real time, the next bus/tram passes in both direction. The stop selector also works if you type the researched stop by autocompleting with the ones existing.
Further development will be added to increase the amount of information you can gather with this tool.
![alt text](Application_start.png?raw=true)
## Map research
The map research has not been developped yet but it will show, from a location the closest stop and when transport pass at that stop.
