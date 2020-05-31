from __future__ import print_function
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

import json


class InvalidIdError(Exception):
   # Constructor method
   def __init__(self, args):
      self.args = args
   # __str__ display function
   def __str__(self):
      return(self.args)

class InvalidFileName(Exception):
   def __init__(self, args):
      self.args = args
   def __str__(self):
      return(self.args)

class InvalidMoveRequest(Exception):
   def __init__(self, args):
      self.args = args
   def __str__(self):
      return(self.args)


class GDrive():
    def __init__(self):
        self.my_drive = "0AJzA_NPQBPA2Uk9PVA"
        self.shared_drive = "0AM-sdiio-Y-0Uk9PVA"
        self.non_artist = "130Fg8G3OAi1PCxsbAtRa_LRBl2KN_R7S"
        self.shared_drive_folder = "1Meu2Kts2CYLkHLUMYAyVFuRacQaLQWRl"
        self.service = self.get_service()

    def get_service(self):
        """Returns Service for usage of google drive api v3.
        """
        # If modifying these scopes, delete the file token.pickle.
        SCOPES = ['https://www.googleapis.com/auth/drive']
        creds = None
        # The file token.pickle stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'client_secrets.json', SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)

        service = build('drive', 'v3', credentials=creds)
        return service

    def empty_trash(self):
        """ Clears the Trash in My Drive """
        """ Examples
            gdrive.empty_trash()
        """
        self.service.files().emptyTrash().execute()

    def list_drives(self):
        """ Returns a list of drive name, drive id """
        """ Examples
            gdrive.list_drives()
        """
        results = self.service.drives().list(pageSize=10, useDomainAdminAccess=False).execute()
        for drive in results["drives"]:
            print("Drive Name : {0}     Drive ID : {1}".format(drive["name"], drive["id"]))
        return results["drives"]

    def my_drive_files(self, query={"id": None, "fields":"id, name", "max_results":1000, "q": ""}):
        """ Returns all the list of files in My Drive i.e. Google Drive or 
        any shared drive(if id key of it is in the query dictionary).
        To list files and folders directly in a file specify the 'q' value
        in query as "'folder_id' in parents".
        Specify fields for the file to retrieve in the query.
        By default id, name fields are returned for each file.
        """ 
        """ Examples
            print(gdrive.my_drive_files())
            print(gdrive.my_drive_files({"max_results": 15}))
            print(gdrive.my_drive_files({"fields":"name, parents"}))
            print(gdrive.my_drive_files({"max_results": 15, "fields":"name, parents"}))
            print(gdrive.my_drive_files({"id": "0AM-sdiio-Y-0Uk9PVA"}))
            print(gdrive.my_drive_files({"id": "0AM-sdiio-Y-0Uk9PVA", "max_results":2}))
            print(gdrive.my_drive_files({"id": "0AM-sdiio-Y-0Uk9PVA", "fields":"name"}))
            print(gdrive.my_drive_files({"q":"'1osD87uCuEMRgIQO-EnfIy-WmCf4pTxxe' in parents", "max_results": 15, 
                "fields":"name, id, parents", "id": "0AM-sdiio-Y-0Uk9PVA"}))
        """
        files_list = []
        if query.get("max_results", None):
            has_max_results = True
        else:
            has_max_results = False
            query["max_results"] = 1000
        if query.get("fields", None) is None:
            query["fields"] = "id, name"
        if query.get("id", None) is None:
            has_id = False
        else:
            has_id = True
        next_page = None
        while True:
            if has_id:
                results = self.service.files().list(q="{0}".format(query.get("q", "")),
                pageSize=query["max_results"], fields="{0}, files({1})".format("nextPageToken", query["fields"]), 
                includeItemsFromAllDrives=True, 
                 corpora='drive', supportsAllDrives=True, driveId=query["id"]).execute()
            else:
                results = self.service.files().list(q="{0}".format(query.get("q", "")),
                    pageSize=query["max_results"], fields="{0}, files({1})".format("nextPageToken", query["fields"]), 
                    pageToken=next_page).execute()
            
            files_list.extend(results["files"])
            next_page = results.get("nextPageToken", None)
            if has_max_results or next_page is None:
                break
        # print(json.dumps(files_list, indent=2))
        # print(len(files_list))
        return files_list

    def files_in_folder(self, query={"folder_id": None, "q": ""}):
        """ Returns the list of files and folders that are directly under the 
        specified 'folder_id' in the query. Specify the 'id' if the search is in
        a shared drive
        """
        """ Examples
            print(gdrive.files_in_folder({"folder_id": "1osD87uCuEMRgIQO-EnfIy-WmCf4pTxxe"}))
            print(gdrive.files_in_folder({"folder_id": "1osD87uCuEMRgIQO-EnfIy-WmCf4pTxxe", "id": "0AM-sdiio-Y-0Uk9PVA"}))
        """
        if query.get("folder_id", None) is None:
            raise InvalidIdError("Invalid ID specified")
        query["q"] = "'{0}' in parents".format(query["folder_id"])
        files_list = self.my_drive_files(query)
        return files_list

    def create_tree(self, folder_obj, files_list):
        """ A helper function for folder_structure. It takes in a
        folder_obj which is dictionary with keys 'id, name, 
        folder_list, file_list' where 'id, name' are preassigned 
        and 'folder_list, file_list' are empty lists. files_list
        parameter takes a list of file dictionary with keys 'id, name,
        mimeType, parents'.
        """
        file_list = []
        folder_list = []
        for file in files_list:
            if folder_obj["id"] in file["parents"]:
                if file["mimeType"] == "application/vnd.google-apps.folder":
                    sub_folder_obj = {
                        "id": file["id"],
                        "name": file["name"],
                        "folder_list": [],
                        "file_list": []
                    }
                    sub_folder_obj = self.create_tree(sub_folder_obj, files_list)
                    folder_list.append(sub_folder_obj)
                else:
                    file_list.append(file)
        folder_obj["folder_list"] = folder_list
        folder_obj["file_list"] = file_list
        return folder_obj

    # TODO: Passing drive ID of My Drive does not return the required tree folder structure
    def folder_structure(self, query={"id": None, "drive_id": None}):
        """ Takes in a query dictionary with 'id' as a key of folder
        and 'drive_id' as the key of the Shared Drive if in any.
        Returns a folder dictionary with keys 'id, name,
        folder_list, file_list'. 'id' and 'name' are the id
        and name of the folder. 'file_list' is the list of file
        dictionaries that are directly inside the folder each with
        keys 'id, name, mimeType, parents'. 'folder_list' is a list
        of other folders that are directly inside the folder and have
        hte same structure as the returned folder since the tree is
        created by recursively calling the create_tree function on
        each folder itself.
        """
        """ Examples
            print(json.dumps(gdrive.folder_structure({"id": "0AJzA_NPQBPA2Uk9PVA"}), indent=1)) # Structure My Drive
            print(json.dumps(gdrive.folder_structure({"id": "130Fg8G3OAi1PCxsbAtRa_LRBl2KN_R7S"}), indent=1)) # Structure a folder in My Drive
            print(json.dumps(gdrive.folder_structure({"id": "1osD87uCuEMRgIQO-EnfIy-WmCf4pTxxe", "drive_id": "0AM-sdiio-Y-0Uk9PVA"}), indent=1)) # Structure a folder in Shared Drive
            print(json.dumps(gdrive.folder_structure({"id": "0AM-sdiio-Y-0Uk9PVA", "drive_id": "0AM-sdiio-Y-0Uk9PVA"}), indent=1)) # Structure Shared Drive
        """
        if query.get("id", None) is None:
            raise InvalidIdError("Invalid Id specified")
        if query.get("drive_id", None) is None:
            files_list = self.my_drive_files(query={"fields":"id, name, mimeType, parents"})
        else:
            files_list = self.my_drive_files(query={"id": query["drive_id"], "fields":"id, name, mimeType, parents"})
        folder_meta = self.file_metadata(query={"id":query["id"], "fields":"id, name, mimeType, parents"})
        folder_obj = {
            "id": folder_meta["id"],
            "name": folder_meta["name"],
            "folder_list": [],
            "file_list": []
        }
        folder_obj = self.create_tree(folder_obj, files_list)
        return folder_obj

    def file_metadata(self, query={"id": None, "fields": "id, name", "fetch_all": False}):
        """ Returns the meta data of files by specify id, fields, fetch_all in a dictionary.
        Raises InvalidIdError of 'id' is not specified.
        """
        """ Examples
            print(gdrive.file_metadata()) # Raises InvalidIdError
            print(gdrive.file_metadata({"id": "1-KfvFJc6qBrdbT44WaJc_xls2cP0wLMn"}))
            print(gdrive.file_metadata({"id": "1-KfvFJc6qBrdbT44WaJc_xls2cP0wLMn", "fields": "name"}))
            print(gdrive.file_metadata({"id": "1-KfvFJc6qBrdbT44WaJc_xls2cP0wLMn", "fetch_all": True}))
        """
        if query.get("id", None) is None:
            raise InvalidIdError("Invalid ID specified")
        if query.get("fetch_all", None):
            query["fields"] = "*"
        elif query.get("fields", None) is None:
            query["fields"] = "id, name"
        file = self.service.files().get(fileId=query["id"], fields=query["fields"],
            supportsAllDrives=True).execute()
        return file

    def create(self, file_metadata={"name": None}):
        """ Creates a file of given name, mimeType and returns the json fields for
        id with other file_metadata as requested. Specify the the parents key with
        'id' of parent in a list to create the file in the specified parent.
        The parent can be a folder, My Drive or a folder or a shared drive itself. 
        """
        """ Examples
            print(gdrive.create({"name": "Hello.txt", "mimeType": "application/vnd.google-apps.folder"}))
            print(gdrive.create({"name": "Hello.txt", "mimeType": "application/vnd.google-apps.folder",
                "parents": ["0AM-sdiio-Y-0Uk9PVA"]}))
        """
        if file_metadata.get("name", None) is None:
            raise InvalidFileName("Invalid File name specified")
        file = self.service.files().create(body=file_metadata, supportsTeamDrives=True,
            supportsAllDrives=True).execute()
        return file

    def move_file(self, query={"file_id": None}):
        """ Specify the file_id which is to be moved and the folder_id
        where it is to be moved. The folder_id can be of any folder
        in My Drive, Shared Drive or the My Drive or Shared Drive itself. 
        Returns the id, parents of the file after the move operation.
        """
        """ Examples
            print(gdrive.move_file({"file_id": "12QoyODS0f8N6vRAGWgjy8omTako3k7M5", "folder_id": "1J-C98GtbRh7jLMy_a4BfQVUNMtUOXUqp"}))
            print(gdrive.move_file({"file_id": "12QoyODS0f8N6vRAGWgjy8omTako3k7M5", "folder_id": "0AM-sdiio-Y-0Uk9PVA"}))
        """
        # Retrieve the existing parents to remove
        if query.get("file_id", None) is None or query.get("folder_id", None) is None:
            raise InvalidMoveRequest("One of file_id or folder_id is missing")
        file = self.file_metadata({"id": query["file_id"], "fields": "parents"})
        previous_parents = ",".join(file.get('parents'))
        # Move the file to the new folder
        file = self.service.files().update(fileId=query["file_id"],
                                            addParents=query["folder_id"],
                                            removeParents=previous_parents,
                                            fields='id, parents',
                                            supportsAllDrives=True,
                                            supportsTeamDrives=True).execute()
        return file
    
    def move_folder(self, folder_obj, parent_id):
        """ Takes in a 'folder_obj' as returned by the 
        folder_structure function, the 'parent_id' of the 
        location where it is to be moved.
        Moves a folder with the same structure as it exists
        into another folder of My Drive, Shared Drive or My Drive
        and Shared Drive themselves. 
        """
        """ Examples
            # Obtain a folder structure
            folder = gdrive.folder_structure(query={"id": "1hvz9w5rXltrckGaH986uck_iOh1vxAmJ", "drive_id": "0AM-sdiio-Y-0Uk9PVA"})
            gdrive.move_folder(folder_obj=folder, parent_id="1J-C98GtbRh7jLMy_a4BfQVUNMtUOXUqp") # Parent is some folder in My Drive
            gdrive.move_folder(folder_obj=folder, parent_id="0AM-sdiio-Y-0Uk9PVA") # Here the parent_id is of a Shared Drive
            gdrive.move_folder(folder_obj=folder, parent_id="1Vx2wp5oWSJGhgk8Rin_6wUqllm1IZ1L9") # Parent is some folder in Shared Drive
            gdrive.move_folder(folder_obj=folder, parent_id="0AJzA_NPQBPA2Uk9PVA") # Here the parent_id is of My Drive
        """
        created_folder = self.create(file_metadata={
                                    "name": folder_obj["name"],
                                    "mimeType": "application/vnd.google-apps.folder",
                                    "parents": [parent_id]
                                })
        for file in folder_obj["file_list"]:
            self.move_file(query={ "file_id": file["id"], "folder_id": created_folder["id"] })
        for folder in folder_obj["folder_list"]:
            self.move_folder(folder, created_folder["id"])
    
    def move_folder_delete(self, folder_obj, parent_id):
        """ Takes in a 'folder_obj' as returned by the 
        folder_structure function, the 'parent_id' of the 
        location where it is to be moved.
        Moves a folder with the same structure as it exists
        into another folder of My Drive, Shared Drive or My Drive
        and Shared Drive themselves. The older folder with no 
        remaining files are then deleted.
        """
        """ Examples
            # Moving a My Drive folder to a Shared Drive
            folder = gdrive.folder_structure(query={"id": "103E1k8UA8hklRZ1600j6vT8AMOItznbU"})
            gdrive.move_folder_delete(folder, gdrive.shared_drive)

            # Moving Shared drive folder to My Drive
            folder = gdrive.folder_structure(query={"id": "1tSOgVFoV7G5_jdpKqmUCwJSyc5FSe3Je", "drive_id": gdrive.shared_drive})
            gdrive.move_folder_delete(folder, gdrive.my_drive)
        """
        self.move_folder(folder_obj=folder_obj, parent_id=parent_id)
        self.delete(query={"id": folder_obj["id"]})

    def copy(self, query={"id": None, "body": None}):
        """ Returns a file resource object for the copied file with fields kind,
        id, name, mimeType. Takes "id" of a file and "body" with any modifications
        for the copied file metadata.
        """
        """ Examples
            # copying a file
            print(gdrive.copy(query={"id": "1LI1m1d9I2k0QUwqN2yqRXKcHfghwfkA4"}))

            # Copying a file to different folder, my_drive, shared_drive
            print(gdrive.copy(query={"id": "1LI1m1d9I2k0QUwqN2yqRXKcHfghwfkA4", "body": {"parents": [gdrive.my_drive]}}))
        """
        if query.get("id") is None:
            raise InvalidIdError("Invalid ID specified")
        obj = self.service.files().copy(fileId=query["id"], body=query.get("body", None), supportsAllDrives=True).execute()
        return obj

    def delete(self, query={"id": None}):
        """ Deletes a file or folder with the 'id' as specified in the query dictionary.
        Raises InvalidIdError of 'id' is not specified.
        """
        """ Examples
            gdrive.delete({"id": "1CIUhnqEOXTsIVpPYDqAgXHOY0oQp4Jhl"})
        """
        if query.get("id", None) is None:
            raise InvalidIdError("Invalid ID specified")
        self.service.files().delete(fileId=query["id"], supportsAllDrives=True).execute()

if __name__ == '__main__':
    gdrive = GDrive()