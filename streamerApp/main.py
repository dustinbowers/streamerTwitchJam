from typing import Tuple

import obsws_python as obs
import websocket
import json
import threading
import requests
import time

from obsws_python.error import OBSSDKRequestError

from secret import password, username, userSceneName

obsWs = obs.ReqClient(host='localhost', port=4455,
                      password=password, timeout=3)
IDs = []
windowConfigData = {}
infoWindowDataConfigData = {}


def getSceneItems():
    raw_request = {
        "requestType": "GetSceneItemList",
        "sceneName": userSceneName,
    }
    response = obsWs.send('GetSceneItemList', data=raw_request, raw=True)
    return response


def getSelectedSceneItems(itemList, itemsToSelect):
    """
    :param itemList: Dictionary representing the list of scene items, expected to have a key 'sceneItems' which is a list of scene item objects.
    :param itemsToSelect: List of item names to select from the scene items. If empty, all items will be selected.
    :param sceneName: obs scene to use
    :return: A tuple containing:
        - A list of selected scene item IDs.
        - A list of dictionaries containing details of the selected scene items, including window ID, window name, width, height, x location, and y location.
    """
    selectedIds = []
    jsonData = []
    for sceneItem in itemList['sceneItems']:
        if sceneItem['sourceName'] in itemsToSelect or len(itemsToSelect) == 0:
            sceneWindowData = getWindowDetails(sceneItem['sceneItemId'])
            jsonData.append({"windowId": sceneItem['sceneItemId'], "windowName": sceneItem['sourceName'],
                             'width': sceneWindowData[0][0], 'height': sceneWindowData[0][1],
                             'xLocation': sceneWindowData[1][0], 'yLocation': sceneWindowData[1][1]})
            # print(sceneItem)
            selectedIds.append(sceneItem['sceneItemId'])
    with open("obsConfig.json", "w+") as f:
        json.dump(jsonData, f)

    return selectedIds, jsonData


def transformId(x: int, y: int, windowId: int, sizeOfWindow=(100, 100)):
    raw_request = {
        "requestType": "SetSceneItemTransform",
        "sceneName": userSceneName,
        "sceneItemId": windowId,
        "sceneItemTransform": {
            "positionX": min(max(x, 0), width - sizeOfWindow[0]),
            "positionY": min(max(y, 0), height - sizeOfWindow[1]),
        }
    }
    # print(f"transform Id request: {raw_request}")
    obsWs.send('SetSceneItemTransform', data=raw_request, raw=True)


def getSizeOfWindow(sceneResponse) -> Tuple[float, float]:
    return (abs(float(sceneResponse['sourceWidth']) - float(sceneResponse['cropLeft'] + sceneResponse['cropRight'])) * abs(sceneResponse['scaleX']),
            abs(float(sceneResponse['sourceHeight']) - float(sceneResponse['cropTop'] + sceneResponse['cropBottom'])) * abs(sceneResponse['scaleY']))


def getWindowDetails(sceneItemId) -> tuple[tuple[float, float], tuple[float, float], tuple[float, float]]:
    raw_request = {
        "requestType": "GetSceneItemTransform",
        "sceneName": userSceneName,
        "sceneItemId": sceneItemId
    }
    try:
        response = obsWs.send('GetSceneItemTransform',
                              data=raw_request, raw=True)
    except OBSSDKRequestError as e:
        print(f"item id {sceneItemId} does not exist")
        return (float(0), float(0)), (float(0), float(0)), (float(0), float(0))
    # print(response)

    sceneResponse = response['sceneItemTransform']
    # print(sceneResponse)
    sizeOfWindow = getSizeOfWindow(sceneResponse)
    # if sceneResponse['scaleX'] sceneResponse['scaleY'] are negative, we want to change the position by that sizeOfWindow[width/height]
    xPosition = float(sceneResponse['positionX'])
    yPosition = float(sceneResponse['positionY'])

    if sceneResponse['scaleX'] < 0:
        xPosition -= sizeOfWindow[0]
    if sceneResponse['scaleY'] < 0:
        yPosition -= sizeOfWindow[1]

    locationOfWindow = (xPosition, yPosition)

    # print(f"sizeOfWindow: {sizeOfWindow}")
    # print(f"locationOfWindow: {locationOfWindow}")
    return sizeOfWindow, locationOfWindow, (sceneResponse['scaleX'], sceneResponse['scaleY'])


def getVideoOutputSettings():
    raw_request = {
        "requestType": "GetVideoSettings",
    }
    print(f"transform Id request: {raw_request}")
    response = obsWs.send('GetVideoSettings', data=raw_request, raw=True)
    return response['baseWidth'], response['baseHeight']


def getScenes():
    raw_request = {
        "requestType": "GetSceneList",
    }
    response = obsWs.send('GetSceneList', data=raw_request, raw=True)
    print(response)
    sceneResponse = ""
    for scene in response['scenes']:
        sceneResponse += f"{scene['sceneName']}, "
    return sceneResponse[:-2]


def startWebsocketRoom(userId):
    print("Starting WebSocket room with ID:", userId)
    # Replace with your actual WebSocket server URL
    postUrl = f'https://websocket.matissetec.dev/lobby/new?user={userId}'
    print(postUrl)
    response = requests.post(postUrl)
    ws_url = f'wss://websocket.matissetec.dev/lobby/connect/streamer?user={userId}&key={response.text}'
    print(ws_url)
    ws_app = websocket.WebSocketApp(
        ws_url,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    ws_app.run_forever()


def runHello(ws):
    # Receive new x and y positions
    wholeData = {'data': []}
    for windowId in IDs:
        # print(f"running for id {windowId}")
        sizeOfWindow, locationOfWindow, _ = getWindowDetails(windowId)
        # this data needs to be gathered from the config
        wholeData['data'].append({"data": [
            {
                "name": windowId,
                "x": locationOfWindow[0],
                "y": locationOfWindow[1],
                "width": f"{sizeOfWindow[0]}px",
                "height": f"{sizeOfWindow[1]}px",
                "info": "some data to register later",
                # maybe we also have this settable for each window
                "zIndex": 10,
            }]})
    ws.send(json.dumps(wholeData))


def sendInfoWindowDataConfig(ws):
    # print("sending InfoWindowDataConfig")
    # print(f"whole data from json {infoWindowDataConfigData}")
    ws.send(json.dumps(infoWindowDataConfigData))


def sendWindowConfig(ws):
    # print("sending windowConfig")
    # print(f"whole data from json {windowConfigData}")
    ws.send(json.dumps(windowConfigData))


## TODO: BUGFIX: Current production extension expects this double-encoded format, so we have to leave it for now
def sendObsSizeConfig(ws):
    # print("sending obs size config")
    ws.send(json.dumps({                # dumps
        "obsSize": json.dumps({         # double-dumps
            "obsSize": {                
                "width": width, 
                "height": height
            }
        }
    )}))


def on_message(ws, message):
    # print("Received message:", message)
    # Parse the message if it's in JSON format
    if 'Hello Server!' in message:
        sendObsSizeConfig(ws)
        # might need to add the sleeps so we can insure we send the data with the network restriction on the server
        # time.sleep(.025)
        sendWindowConfig(ws)
        # time.sleep(.025)
        sendInfoWindowDataConfig(ws)
        # time.sleep(.025)
        runHello(ws)
        return
    try:
        data = json.loads(message)
        if 'color' in data:
            return  # this is for the frontend only for now
        x = data.get('x', .5)
        y = data.get('y', .5)
        windowId = int(data.get('name', 0))
        if windowId == 0:
            print("error name does not exist in data", data)
            return
        sizeOfWindow, _, scaleOfWindow = getWindowDetails(windowId)
        curWindowId = str(windowId)

        print(f"curWindowId: {curWindowId}")


        #########
        ## TODO : Re-Add boundary constraint verification here
        #########


        # get id from name off list we create at beginning
        transformX = x*float(width)
        transformY = y*float(height)

        # TODO look into why negative scale breaks
        # if scaleOfWindow[0] < 0:
        #     print(f"resizing {transformX} to {transformX + sizeOfWindow[0]}")
        #     transformX += sizeOfWindow[0]
        # if scaleOfWindow[1] < 0:
        #     transformY += sizeOfWindow[1]

        transformId(transformX, transformY, windowId, sizeOfWindow)
        ws.send(json.dumps({"data": [
            {
                "name": windowId,
                "x": x*float(width),
                "y": y*float(height),
                "width": f"{sizeOfWindow[0]}px",
                "height": f"{sizeOfWindow[1]}px",
                "info": "some data to register later"
            }]}))
        print(f"{windowId} Moved window to {x} {y}")
    except json.JSONDecodeError:
        print("Received non-JSON message" + message)


def on_error(ws, error):
    print("WebSocket error:", error)


def on_close(ws, close_status_code, close_msg):
    print("WebSocket connection closed")


def on_open(ws):
    print("WebSocket connection opened")
    for windowId in IDs:
        ws.send(json.dumps({"command": "get_positions", "id": windowId}))

    def ping():
        while True:
            time.sleep(30)
            ws.send("ping")
    threading.Thread(target=ping, daemon=True).start()


def getUserIdFromName(name):
    url = f'https://decapi.me/twitch/id/{name}'
    response = requests.get(url)
    return response.text


if __name__ == '__main__':
    width, height = getVideoOutputSettings()
    # allScenes = getScenes()
    # print(allScenes)
    #    Get names of the scenes wanted to be modified
    # selectedScene = "Scene"

    # allow for more than 1 scene to be in the scene item list
    # likely this will need to become a map like they have on obs
    sceneItems = getSceneItems()
    _, jsonData = getSelectedSceneItems(sceneItems, [])
    # print(jsonData)

    # get items to select from json data save above

    # for scene in sceneItems:
    #     print(scene)
    #     windowData = getWindowDetails('Scene', scene['sceneItemId'])
    #     print({"windowId": scene['sceneItemId'], "windowName": scene['sourceName'], 'width': windowData[0][1], 'height': windowData[0][0],'xLocation': windowData[1][0], 'yLocation': windowData[1][1]})
    #     print(scene['sceneItemId'], scene['sourceName'])

    movableWindowNames = []
    with open("movableWindowNames.json", "r", encoding="utf-8") as f:
        movableWindowNames = json.loads(f.read())
        print(movableWindowNames)

    IDs, _ = getSelectedSceneItems(sceneItems, movableWindowNames)
    # print(IDs)
    userId = getUserIdFromName(username)
    # print(userId)

    with open("windowConfig.json", "r", encoding="utf-8") as f:
        windowConfigData = f.read()
        print(windowConfigData)

    with open("infoWindowDataConfig.json", "r", encoding="utf-8") as f:
        infoWindowDataConfigData = f.read()
        print(infoWindowDataConfigData)

    listener_thread = threading.Thread(
        target=startWebsocketRoom, args=(userId,))
    listener_thread.start()
