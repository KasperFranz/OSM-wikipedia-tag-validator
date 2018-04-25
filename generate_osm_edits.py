import argparse
import common
import os
import wikimedia_connection.wikimedia_connection as wikimedia_connection
import osm_bot_abstraction_layer.osm_bot_abstraction_layer as osm_bot_abstraction_layer
import osm_handling_config.global_config as osm_handling_config

def parsed_args():
    parser = argparse.ArgumentParser(description='Production of webpage about validation of wikipedia tag in osm data.')
    parser.add_argument('-file', '-f', dest='file', type=str, help='name of yaml file produced by validator')
    args = parser.parse_args()
    if not (args.file):
        parser.error('Provide yaml file generated by wikipedia validator')
    return args

def is_text_field_mentioning_wikipedia_or_wikidata(text):
    text = text.replace("http://wiki-de.genealogy.net/GOV:", "")
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

def load_errors():
    args = parsed_args()
    filepath = common.get_file_storage_location()+"/"+args.file
    if not os.path.isfile(filepath):
        print(filepath + " is not a file, provide an existing file")
        return
    return common.load_data(filepath)

def fit_wikipedia_edit_description_within_character_limit_new(new, reason):
    comment = "adding [wikipedia=" + new + "]" + reason
    if(len(comment)) > character_limit_of_description():
        comment = "adding wikipedia tag " + reason
    if(len(comment)) > character_limit_of_description():
        raise("comment too long")
    return comment

def fit_wikipedia_edit_description_within_character_limit_changed(now, new, reason):
    comment = "[wikipedia=" + now + "] to [wikipedia=" + new + "]" + reason
    if(len(comment)) > character_limit_of_description():
        comment = "changing wikipedia tag to <" + new + ">" + reason
    if(len(comment)) > character_limit_of_description():
        comment = "changing wikipedia tag " + reason
    if(len(comment)) > character_limit_of_description():
        raise("comment too long")
    return comment

def get_and_verify_data(e):
    return osm_bot_abstraction_layer.get_and_verify_data(e['osm_object_url'], e['prerequisite'], note_or_fixme_review_request_indication)

def handle_follow_wikipedia_redirect(e):
    if e['error_id'] != 'wikipedia wikidata mismatch - follow wikipedia redirect':
        return
    language_code = wikimedia_connection.get_language_code_from_link(e['prerequisite']['wikipedia'])
    if language_code != "pl":
        print(e['prerequisite']['wikipedia'] + " is not in the expected language code!")
        return
    data = get_and_verify_data(e)
    if data == None:
        return None
    now = data['tag']['wikipedia']
    new = e['desired_wikipedia_target']
    reason = ", as current tag is a redirect and the new page matches present wikidata"
    comment = fit_wikipedia_edit_description_within_character_limit_changed(now, new, reason)
    data['tag']['wikipedia'] = e['desired_wikipedia_target']
    discussion_url = "https://forum.openstreetmap.org/viewtopic.php?id=59649"
    automatic_status = osm_bot_abstraction_layer.fully_automated_description()
    type = e['osm_object_url'].split("/")[3]
    source = "wikidata, OSM"
    osm_bot_abstraction_layer.make_edit(e['osm_object_url'], comment, automatic_status, discussion_url, type, data, source)

def change_to_local_language(e):
    if e['error_id'] != 'wikipedia tag unexpected language':
        return
    #language_code = wikimedia_connection.get_language_code_from_link(e['prerequisite']['wikipedia'])
    #if language_code != "pl":
    #    return
    data = get_and_verify_data(e)
    if data == None:
        return None
    now = data['tag']['wikipedia']
    new = e['desired_wikipedia_target']
    reason = ", as wikipedia page in the local language should be preferred"
    comment = fit_wikipedia_edit_description_within_character_limit_changed(now, new, reason)
    data['tag']['wikipedia'] = e['desired_wikipedia_target']
    discussion_url = None
    automatic_status = osm_bot_abstraction_layer.manually_reviewed_description()
    type = e['osm_object_url'].split("/")[3]
    source = "wikidata, OSM"
    osm_bot_abstraction_layer.make_edit(e['osm_object_url'], comment, automatic_status, discussion_url, type, data, source)

def filter_reported_errors(reported_errors, matching_error_ids):
    errors_for_removal = []
    for e in reported_errors:
        if e['error_id'] in matching_error_ids:
            errors_for_removal.append(e)
    return errors_for_removal

def add_wikidata_tag_from_wikipedia_tag(reported_errors):
    errors_for_removal = filter_reported_errors(reported_errors, ['wikidata from wikipedia tag'])
    if errors_for_removal == []:
        return
    automatic_status = osm_bot_abstraction_layer.fully_automated_description()
    affected_objects_description = ""
    comment = "add wikidata tag based on wikipedia tag"
    discussion_url = 'https://forum.openstreetmap.org/viewtopic.php?id=59925'
    api = osm_bot_abstraction_layer.get_correct_api(automatic_status, discussion_url)
    source = "wikidata, OSM"
    builder = osm_bot_abstraction_layer.ChangesetBuilder(affected_objects_description, comment, automatic_status, discussion_url, source)
    builder.create_changeset(api)

    for e in errors_for_removal:
        data = get_and_verify_data(e)
        if data == None:
            continue
        language_code = wikimedia_connection.get_language_code_from_link(data['tag']['wikipedia'])
        article_name = wikimedia_connection.get_article_name_from_link(data['tag']['wikipedia'])
        wikidata_id = wikimedia_connection.get_wikidata_object_id_from_article(language_code, article_name)
        if language_code != "pl":
            raise "UNEXPECTED LANGUAGE CODE for Wikipedia tag in " + e['osm_object_url']
        print(e['osm_object_url'])
        print(wikidata_id)
        reason = ", as wikidata tag may be added based on wikipedia tag"
        change_description = e['osm_object_url'] + " " + str(e['prerequisite']) + " to " + wikidata_id + reason
        print(change_description)
        osm_bot_abstraction_layer.sleep(25)
        data['tag']['wikidata'] = wikidata_id
        type = e['osm_object_url'].split("/")[3]
        osm_bot_abstraction_layer.update_element(api, type, data)

    api.ChangesetClose()
    osm_bot_abstraction_layer.sleep(60)

def add_wikipedia_tag_from_wikidata_tag(reported_errors):
    errors_for_removal = filter_reported_errors(reported_errors, ['wikipedia from wikidata tag'])
    if errors_for_removal == []:
        return
    #TODO check location - checking language of desired article is not helpful as Polish articles exist for objects outside Poland...
    #language_code = wikimedia_connection.get_language_code_from_link(e['desired_wikipedia_target'])
    #if language_code != "pl":
    #    return
    automatic_status = osm_bot_abstraction_layer.fully_automated_description()
    affected_objects_description = ""
    comment = "add wikipedia tag based on wikidata tag"
    discussion_url = 'https://forum.openstreetmap.org/viewtopic.php?id=59888'
    api = osm_bot_abstraction_layer.get_correct_api(automatic_status, discussion_url)
    source = "wikidata, OSM"
    builder = osm_bot_abstraction_layer.ChangesetBuilder(affected_objects_description, comment, automatic_status, discussion_url, source)
    builder.create_changeset(api)

    for e in errors_for_removal:
        data = get_and_verify_data(e)
        if data == None:
            continue
        new = e['desired_wikipedia_target']
        reason = ", as wikipedia tag may be added based on wikidata"
        change_description = e['osm_object_url'] + " " + str(e['prerequisite']) + " to " + new + reason
        print(change_description)
        data['tag']['wikipedia'] = e['desired_wikipedia_target']
        type = e['osm_object_url'].split("/")[3]
        osm_bot_abstraction_layer.update_element(api, type, data)

    api.ChangesetClose()
    osm_bot_abstraction_layer.sleep(60)

def add_wikipedia_links_basing_on_old_style_wikipedia_tags(reported_errors):
    matching_error_ids = [
                'wikipedia tag from wikipedia tag in an outdated form and wikidata',
                'wikipedia tag from wikipedia tag in an outdated form',
                ]
    errors_for_removal = filter_reported_errors(reported_errors, matching_error_ids)
    if errors_for_removal == []:
        return
    #TODO check location - checking language of desired article is not helpful as Polish articles exist for objects outside Poland...
    #language_code = wikimedia_connection.get_language_code_from_link(e['desired_wikipedia_target'])
    #if language_code != "pl":
    #    return

    automatic_status = osm_bot_abstraction_layer.fully_automated_description()
    affected_objects_description = ""
    comment = "adding wikipedia and wikidata tags based on old style wikipedia tags"
    discussion_url = 'https://forum.openstreetmap.org/viewtopic.php?id=59665'
    api = osm_bot_abstraction_layer.get_correct_api(automatic_status, discussion_url)
    source = "wikidata, OSM"
    builder = osm_bot_abstraction_layer.ChangesetBuilder(affected_objects_description, comment, automatic_status, discussion_url, source)
    builder.create_changeset(api)

    for e in errors_for_removal:
        data = get_and_verify_data(e)
        if data == None:
            continue
        new = e['desired_wikipedia_target']
        data['tag']['wikipedia'] = new
        reason = ", as standard wikipedia tag is better than old style wikipedia tags"
        change_description = e['osm_object_url'] + " " + str(e['prerequisite']) + " to " + new + reason
        if e['error_id'] == 'wikipedia tag from wikipedia tag in an outdated form':
            language_code = wikimedia_connection.get_language_code_from_link(e['desired_wikipedia_target'])
            article_name = wikimedia_connection.get_article_name_from_link(e['desired_wikipedia_target'])
            wikidata_id = wikimedia_connection.get_wikidata_object_id_from_article(language_code, article_name)
            if wikidata_id == None:
                print(wikimedia_connection.wikipedia_url(language_code, article_name) + " from " + e['osm_object_url'] + " has no wikidata entry")
                continue
            data['tag']['wikidata'] = wikidata_id
            change_description += " +adding wikidata=" + wikidata_id
        print(change_description)
        type = e['osm_object_url'].split("/")[3]
        osm_bot_abstraction_layer.update_element(api, type, data)

    api.ChangesetClose()
    osm_bot_abstraction_layer.sleep(60)

def main():
    wikimedia_connection.set_cache_location(osm_handling_config.get_wikimedia_connection_cache_location())
    # for testing: api="https://api06.dev.openstreetmap.org", 
    # website at https://master.apis.dev.openstreetmap.org/
    reported_errors = load_errors()
    #requires manual checking is it operating in Poland #add_wikipedia_links_basing_on_old_style_wikipedia_tags(reported_errors)
    #requires manual checking is it operating in Poland #add_wikipedia_tag_from_wikidata_tag(reported_errors)
    add_wikidata_tag_from_wikipedia_tag(reported_errors) #self-checking location based on Wikipedia language code
    for e in reported_errors:
        #handle_follow_wikipedia_redirect(e)
        #change_to_local_language(e)
        pass

if __name__ == '__main__':
    main()
