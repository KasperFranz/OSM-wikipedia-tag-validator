import argparse
import yaml
import os.path
import generate_shared
import html

def print_html_header():
    print("<html>")
    print("<body>")
    print("<table>")

def link_to_osm_object(url):
    return '<a href="' + url + '" target="_new">OSM element with broken tag that should be fixed</a>'

def article_name_from_wikipedia_string(string):
    return string[string.find(":")+1:]

def language_code_from_wikipedia_string(string):
    return string[0:string.find(":")]

def escape_from_internal_python_string_to_html_ascii(string):
    return str(string).encode('ascii', 'xmlcharrefreplace').decode()

def format_wikipedia_link(string):
    if string == None:
        return "?"
    language_code = language_code_from_wikipedia_string(string)
    language_code = escape_from_internal_python_string_to_html_ascii(language_code)
    article_name = article_name_from_wikipedia_string(string)
    article_name = escape_from_internal_python_string_to_html_ascii(article_name)
    return '<a href="https://' + language_code + '.wikipedia.org/wiki/' + article_name + '" target="_new">' + language_code+":"+article_name + '</a>'

def print_table_row(text):
    print("<tr>")
    print("<td>")
    print(text)
    print("</td>")
    print("</tr>")

def parsed_args():
    parser = argparse.ArgumentParser(description='Production of webpage about validation of wikipedia tag in osm data.')
    parser.add_argument('-file', '-f', dest='file', type=str, help='name of yaml file produced by validator')
    args = parser.parse_args()
    if not (args.file):
        parser.error('Provide yaml file generated by wikipedia validator')
    return args

def htmlify(string):
    escaped = html.escape(string)
    escaped_ascii = escape_from_internal_python_string_to_html_ascii(escaped)
    return escaped_ascii.replace("\n", "<br />")

def main():
    args = parsed_args()
    print_html_header()
    filepath = generate_shared.get_write_location()+"/"+args.file
    if not os.path.isfile(filepath):
        print(filepath + " is not a file, provide an existing file")
        return
    reported_errors = generate_shared.load_data(filepath)
    types = [
        'wikipedia tag links to 404',
        'link to disambig',
        'wikipedia wikidata mismatch',
        'should use wikipedia:subject',
        'wikipedia tag unexpected language',
        'wikipedia wikidata mismatch - follow redirect',
    ]
    for error_type_id in types:
        error_count = 0
        for e in reported_errors:
            if e['error_id'] == error_type_id:
                error_count += 1
                print_table_row(htmlify(e['error_message']))
                print_table_row(link_to_osm_object(e['osm_object_url']))
                current = format_wikipedia_link(e['current_wikipedia_target'])
                to = format_wikipedia_link(e['desired_wikipedia_target'])
                if to == current:
                    to = "?"
                print_table_row( current + " -> " + to)
                if to != "?":
                    print_table_row( escape_from_internal_python_string_to_html_ascii(article_name_from_wikipedia_string(e['desired_wikipedia_target'])))
                print_table_row( '-------' )
        if error_count != 0:
            print_table_row( 'overpass query usable in JOSM that will load all objects with this error type:' )
            query = generate_shared.get_query(filename = args.file, printed_error_ids = [error_type_id], format = "josm")
            print_table_row(escape_from_internal_python_string_to_html_ascii(query))
            print_table_row( '==========' )

    print("</table>")
    print("</body>")
    print("</html>")

main()
