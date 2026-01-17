import requests as req 

from dotenv import load_dotenv
import os

load_dotenv()

CTS_TOKEN=os.getenv("CTS_TOKEN")
BASE_URL="https://api.cts-strasbourg.eu"
AUTH=(CTS_TOKEN,"")

def stop_monitoring(MonitoringRef,LineRef="toutes",
                      DirectionRef="lesdeux",
                      VehicleMode="undefined"
                      ,PreviewInterval="PT30M",
                      MaximumStopVisits=3,
                      MinimumStopVisitsPerLine=3,
                      IncludeGeneralMessage=True,
                      StartTime="now"):
    url=BASE_URL+"/v1/siri/2.0/stop-monitoring"

    params = {
        "MonitoringRef" : MonitoringRef,
        "VehicleMode" : VehicleMode,
        "PreviewInterval" : PreviewInterval,
        "MaximumStopVisits" : MaximumStopVisits,
        "MinimumStopVisitsPerLine" : MinimumStopVisitsPerLine,
        "IncludeGeneralMessage" : IncludeGeneralMessage,
    }
    if LineRef!="toutes":
        params["LineRef"]=LineRef
    if DirectionRef!="lesdeux":
        params["DirectionRef"]=DirectionRef
    if StartTime!="now":
        params["StartTime"]=StartTime

    
    resp=req.get(
        url,
        params=params,
        auth=AUTH)
    return resp.json()

def prochains_departs(MonitoringRef,LineRefList=[],
                      DirectionRefList=[],
                      VehicleMode="undefined"
                      ,PreviewInterval="PT30M",
                      MaximumStopVisits=3,
                      MinimumStopVisitsPerLine=3,
                      IncludeGeneralMessage=True,
                      StartTime="now"):
    resp= stop_monitoring(MonitoringRef,LineRef="toutes",
                      VehicleMode=VehicleMode,
                      PreviewInterval=PreviewInterval,
                      MaximumStopVisits=MaximumStopVisits,
                      MinimumStopVisitsPerLine=MinimumStopVisitsPerLine,
                      IncludeGeneralMessage=IncludeGeneralMessage,
                      StartTime=StartTime)
    
    result=[]
    # return resp["ServiceDelivery"]["StopMonitoringDelivery"][0]["MonitoredStopVisit"]
    if not "MonitoredStopVisit" in resp["ServiceDelivery"]["StopMonitoringDelivery"][0].keys():
        return []
    for depart in resp["ServiceDelivery"]["StopMonitoringDelivery"][0]["MonitoredStopVisit"]:
        temp_ligne=depart["MonitoredVehicleJourney"]["PublishedLineName"]
        temp_directionref=depart["MonitoredVehicleJourney"]["DirectionRef"]
        if temp_ligne in LineRefList :
            if temp_directionref==int(DirectionRefList[LineRefList.index(temp_ligne)]):
                result.append({
                    "ligne" : temp_ligne,
                    "arret" : depart["MonitoringRef"],
                    "StopPointName" : depart["MonitoredVehicleJourney"]["MonitoredCall"]["StopPointName"],
                    "hdepart" : depart["MonitoredVehicleJourney"]["MonitoredCall"]["ExpectedDepartureTime"],
                    "direction" : depart["MonitoredVehicleJourney"]["DestinationName"],
                    "DirectionRef" : temp_directionref,
                })
    return result