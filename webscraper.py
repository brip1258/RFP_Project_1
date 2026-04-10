from bs4 import BeautifulSoup
from tqdm import tqdm
import requests
import json

# "https://www.bidnetdirect.com/colorado/larimer-county"

def remove_whitespace(string: str) -> str:
    return " ".join(string.split())

def get_rfp_links(link: str) -> list:
    html = requests.get(link)
    soup = BeautifulSoup(html.text, "html.parser")
    links_list = []

    for link in soup.find_all("a", class_="solicitation-link mets-command-link", href = True):
        links_list.append("https://www.bidnetdirect.com" + link['href'])

    return links_list

# https://www.bidnetdirect.com/colorado/solicitations/open-bids/The-Ranch-Events-Complex-Fence-Installation/0000418729?purchasingGroupId=8409951&origin=2

def get_information(link:str) -> list:
    html = requests.get(link)
    soup = BeautifulSoup(html.text, "html.parser")
    list = []

    list.append(remove_whitespace(soup.find("h1").get_text()))

    for item in soup.find_all("div", class_="mets-field mets-field-view"):
        text = item.find("div", class_="mets-field-body").get_text()
        list.append(remove_whitespace(text))

    return list


json_list = []

rfp_links = get_rfp_links(input("Please put the link here: "))

for link in tqdm(rfp_links):
    info_list = get_information(link)
    info_dict = {"Name": info_list[0],
                 "Location": info_list[1],
                 "Publication Date": info_list[2],
                 "Closing Date": info_list[3],
                 "Solicitation Number": info_list[4]}
    json_list.append(info_dict)

with open("data/information.json","w") as file:
    json.dump(json_list, file, indent = 2)
    print(f"Done! Uploaded to {file.name}!")

