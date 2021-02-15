import argparse
import yaml
import os.path
import common
import datetime

def generate_output_for_given_area(raw_reports_data_filepath, main_output_name_part):
    if not os.path.isfile(raw_reports_data_filepath):
        print(raw_reports_data_filepath + " is not a file, provide an existing file")
        return
    reports_data = common.load_data(raw_reports_data_filepath)
    main_report_count = generate_html_file(reports_data, main_output_name_part + ".html", for_review(), "Remember to check whatever edit makes sense! All reports are at this page because this tasks require human judgment to verify whatever proposed edit makes sense.")
    generate_html_file(reports_data, main_output_name_part + " - obvious.html", obvious_fixes(), "Proposed edits at this page are so obvious that automatic edit makes sense.")
    generate_html_file(reports_data, main_output_name_part + " - test.html", for_tests(), "This page contains reports that are tested or are known to produce false positives. Be careful with using this data.")
    note_unused_errors(reports_data)
    return main_report_count

def generate_html_file(errors, output_file_name, types, information_header):
    prefix_of_lines = "\t\t\t"
    total_error_count = 0
    added_reports = {}
    with open( output_file_name, 'w') as file:
        file.write(object_list_header())
        file.write(row( '<hr>', prefix_of_lines=prefix_of_lines))
        file.write(row( information_header, prefix_of_lines=prefix_of_lines ))
        file.write(row( '<hr>', prefix_of_lines=prefix_of_lines ))
        #print("LOADING ERRORS START")
        reported_errors = sorted(errors, key=lambda error: error['osm_object_url'])
        #print("LOADING ERRORS END")
        for error_type_id in types:
            #print(error_type_id)
            error_count = 0
            for e in reported_errors:
                if e['error_id'] == error_type_id:
                    if error_count == 0:
                        file.write(row( '<a href="#' + error_type_id + '"><h2 id="' + error_type_id + '">' + error_type_id + '</h2></a>', prefix_of_lines=prefix_of_lines))
                    error_text = error_description(e, prefix_of_lines + "\t")
                    if error_text in added_reports:
                        print("duplicated error!")
                        print(error_text)
                        print(error_type_id)
                        print(output_file_name)
                        continue
                    added_reports[error_text] = "added!"
                    error_count += 1
                    total_error_count += 1
                    file.write(error_text)
            if error_count != 0:
                file.write(row( '<a href="https://overpass-turbo.eu/">overpass query</a> usable in JOSM that will load all objects where this specific eror is present:', prefix_of_lines=prefix_of_lines ))
                query = common.get_query_for_loading_errors_by_category_from_error_data(errors, printed_error_ids = [error_type_id], format = "josm")
                query_html = "<blockquote>" + common.escape_from_internal_python_string_to_html_ascii(query) + "</blockquote>"
                file.write(row(query_html, prefix_of_lines=prefix_of_lines))
                file.write(row( '<hr>', prefix_of_lines=prefix_of_lines ))
        file.write(html_file_suffix())
    return total_error_count
        
def contact_url():
    return "https://www.openstreetmap.org/message/new/Mateusz%20Konieczny"

def contact_html_prefix():
    return "<a href=\"" + contact_url() + "\">"

def contact_html_suffix():
    return "</a>"

def send_me_a_message_html():
    return contact_html_prefix() + "send me a message" + contact_html_suffix()

def feedback_header():
    return "Feedback? Ideas? Complaints? Suggestions? Request for report about other area? " + send_me_a_message_html() + "!"

def timestamp():
    return "This page was generated on " + str(datetime.date.today()) + ". Please, " + send_me_a_message_html() + " if you want it updated!" 

def feedback_request():
    returned = ""
    returned += feedback_header()
    returned += "<br />\n"
    returned += timestamp()
    returned += "<br />\n"
    return returned

def html_file_header():
    returned = ""
    returned += "<html>\n"
    returned += "\t<head>\n"
    returned += '\t\t<link rel="stylesheet" href="https://mapsaregreat.com/style.css" /> <!-- GPLv3 licensed -->\n'
    returned += "\t</head>\n"
    returned += "<body>\n"
    returned += "\t<div class=\"inner\">"
    return returned

def html_file_suffix():
    returned = ""
    returned += "<p class=\"small\">files stored at <a href=\"https://github.com/matkoniecz/OSM-wikipedia-tag-validator-reports/\">https://github.com/matkoniecz/OSM-wikipedia-tag-validator-reports/</a>\n</p>"
    returned += "\t\t</div>\n"
    returned += "\t</body>\n"
    returned +=  "</html>\n"
    return returned


def object_list_header():
    returned = ""
    returned += html_file_header()
    returned += feedback_request()
    returned += "<br />\n"
    returned += "<br />\n"
    return returned

def link_to_osm_object(url):
    return '<a href="' + url + '" target="_new">Affected OSM element that may be improved</a>'

def article_name_from_wikipedia_string(string):
    return string[string.find(":")+1:]

def language_code_from_wikipedia_string(string):
    return string[0:string.find(":")]

def format_wikipedia_link(string):
    if string == None:
        return "?"
    language_code = language_code_from_wikipedia_string(string)
    language_code = common.escape_from_internal_python_string_to_html_ascii(language_code)
    article_name = article_name_from_wikipedia_string(string)
    article_name = common.escape_from_internal_python_string_to_html_ascii(article_name)
    return '<a href="https://' + language_code + '.wikipedia.org/wiki/' + article_name + '" target="_new">' + language_code+":"+article_name + '</a>'

def row(text, prefix_of_lines):
    returned = ""
    returned += prefix_of_lines + "</br>\n"
    returned += prefix_of_lines + text + "\n"
    return returned

    returned = ""
    returned += prefix_of_lines + "<tr>\n"
    returned += prefix_of_lines + "\t<td>\n"
    returned += prefix_of_lines + "\t\t" + text + "\n"
    returned += prefix_of_lines + "\t</td>\n"
    returned += prefix_of_lines + "</tr>\n"
    return returned

def error_description(e, prefix_of_lines):
    returned = ""
    returned += row(common.htmlify(e['error_message']), prefix_of_lines=prefix_of_lines)
    returned += row(link_to_osm_object(e['osm_object_url']), prefix_of_lines=prefix_of_lines)
    if e['desired_wikipedia_target'] != None:
        returned += describe_proposed_relinking(e, prefix_of_lines)
    returned += row( '<hr>', prefix_of_lines=prefix_of_lines)
    return returned

def describe_proposed_relinking(e, prefix_of_lines):
    returned = ""
    current = format_wikipedia_link(e['current_wikipedia_target'])
    to = format_wikipedia_link(e['desired_wikipedia_target'])
    if to == current:
        to = "?"
    returned += row( current + " -> " + to, prefix_of_lines=prefix_of_lines)
    if to != "?":
        article_name = article_name_from_wikipedia_string(e['desired_wikipedia_target'])
        returned += row( common.escape_from_internal_python_string_to_html_ascii(article_name), prefix_of_lines=prefix_of_lines)
    return returned

def note_unused_errors(reported_errors):
    for e in reported_errors:
        if e['error_id'] in for_review():
            continue
        if e['error_id'] in obvious_fixes():
            continue
        if e['error_id'] in for_tests():
            continue
        print('"' + e['error_id'] + '" is not appearing in any generated webpage')

def for_review():
    return [
        'wikipedia tag in outdated form and there is mismatch between links',
        'wikipedia tag links to 404',
        'wikidata tag links to 404',
        'link to an unlinkable article',
        'wikipedia wikidata mismatch',
        'tag may be added based on wikidata',
        'tag may be added based on wikidata - teryt',
        'invalid old-style wikipedia tag',
        'malformed wikidata tag',
        'malformed wikipedia tag',
        'link to a list',
    ]

def obvious_fixes():
    return [
        'blacklisted connection with known replacement',
        'wikipedia tag unexpected language',
        'wikipedia tag from wikipedia tag in an outdated form',
        'wikipedia wikidata mismatch - follow wikipedia redirect',
        'wikipedia from wikidata tag',
        'wikipedia from wikidata tag, unexpected language',
        'wikidata from wikipedia tag',
        'wikipedia tag in an outdated form for removal',
        'wikipedia tag from wikipedia tag in an outdated form and wikidata',
        'wikipedia wikidata mismatch - follow wikidata redirect',
    ]

def for_tests():
    return [
        'should use a secondary wikipedia tag', # split in parts? reporting for humans seems reliable or for artworks in general such as memorial=statue / tourism=artwork
        'no longer existing object',
        'tag conflict with wikidata value',
        'tag conflict with wikidata value - testing',
        'wikipedia tag unexpected language, article missing',
        'tag conflict with wikidata value - boring',
        'tag may be added based on wikidata - website', # dubious copyright
    ]

if __name__ == "__main__":
    main()
