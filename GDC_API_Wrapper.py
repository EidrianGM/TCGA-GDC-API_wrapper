#! user/bin/python
#! Adrian Garcia Moreno

# Wrapper of GDC API to explore and download data

import sys
sys.executable
sys.path.append("/usr/lib/python2.7/site-packages/")
import icgc # API to controll prgramatically https://dcc.icgc.org/search
import requests
import json
import re
import time
import os

# endpts = ["files", "cases", "projects", "annotations"]
# extraendpts = ["status", "data", "manifest", "slicing","submission"]
# ops = ["=","!=",">","<",">=","<=","is","not","in","exclude","and","or"]

def def_params(filters, fields, groups = "", size = "10",
               form = "TSV", pretty = "false", from_ = "0",
               sort = "", asc_or_desc = ""):
    if sort != "":
        sort = sort+":"+asc_or_desc

    params = {
    "filters": json.dumps(filters),
    "format": form,
    "pretty": pretty,
    "fields": ",".join(fields),
    "expand": ",".join(groups),
    "size": size,
    "from": from_,
    "sort": sort
    #"facets": ""
    }
    return params

def def_filters(langquery, main_op = "and"):
    # example of langquery =
    # "1value,2value;in;1field;and;3value,4value;in;anotherfield"
    filters = {"op":main_op,
               "content":[]}
    langquery = langquery.split(";")
    i = 0
    for query in range(len(langquery)//3):
        values, op, field = langquery[i:i+3]
        filters["content"].append({
            "op":op,
            "content":{
              "field":field,
              "value":values.split(",")
             }
            })
    i += 3
    return filters

def get_response(endpt, params, infoplus = False, token = ""):
    header = {"Content-Type":"application/json"}
    if token != "":
        header["X-Auth-Token"] = token

    query_url = 'https://api.gdc.cancer.gov/{}/'.format(endpt)
    print("Querying: {}".format(query_url))
    if infoplus:
        print("for extra metainfo")
        response = requests.get(query_url + "_mapping", params = params, headers = header)
    else:
        response = requests.get(query_url, params = params, headers = header)
    return response

def get_fields(endpt, groups = False, token = ""):
    response = get_response(endpt, "", True, token)
    response = response.json()
    fields = response["fields"]
    if groups:
        groups = response["expand"]
        #fields = {"fields":fields, "groups":groups}
    return fields, groups

def get_values_of_field(endpt, field, filters = "", token = ""):
    params = {
    "filters": json.dumps(filters),
    "facets": field
    }
    response = get_response(endpt, params, False, token)
    response = response.json()
    try:
        facets = response['data']['aggregations'][field]['buckets']
        aggregate_n_value = {list(value.values())[0]:list(value.values())[1] for value in facets}
        return aggregate_n_value
    except:
        print("Error with {}/{}".format(endpt, field))
        return "Non Aviable Info"

def get_token(path2tokenfile):
    with open(path2tokenfile,"r") as token:
        token_string = str(token.read().strip())
    return token_string

def TCGA_downloader(file_ids, outfolder, token = ""):
    header = {"Content-Type":"application/json"}
    if token != "":
        header["X-Auth-Token"] = token

    if type(file_ids) != list:
        file_ids = [file_ids]

    os.makedirs(outfolder, exist_ok = True)
    for fileID in file_ids:
        query_url = "https://api.gdc.cancer.gov/data/{}".format(fileID)
        response = requests.get(query_url, headers = header)
        try:
            response_head_cd = response.headers["Content-Disposition"]
            file_name = re.findall("filename=(.+)", response_head_cd)[0]
        except:
            file_name = "no_name.txt"
            while file_name in os.listdir(outfolder):
                file_name = time.strftime("%H:%M:%S", time.gmtime())+"_"+file_name
        with open(outfolder+file_name, "wb") as output_file:
            output_file.write(response.content)
        print("Downloaded {}".format(file_name))

def get_allqueryable(endpts, token = ""):
    allqueryable = {}
    for endpt in endpts:
        fields, groups = get_fields(endpt, True, token = token)
        allqueryable[endpt] = {}
        for field in fields:
            print("{}/{}".format(endpt,field))
            values = get_values_of_field(endpt, field, token = token)
            allqueryable[endpt][field] = values
        for group in groups:
            print("{}/{}".format(endpt,group))
            values = get_values_of_field(endpt, group, token = token)
            allqueryable[endpt][group] = values
    with open("all_queryable.json", "w") as all_queryable_json:
        json.dump(allqueryable, all_queryable_json)
    return allqueryable

def get_realqueryable(allqueryable):
    aviable_querys = {}
    for endpt in allqueryable:
        aviable_data = []
        non_aviable_data = []
        missing_data = []
        aviable_querys[endpt] = {}
        for file_field in all_queryable[endpt]:
            data = all_queryable[endpt][file_field]
            if data == "Non Aviable Info":
                non_aviable_data.append(file_field)
            elif len(data) == 1 and "_missing" in data[0].keys():
                missing_data.append(file_field)
            else:
                aviable_data.append(file_field)
        aviable_querys[endpt]["Non Aviable Info"] = non_aviable_data
        aviable_querys[endpt]["Aviable Info"] = aviable_data
        aviable_querys[endpt]["_missing"] = missing_data
    with open("aviable_querys.json", "w") as all_queryable_json:
        json.dump(aviable_querys, all_queryable_json)
    return aviable_querys
