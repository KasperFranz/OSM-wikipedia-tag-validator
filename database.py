def create_table_if_needed(cursor):
    if "osm_data" in existing_tables(cursor):
        print("osm_data table exists already, delete file with database to recreate")
    else:
        # validator_complaint needs to hold
        # - not checked
        # - checked, no problem found
        # - error data
        #
        # right now for "checked, no error" I plan to use empty string but I am not too happy
        cursor.execute('''CREATE TABLE osm_data
                    (type text, id number, lat float, lon float, tags text, area_identifier text, download_timestamp integer, validator_complaint text, error_id text)''')

        # magnificent speedup
        cursor.execute("""CREATE INDEX idx_osm_data_area_identifier ON osm_data (area_identifier);""")
        cursor.execute("""CREATE INDEX idx_osm_data_id_type ON osm_data (id, type);""")
        cursor.execute("""CREATE INDEX idx_error_id ON osm_data (error_id);""")
    if "osm_data_update_log" in existing_tables(cursor):
        print("osm_data_update_log table exists already, delete file with database to recreate")
    else:
        # register when data was downloaded so update can be done without downloading
        # and processing the entire dataset
        #
        # instead just entries that were changed since then
        # - and carry *(wikipedia|wikidata)* tags
        # - that previously had problem reported about them
        # should be downloaded
        cursor.execute('''CREATE TABLE osm_data_update_log
                    (area_identifier text, filename text, download_type text, download_timestamp integer)''')
    if "osm_bot_edit_log" in existing_tables(cursor):
        print("osm_bot_edit_log table exists already")
    else:
        cursor.execute('''CREATE TABLE osm_bot_edit_log
                    (area_identifier text, type text, bot_edit_timestamp integer)''')

def existing_tables(cursor):
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    table_listing = cursor.fetchall()
    returned = []
    for entry in table_listing:
        returned.append(entry[0])
    return returned

def get_data_download_timestamp(cursor, internal_region_name):
    cursor.execute("SELECT download_timestamp FROM osm_data_update_log WHERE area_identifier = :area_identifier ORDER BY download_timestamp DESC LIMIT 1", {"area_identifier": internal_region_name})
    returned = cursor.fetchall()
    if len(returned) == 0:
        return 0
    else:
        return returned[0][0]

def get_bot_edit_timestamp(cursor, internal_region_name, bot_edit_type):
    cursor.execute("SELECT download_timestamp FROM osm_data_update_log WHERE area_identifier = :area_identifier AND type = :type ORDER BY download_timestamp DESC LIMIT 1", {"area_identifier": internal_region_name, "type": bot_edit_type, })
    returned = cursor.fetchall()
    if len(returned) == 0:
        return 0
    else:
        return returned[0][0]

def record_bot_edit_timestamp(cursor, internal_region_name, bot_edit_type, timestamp):
    cursor.execute("INSERT INTO osm_bot_edit_log VALUES (:area_identifier, :type, :bot_edit_timestamp)", {"area_identifier": internal_region_name, "type": bot_edit_type, "bot_edit_timestamp": timestamp})
