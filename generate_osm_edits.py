import osmapi
import time
import argparse
import common
import os
import wikipedia_connection
# docs: http://osmapi.metaodi.ch/

def bot_username():
    return "Mateusz Konieczny - bot account"

def manual_username():
    return "Mateusz Konieczny"

def character_limit_of_description():
    return 255

def parsed_args():
    parser = argparse.ArgumentParser(description='Production of webpage about validation of wikipedia tag in osm data.')
    parser.add_argument('-file', '-f', dest='file', type=str, help='name of yaml file produced by validator')
    args = parser.parse_args()
    if not (args.file):
        parser.error('Provide yaml file generated by wikipedia validator')
    return args

def get_data(api, id, type):
    try:
        if type == 'node':
            return api.NodeGet(id)
        if type == 'way':
            return api.WayGet(id)
        if type == 'relation':
            return api.RelationGet(id)
    except osmapi.ElementDeletedApiError:
        return None
    assert(False)

def update_element(api, type, data):
    if type == 'node':
        return api.NodeUpdate(data)
    if type == 'way':
        return api.WayUpdate(data)
    if type == 'relation':
        return api.RelationUpdate(data)
    assert False, str(type) + " type as not recognised"

def is_text_field_mentioning_wikipedia_or_wikidata(text):
    if text.find("wikipedia") != -1:
        return True
    if text.find("wikidata") != -1:
        return True
    if text.find("wiki") != -1:
        return True
    return False

def note_or_fixme_review_request_indication(data):
    fixme = ""
    note = ""
    if 'fixme' in data['tag']:
        fixme = data['tag']['fixme']
    if 'note' in data['tag']:
        note = data['tag']['note']
    text_dump = "fixme=<" + fixme + "> note=<" + note + ">"
    if is_text_field_mentioning_wikipedia_or_wikidata(fixme):
        return text_dump
    if is_text_field_mentioning_wikipedia_or_wikidata(note):
        return text_dump
    return None

def prerequisite_failure_reason(e, data):
    advice = note_or_fixme_review_request_indication(data)
    if advice != None:
        return advice + " was present for " + e['osm_object_url']

    for key in e['prerequisite'].keys():
        if e['prerequisite'][key] == None:
            if key in data['tag']:
                return("failed " + key + " prerequisite, as key " + key + " was present for " + e['osm_object_url'])
        elif key not in data['tag']:
            return("failed " + key + " prerequisite, as key " + key + " was missing for " + e['osm_object_url'])
        elif e['prerequisite'][key] != data['tag'][key]:
            return("failed " + key + " prerequisite for " + e['osm_object_url'])
    return None

def load_errors():
    args = parsed_args()
    filepath = common.get_file_storage_location()+"/"+args.file
    if not os.path.isfile(filepath):
        print(filepath + " is not a file, provide an existing file")
        return
    return common.load_data(filepath)

def sleep(time_in_s):
    print("Sleeping")
    time.sleep(time_in_s)

def make_edit(affected_objects, comment, automatic_status, discussion_url, api, type, data):
    if(len(comment) > character_limit_of_description()):
        raise "comment too long"
    if(len(affected_objects + " " + comment) <= character_limit_of_description()):
        comment = affected_objects + " " + comment
    else:
        print(affected_objects)
    print(comment)
    changeset_description = {
        "comment": comment,
        "automatic": automatic_status,
        "source_code": "https://github.com/matkoniecz/OSM-wikipedia-tag-validator.git",
        }
    if discussion_url != None:
        changeset_description["discussion_before_edits"] = discussion_url
    api.ChangesetCreate(changeset_description)
    update_element(api, type, data)
    api.ChangesetClose()
    sleep(60)

def fit_wikipedia_edit_description_within_character_limit(new, reason):
    comment = "adding [wikipedia=" + new + "]" + reason
    if(len(comment)) > character_limit_of_description():
        comment = "adding wikipedia tag " + reason
    if(len(comment)) > character_limit_of_description():
        raise("comment too long")
    return comment

def fit_wikipedia_edit_description_within_character_limit(now, new, reason):
    comment = "[wikipedia=" + now + "] to [wikipedia=" + new + "]" + reason
    if(len(comment)) > character_limit_of_description():
        comment = "changing wikipedia tag to <" + new + ">" + reason
    if(len(comment)) > character_limit_of_description():
        comment = "changing wikipedia tag " + reason
    if(len(comment)) > character_limit_of_description():
        raise("comment too long")
    return comment

def get_and_verify_data(e, api):
    type = e['osm_object_url'].split("/")[3]
    id = e['osm_object_url'].split("/")[4]
    data = get_data(api, id, type)
    if data == None:
        return None
    failure = prerequisite_failure_reason(e, data)
    if failure != None:
        print(failure)
        return None
    return data

def handle_follow_redirect(e, api):
    if e['error_id'] != 'wikipedia wikidata mismatch - follow redirect':
        return
    language_code = wikipedia_connection.get_language_code_from_link(e['prerequisite']['wikipedia'])
    if language_code != "pl":
        return
    data = get_and_verify_data(e, api)
    if data == None:
        return None
    now = data['tag']['wikipedia']
    new = e['desired_wikipedia_target']
    reason = ", as current tag is a redirect and the new page matches present wikidata"
    comment = fit_wikipedia_edit_description_within_character_limit(now, new, reason)
    data['tag']['wikipedia'] = e['desired_wikipedia_target']
    discussion_url = "https://forum.openstreetmap.org/viewtopic.php?id=59649"
    automatic_status = "yes"
    type = e['osm_object_url'].split("/")[3]
    make_edit(e['osm_object_url'], comment, automatic_status, discussion_url, api, type, data)

def change_to_local_language(e, api):
    if e['error_id'] != 'wikipedia tag unexpected language':
        return
    #language_code = wikipedia_connection.get_language_code_from_link(e['prerequisite']['wikipedia'])
    #if language_code != "pl":
    #    return
    data = get_and_verify_data(e, api)
    if data == None:
        return None
    new = e['desired_wikipedia_target']
    reason = ", as wikipedia page in the local language should be preferred"
    comment = fit_wikipedia_edit_description_within_character_limit(new, reason)
    data['tag']['wikipedia'] = e['desired_wikipedia_target']
    discussion_url = None
    automatic_status = "no, it is a manually reviewed edit"
    type = e['osm_object_url'].split("/")[3]
    make_edit(e['osm_object_url'], comment, automatic_status, discussion_url, api, type, data)

def add_wikipedia_tag_based_wikidata(e, api):
    if e['error_id'] != 'wikipedia from wikidata tag':
        return
    #TODO check location - checking language of desired article is not helpful as Polish articles exist for objects outside Poland...
    #language_code = wikipedia_connection.get_language_code_from_link(e['desired_wikipedia_target'])
    #if language_code != "pl":
    #    return
    data = get_and_verify_data(e, api)
    if data == None:
        return None
    now = None
    new = e['desired_wikipedia_target']
    reason = ", as wikipedia page in the local language should be preferred"
    comment = fit_wikipedia_edit_description_within_character_limit(now, new, reason)
    data['tag']['wikipedia'] = e['desired_wikipedia_target']
    discussion_url = None
    automatic_status = "no, it is a manually reviewed edit"
    type = e['osm_object_url'].split("/")[3]
    make_edit(e['osm_object_url'], comment, automatic_status, discussion_url, api, type, data)

def main():
    bot_api = osmapi.OsmApi(username = bot_username(), passwordfile = "password.secret")
    user_api = osmapi.OsmApi(username = manual_username(), passwordfile = "password.secret")
    # for testing: api="https://api06.dev.openstreetmap.org", 
    # website at https://master.apis.dev.openstreetmap.org/
    reported_errors = load_errors()
    for e in reported_errors:
        handle_follow_redirect(e, bot_api)
        change_to_local_language(e, user_api)
        #add_wikipedia_tag_based_wikidata(e, id, type, user_api)

if __name__ == '__main__':
    main()
