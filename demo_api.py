import requests
import json
import os
from requests.auth import HTTPBasicAuth
from requests.auth import AuthBase
import shutil
import boto3 #AWS 
from botocore.exceptions import ClientError
import logging
import tqdm
from PIL import Image, ImageOps 
import botocore
import boto3.s3.transfer as s3transfer
import tqdm
import time
from dotenv import load_dotenv 

#Load environment variables
load_dotenv()

#BOTO3 configuration
bucket = "upgraded-unfiltered"
botocore_config = botocore.config.Config(max_pool_connections=20)
s3_client = boto3.client("s3", config=botocore_config)
s3_resource = boto3.resource("s3")
transfer_config = s3transfer.TransferConfig(
    use_threads=True,
    max_concurrency=20,
)

# API vars
API_KEY = os.getenv("API_KEY")
API_ENDPOINT = "https://api.letsenhance.io/v1/pipeline"  # POST
GET_API = "https://api.letsenhance.io/v1/pipeline/"
IMAGE_LOCATION = r"\test"

#Header for sending Requests
headers = {"Content-type": "application/json", "X-API-KEY": API_KEY}
#open JSON file
f = open(
    "snippet.json",
)
payload = json.load(f)


json_width = payload["operations"][3]["width"]
json_height = payload["operations"][3]["height"]

#File Paths
current_directory = os.path.dirname(os.path.realpath(__file__))
pre_enhanced_folder = current_directory + r"\test"
my_path = os.path.dirname(__file__)

#
bucket = "upgraded-unfiltered"

#Global Count for number of images processed
num_processed = 0

#THis all 4x3
#This function walks through an image directory and then sends the images to the Lets Enhance API.
#When Lets Enhance finishes the enhancment process the images is downloaded into the Upgraded directory
def lets_enhance():
    global num_processed
    for root, dirs, files in os.walk(pre_enhanced_folder):
        if len(files) == 0:
            print("empty Directory, continueing to Boto3 Upload")
            break
        else:
            for file in files:
                if file.startswith("."):
                    continue
                open_path = my_path + r"/test/" + file
                pic = Image.open(open_path)
                w, h = pic.size
                s3URL = ""
                
                #Setting the widht
                #4x3
                if w > h: #Horizontal or Landscape
                    json_width = 9600 #600
                    json_height = 7600
                elif h>w: #Portrait or Verticle
                    json_height = 9600
                    json_width = 7600
                else: #Square
                    json_height = 9600
                    json_width = 9600
                s3_url = "https://original-unfiltered.s3.us-west-1.amazonaws.com/" + file
                payload["source"]["http"]["url"] = s3_url
                request = requests.post(url=API_ENDPOINT, headers=headers, json=payload)
                print(request.status_code)
                
                post_json = request.json()
                #print(post_json)
                
                #id of the image sent in post request
                id = post_json["pipeline"]["id"]
                get_id = GET_API + str(id)
                response = requests.get(get_id, headers=headers)
                print("Status code for GET request: ", response.status_code)
                if response.status_code != 200:
                    print("ERROR, problem sending image")
                json = response.json()
                print("STATUS = ",json['pipeline']["status"])
                if json["pipeline"]["status"] == "ERROR":
                    print("Error = \n\n ", json)
                # print(json)
                headers["Connection"] = "keep-alive"
                headers["Keep-Alive"] = "timeout=5, max=100"
                while json["pipeline"]["status"] == "PROCESSING":
                    response = requests.get(get_id, headers=headers, stream=True)
                    json = response.json()
                    print("Processing")
                # print("STATUS = ",json['pipeline']["status"] , "json = ", json)
                pic.close()
                if json["pipeline"]["status"] == "DONE":
                    print(response.json())
                    x = response.json()
                    down_URL = x["pipeline"]["results"][0]["output_object"]["tmp_url"]
                    file_name = x["pipeline"]["results"][0]["output_object"]["filename"]
                    r = requests.get(down_URL, stream=True)
                    if not os.path.exists("Upgraded"):
                        os.makedirs("Upgraded")
                    path_to_upgraded = "./Upgraded/" + file_name
                    with open(path_to_upgraded, "wb") as f:
                        for chunk in r.iter_content(chunk_size=1024):
                            if chunk:
                                f.write(chunk)
                    #os.remove(open_path)
                    num_processed += 1
                    print(f"\n\nDone {num_processed} of {len(files)}")
                else:
                    #should use logging or better output statements. Sorry was lazy
                    print(f"Error on file: {file}")
                    print(f"\n\nJSON = {json}")
    

def upload_upgrades():
    upload_args = {"ACL": "public-read", "ContentType": "image/jpeg"}
    file_num = 1

    print("Uploading:")
    # file_not_found = False

    #This is a progress bar.
    # progress = tqdm.tqdm(
    #     desc="Upload", unit="B", unit_scale=1, position=1, bar_format="{desc:<10}{percentage:3.0f}%|{bar:10}{r_bar}"
    # )
    
    s3t = s3transfer.create_transfer_manager(s3_client, transfer_config)
    for root, dirs, files in os.walk("Upgraded"):
        num_files = len(files)
        for x in files:
            file_not_found = False
            f_path = my_path + r"/Upgraded/" + x
            try:
                s3_client.head_object(Bucket=bucket, Key=os.path.basename(x))
            except ClientError:
                file_not_found = True
            if file_not_found:
                # bucket_object = s3_resource.Object(bucket_name= bucket, key = os.path.basename(x))
                # bucket_object.upload_file(f_path, ExtraArgs=upload_args)
                s3t.upload(
                    f_path,
                    bucket #,
                    key=os.path.basename(x),
                    subscribers=[
                        s3transfer.ProgressCallbackInvoker(progress.update),
                    ],
                )
                print(f"Uploaded {x}, {file_num} of {num_files}")
                delete_path = my_path + r"/Upgraded/" + x
                # os.remove(delete_path)
            else:
                file_num = 1 + file_num
                continue
            file_num = 1 + file_num
        s3t.shutdown()
        #progress.close()
    print("Done Uploading to S3")

    # del_path = os.getcwd() + r"/SKU_Name"
    # try:
    #    shutil.rmtree(del_path)
    # except:
    #    print("Error while deleting directory")


def main():
    print("Main")
    # pre_up()
    # hold = input("holdd")
    lets_enhance()
    #upload_upgrades()


if __name__ == "__main__":
    main()
# progress bar display for downloading images to local.
# https://stackoverflow.com/questions/37573483/progress-bar-while-download-file-over-http-with-requests/37573701

# response = requests.get(GET_API, headers=headers)
# print("Status code for GET request: ", response.status_code)
# print("Headers: ", response.headers)
# #print(response.text)asd
# json = response.json()
# print(json)

# test = json.dumps(json)
# print(test)
# print(response.json())


# total_size_in_bytes= int(response.headers.get('content-length', 0))
# block_size = 1024 #1 Kibibyte
# progress_bar = tqdm(total=total_size_in_bytes, unit='iB', unit_scale=True)
# with open('test.dat', 'wb') as file:
#     for data in response.iter_content(block_size):
#         progress_bar.update(len(data))
#         file.write(data)
# progress_bar.close()
# if total_size_in_bytes != 0 and progress_bar.n != total_size_in_bytes:
#     print("ERROR, something went wrong")


# image_url = "https://cdn.pixabay.com/photo/2020/02/06/09/39/summer-4823612_960_720.jpg"
# filename = image_url.split("/")[-1]

# # Open the url image, set stream to True, this will return the stream content.
# r = requests.get(image_url, stream = True)

# # Check if the image was retrieved successfully
# if r.status_code == 200:
#     # Set decode_content value to True, otherwise the downloaded image file's size will be zero.
#     r.raw.decode_content = True

#     # Open a local file with wb ( write binary ) permission.
#     with open(filename,'wb') as f:
#         shutil.copyfileobj(r.raw, f)

#     print('Image sucessfully Downloaded: ',filename)
# else:
#     print('Image Couldn\'t be retreived')
