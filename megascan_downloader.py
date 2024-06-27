import os
import sys
import requests
import base64
import json
import time
import threading
import wget


class MegascanDownloader():

    def __init__(self, download_dir):
        # Define your username, password, app key, and application ID
        # You can find app_key and app_id in quixel.com under Acount>Developer-Apps
        self.username = 'your user name'
        self.password = 'your password'
        self.app_key = 'your app key'
        self.app_id = 'your app id'
        
        self.assets_url = 'https://megascans.se/v1/assets'
        self.download_url = 'https://megascans.se/v1/downloads'
        self.download_dir = download_dir
        self.log_path = download_dir + "/download_log.json"
        self.payload = {}
        self.response = None
        self.token = ""
        self.refresh_token = ""
        self.token_header = {}
        self.asset_types = ["normalbump", "normalobject", "albedo", "cavity", "curvature", "gloss", "normal", "displacement", "bump", "ao", "metalness", "diffuse", "roughness", "specular", "fuzz"]
        self.priority_categories = ["bark", "debris", "grass", "gravel", "ground", "moss", "rock", "sand", "snow", "soil"] 

        self.run() 
        


    def run(self):
        # Update credentials
        self._send_credentials()
        asset_ids = list(self._get_asset_ids())
        for _id in asset_ids:
            if self._is_priority(_id):
                download_payload = {
                    "asset": _id,
                }
                response = requests.post(self.download_url, json=download_payload, headers=self.token_header)
                if(response.status_code == 200):
                    # acquired assets scope
                    available_types = self._get_available_types(_id)
                    intersection_types = [x for x in self.asset_types if x in available_types]
                    components = []
                    for type in intersection_types:
                        components.append({'mimeType': 'image/x-exr', 'type': type})
                    download_payload = {
                        "asset": _id,
                        "components" : components
                    }
                    response = requests.post(self.download_url, json=download_payload, headers=self.token_header)
                    if response.status_code == 200:
                        download_id = response.json().get("id")
                        asset_id = response.json().get("asset")

                        local_file_path = self.download_dir+"/"+asset_id+'.zip'
                        # skip if already downloaded
                        if not os.path.exists(local_file_path):
                            # Specify the local file path where you want to save the downloaded file
                            link = 'http://downloadp.megascans.se/download/{}?url=https%3A%2F%2Fmegascans.se%2Fv1%2Fdownloads'.format(download_id) 
                            download_thread = threading.Thread(target= self._download_url, args=(_id, link, local_file_path))
                            download_thread.start()
                            # self._download_url(_id, link, local_file_path)
                        

    def _send_credentials(self):
        # Send credentials
        quixel_url = 'https://accounts.quixel.se/api/v1/applications/{}/tokens'.format(self.app_id)
        credentials = base64.b64encode("{}:{}".format(self.username, self.password).encode()).decode()
        headers = {'Content-type': 'application/json', 'Authorization': 'Basic '+credentials}
        self.payload = {"secret": self.app_key}
        self.response = requests.post(quixel_url, json=self.payload, headers=headers)
        # Get token
        self.token = self.response.json().get('token')
        self.refreshToken = self.response.json().get('refreshToken')
        self.token_header = {'Authorization': 'Bearer '+self.token}


    def _get_available_types(self, _id):
        # self._send_credentials()
        download_url = 'https://megascans.se/v1/downloads'
        download_payload = {
            "asset": _id
        }
        response = requests.post(download_url, json=download_payload, headers=self.token_header)
        if(response.status_code == 200):
            data = response.json()
            types = []
            for x in data.get("components"):
                types.append(x.get("type"))
            return types
        return []


    def _get_asset_ids(self):
        # Takes about 40 seconds
        page_total = self._get_page_total("surface")
        # for page_index in range(60, 61):
        for page_index in range(1, page_total+1):
            print("page {} out of {}".format(page_index, page_total))
            # Get the page asset ids
            params = {
                "limit": 200,
                "page": page_index,
                "type": "surface",
            }
            response = requests.get(self.assets_url, json=self.payload, headers=self.token_header, params=params)
            data = response.json()
            for asset in data.get("assets"):
                yield asset.get("id")


    def _is_priority(self, _id):
        asset_url = self.assets_url + "/" + _id
        response = requests.get(asset_url, json=self.payload, headers=self.token_header)
        if response.status_code == 200:
            data = response.json()
            for category in data.get("categories", []):
                if category.lower() in self.priority_categories:
                    return True
        return False
    
    
    def _download_url(self, _id, url, local_file_path):
        # Send an HTTP GET request to the URL
        response = requests.get(url, json=self.payload, headers=self.token_header)
        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            wget.download(url, local_file_path)
            self._log_download( _id, True)
            print(" ========= Downloaded successfully! ========= ")
        else:
            self._log_download(_id, False)
            print("========= Failed to download file. Status code: ", response.status_code)


    def _get_page_total(self, type):
        # Get the page total
        params = {
            "limit": 200,
            "type": type,
        }
        response = requests.get(self.assets_url, json=self.payload, headers=self.token_header, params=params)
        return response.json().get("pages")


    def _log_download(self, _id, has_succeeded):
        data = {"succeeded" : [], "faild" : []}
        if os.path.exists(self.log_path):
            with open(self.log_path, 'r') as json_file:
                data = json.load(json_file)
        
        if has_succeeded:
            data["succeeded"].append(_id)
        else:
            data["faild"].append(_id)

        with open(self.log_path, "w") as json_file:
            json.dump(data, json_file, indent=4)
        


MegascanDownloader(sys.argv[0])