import csv
import logging
import multiprocessing
import datetime
import os
import platform
import sqlite3
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="out9.txt"  # Specify the filename here
)

# Define program constants (typically constants are named with ALL_CAPS)
TASK_DURATION_SECONDS = 1  # TODO: increase this to 3 and see what happens
DIVIDER = "=" * 70  # A string divider for cleaner output formatting
DB_NAME = "shared.db"
DB_LOCK = multiprocessing.Lock()

# Define multi-line (doc) strings to communicate with the user
SUCCESS_MESSAGE = """
SUCCESS: All processes successfully completed!

Now - increase the task duration (representing 
      the time the task has the database 
      tied up during an insert statement).
How well do multiple, concurrent processes share a database 
    when each task takes more time? 
How can multiple processes share a resource
    without interfering with each other?
"""

# Define multi-line formatted string to display useful information at the start of the program
INFO_MESSAGE = f"""
{DIVIDER}
STARTING UP.............................
  Date and Time:    {datetime.date.today()} at {datetime.datetime.now().strftime("%I:%M %p")}
  Operating System: {os.name} {platform.system()} {platform.release()}
  Python Version:   {platform.python_version()}
  Path to Interpreter:  {sys.executable}
{DIVIDER}
"""

# Define program functions (bits of reusable code)
def recreate_database():
    """Drop and recreate the database."""
    logging.info("Called recreate_database().")
    drop_table()
    create_table()

def create_table():
    """
    Create a table in the database. 
    This requires a connection to the database.
    Important: Working with databases can FAIL even if our code is correct.
    So:
      TRY some statements
      EXCEPT if there is an error, we do something else
      FINALLY tidy up and close the connection - regardless of what happened
    """
    logging.info("Called create_table().")
    try:
        # create a connection to the database
        conn = sqlite3.connect(DB_NAME)

        # create a connection cursor to execute statements
        cur = conn.cursor()

        # create valid SQL statement
        sql_string = "CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY, first_name TEXT, last_name TEXT, city TEXT, country TEXT)"
        
        # call cursor.execute() to run the SQL statement
        cur.execute(sql_string)

        # commit the transaction
        conn.commit()
        logging.info("Table 'customers' created successfully.")

    except Exception as e:
        # if there is an error, log the error message
        logging.error(e)

    finally:
        conn.close()

def drop_table():
    """Drop the table if it exists."""
    logging.info("Called drop_table().")
    
    try:
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("DROP TABLE IF EXISTS customers")
        conn.commit()
        logging.info("Table 'customers' dropped successfully.")
    except sqlite3.Error as error:
        logging.error(f"Error while dropping the 'customers' table: {error}")
    finally:
        conn.close()

def insert_customer(process, first_name, last_name, city, country):
    """Insert a customer into the customers table."""
    logging.info(f"  Called insert_customer() with process={process}, first_name={first_name}, last_name={last_name}, city={city}, country={country}.")
    
    try:
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        sql = f"INSERT INTO customers (first_name, last_name, city, country) VALUES ('{first_name}', '{last_name}', '{city}', '{country}')"
        retries = 3
        while retries > 0:
            try:
                with DB_LOCK:
                    cur.execute(sql)
                    logging.debug(f"{process} getting ready to insert {first_name} {last_name} from {city}, {country}.")
                    time.sleep(TASK_DURATION_SECONDS)
                    conn.commit()
                    logging.debug(f"{process} ADDED {first_name} {last_name} from {city}, {country}.")
                    break
            except sqlite3.Error as error:
                if "database is locked" in str(error):
                    logging.warning(f"Database is locked, retrying... ({retries} retries left)")
                    retries -= 1
                    time.sleep(0.1) #wait while retrying
                else:
                    logging.error(f"ERROR while {process} inserting customer {first_name} {last_name} from {city}, {country}: {error}")
                    break
    finally:
        conn.close()

def stream_data_from_csv(file_path):
    with open(file_path, 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            yield row

def process_csv_data():
    logging.info("Called process_csv_data().")
    file_path = "customers-100.csv"
    count = 0
    for idx, data in enumerate(stream_data_from_csv(file_path), start=1):
        if count >= 12:
            break
        insert_customer(f"CSV_{idx}", data['First Name'], data['Last Name'], data['City'], data['Country'])
        count += 1

if __name__ == "__main__":
    # log some introductory information
    logging.info(INFO_MESSAGE)

    # start over with a clean database
    recreate_database()

    # define a process to insert data from CSV
    p_csv = multiprocessing.Process(target=process_csv_data)
    
    # start the CSV process
    p_csv.start()

    # wait for the CSV process to finish and rejoin the flow of execution
    p_csv.join()

    # if the task duration is 0, then show the success message
    if TASK_DURATION_SECONDS == 0:
        logging.info(SUCCESS_MESSAGE)
