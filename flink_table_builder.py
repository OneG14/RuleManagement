import argparse
import mysql.connector
import traceback
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql.expression import text


def getConnection():
    try:
        # Update with your actual Trino connection string
        engine = create_engine('trino://admin@k8s-trinowri-trinoser-7d4699a13a-cea823d019e38cd3.elb.us-east-1.amazonaws.com:8080/v1/statement')
        connection = engine.connect()
    except SQLAlchemyError as e:
        connection = None
        print("An error occurred:", e)
    return connection


def closeConnection(conn):
    try:
        conn.close()
    except Exception as e:
        print("closeConnection: " + str(e))
    return


def desc_table(table):
    result = []
    status = -1
    try:
        conn = getConnection()
        if conn is not None:
            sql = f'DESC {table}'
            res = conn.execute(text(sql)).fetchall()
            status = 0
        else:
            status = -2
            raise Exception("DESC TABLE : db.checkConnection Failed")
    except Exception as e:
        result = str(e)
        print(result)
        print(traceback.format_exc())
        res = []
    finally:
        if conn:
            closeConnection(conn)
    return status, res


def format_as_sql_structure(data):
    nested_structures = {}
    for key in data:
        parts = key.split('.')
        current = nested_structures
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = data[key]

    def build_sql_structure(nested, level=0):
        indent = '    ' * level
        entries = []
        for key, value in sorted(nested.items()):
            if isinstance(value, dict):
                row_content = build_sql_structure(value, level + 1)
                entry = f"`{key}` row(\n{row_content}\n{indent})"
            elif isinstance(value, list):
                entry = f"`{key}` array<{value[0]}>"
            else:
                entry = f"`{key}` {value}"
            entries.append(indent + entry)
        return ',\n'.join(entries)

    return build_sql_structure(nested_structures)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Describe a table and generate its SQL structure.")
    parser.add_argument("table", type=str, help="The table name to describe (e.g., 'iceberg.bluevents.genie').")
    args = parser.parse_args()

    table_name = args.table

    # Call desc_table with the provided table name
    data = desc_table(table_name)

    if data[0] == -1:
        print("Failed to describe the table.")
    else:
        field_type_dict = {}
        for field in data[1]:
            field_name = field[0]
            data_type = field[1]

            # Apply transformation rules
            if data_type == 'array(varchar)':
                data_type = 'array<varchar>'
            elif data_type == 'timestamp(6)':
                data_type = 'timestamp'
            elif field_name == 'event.created':
                data_type = 'varchar'

            field_type_dict[field_name] = data_type

        # Generate the SQL structure
        sql_structure = format_as_sql_structure(field_type_dict)
        print(sql_structure)

## TO RUN THIS CODE 
# -->  /opt/blusapphire/virtenv/django/bin/python flink_temp_table_builder.py iceberg.bluevents.genie
