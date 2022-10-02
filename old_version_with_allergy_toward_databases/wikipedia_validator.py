# coding=utf-8

import argparse
import wikimedia_connection.wikimedia_connection as wikimedia_connection
from osm_iterator.osm_iterator import Data
import osm_handling_config.global_config as osm_handling_config
from wikibrain import wikimedia_link_issue_reporter
from wikibrain import wikipedia_knowledge

def get_problem_for_given_element_and_record_stats(element, forced_refresh, arguments):
    # TODO replace arguments.expected_language_code where applicable
    user_provided_expected_language_codes = [arguments.expected_language_code]
    if arguments.flush_cache:
        forced_refresh = True
    helper_object = wikimedia_link_issue_reporter.WikimediaLinkIssueDetector(
        forced_refresh, arguments.expected_language_code, get_expected_language_codes(user_provided_expected_language_codes), arguments.additional_debug,
        arguments.allow_requesting_edits_outside_osm, arguments.allow_false_positives)
    problems = helper_object.get_problem_for_given_element(element)
    if problems != None:
        return problems

def get_expected_language_codes(user_provided_expected_language_codes):
    returned = user_provided_expected_language_codes
    return returned + wikipedia_knowledge.WikipediaKnowledge.all_wikipedia_language_codes_order_by_importance()

def output_element(element, error_report, output_filepath):
    error_report.bind_to_element(element)
    link = element.get_tag_value("wikipedia")
    language_code = None
    article_name = None
    if link != None:
        language_code = wikimedia_connection.get_language_code_from_link(link)
        article_name = wikimedia_connection.get_article_name_from_link(link)
    position = element.get_coords()

    if position == None or position.lat == None or position.lon == None:
        error_report.debug_log = "Location data missing"

    error_report.yaml_output(output_filepath)

def validate_wikipedia_link_on_element_and_print_problems(element):
    arguments = args # called by OSM iterator so inelgible for more arguments to be provided for function
    link = element.get_tag_value("wikipedia") # TODO: apply this only in Germany
    if link!=None and "#" in link:
        return
    problem = get_problem_for_given_element_and_record_stats(element, False, arguments)
    if (problem != None):
        output_element(element, problem, arguments.output_filepath)

def validate_wikipedia_link_on_element_and_print_problems_refresh_cache_for_reported(element):
    arguments = args # called by OSM iterator so inelgible for more arguments to be provided for function
    if(get_problem_for_given_element_and_record_stats(element, False, arguments) != None):
        get_problem_for_given_element_and_record_stats(element, True, arguments)
    validate_wikipedia_link_on_element_and_print_problems(element)


def parsed_args():
    parser = argparse.ArgumentParser(description='Validation of wikipedia tag in osm data.')
    parser.add_argument('-filepath', '-f',
                        dest='filepath',
                        type=str,
                        help='location of .osm file (short form of parameter: -f), mandatory parameter',
                        required=True)
    parser.add_argument('-output_filepath', '-of',
                        dest='output_filepath',
                        type=str,
                        help='location of .osm file (short form of parameter: -of), mandatory parameter',
                        required=True)
    parser.add_argument('-expected_language_code', '-l',
                        dest='expected_language_code',
                        type=str,
                        help='expected language code (short form of parameter: -l)')
    parser.add_argument('-flush_cache',
                        dest='flush_cache',
                        help='adding this parameter will trigger flushing cache',
                        action='store_true')
    parser.add_argument('-flush_cache_for_reported_situations',
                        dest='flush_cache_for_reported_situations',
                        help='adding this parameter will trigger flushing cache only for reported situations \
                        (redownloads wikipedia data for cases where errors are reported, \
                        so removes false positives where wikipedia is already fixed)',
                        action='store_true')
    parser.add_argument('-allow_requesting_edits_outside_osm',
                        dest='allow_requesting_edits_outside_osm',
                        help='enables reporting of problems that may require editing wikipedia or wikidata',
                        action='store_true')
    parser.add_argument('-additional_debug',
                        dest='additional_debug',
                        help='additional debug - shows when wikidata types are no recognized, list locations allowed to have a foreign language label',
                        action='store_true')
    parser.add_argument('-allow_false_positives',
                        dest='allow_false_positives',
                        help='enables validator rules that may report false positives',
                        action='store_true')
    return parser.parse_args()


def main(arguments, osm_file_filepath, flush_cache_for_reported_situations):
    wikimedia_connection.set_cache_location(osm_handling_config.get_wikimedia_connection_cache_location())
    osm = Data(osm_file_filepath)
    if flush_cache_for_reported_situations:
        osm.iterate_over_data(validate_wikipedia_link_on_element_and_print_problems_refresh_cache_for_reported)
    else:
        osm.iterate_over_data(validate_wikipedia_link_on_element_and_print_problems)

global args #TODO remove global

if __name__ == "__main__":
    global args #TODO remove global
    args = parsed_args()
    arguments = args
    main(arguments, arguments.filepath, arguments.flush_cache_for_reported_situations)

# TODO - search for IDEA note
