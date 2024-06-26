"""
Updated using multiprocessing to wait for database to unlock, saved results in out6.txt

"""

# Import from Python Standard Library


import datetime
import logging
import multiprocessing
import os
import platform
import sqlite3
import sys
import time

# Set up basic configuration for logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


# Declare program constants (typically constants are named with ALL_CAPS)

TASK_DURATION_SECONDS = 3 # TODO: increase this to 3 and see what happens
DIVIDER = "=" * 70  # A string divider for cleaner output formatting
DB_NAME = "shared.db"
DB_LOCK = multiprocessing.Lock()

# define a multi-line (doc) string to communicate with the user
SUCCESS_MESSAGE ="""
SUCCESS: All processes successfully completed!

Now - increase the task duration (representing 
      the time the task has the database 
      tied up during an insert statement).
How well do multiple, concurrent processes share a database 
    when each task takes more time? 
How can multiple processes share a resource
    without interfering with each other?
"""

# define another multi-line f-string (formatted string) to
# display useful information at the start of the program
# f-strings make it easy to insert variables into strings
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
        # logging.debug(f"  CREATED connection to {DB_NAME}.")

        # create a connection cursor to execute statements
        cur = conn.cursor()
        # logging.debug("  CREATED cursor.")

        # create valid SQL statement
        sql_string = "  CREATE TABLE pets (id INTEGER PRIMARY KEY, name TEXT, breed TEXT)"
        # call cursor.execute() to run the SQL statement
        cur.execute(sql_string)
        # logging.debug("  CREATED table pets.")

        # commit the transaction
        conn.commit()
        logging.info("Table 'pets' created successfully.")

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
        cur.execute("DROP TABLE IF EXISTS pets")
        conn.commit()
        logging.info("Table 'pets' dropped successfully.")
    except sqlite3.Error as error:
        logging.error(f"Error while dropping the 'pets' table: {error}")
    finally:
        conn.close()

def insert_pet(process, name, breed):
    """Insert a pet into pets table."""
    logging.info(f"  Called insert_pet() with process={process}, name={name}, breed={breed}.")
    
    try:
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        sql = f"INSERT INTO pets (name, breed) VALUES ('{name}', '{breed}');"
        retries = 3
        while retries > 0:
            try:
                with DB_LOCK:
                    cur.execute(sql)
                    logging.debug(f"{process} getting ready to insert {name} the {breed}.")
                    time.sleep(TASK_DURATION_SECONDS)
                    conn.commit()
                    logging.debug(f"{process} ADDED {name} the {breed}.")
                    break
            except sqlite3.Error as error:
                if "database is locked" in str(error):
                    logging.warning(f"Database is locked, retrying... ({retries} retries left)")
                    retries -= 1
                    time.sleep(0.1) #wait while retrying
                else:
                    logging.error(f"ERROR while {process} inserting pet {name}: {error}")
                    break
    finally:
        conn.close()

def process_one():
    logging.info("Called process_one().")
    insert_pet("P1", "Ace", "Dog")
    insert_pet("P1", "Buddy", "Dog")

def process_two():
    logging.info("Called process_two().")
    insert_pet("P2", "Cooper", "Rabbit")
    insert_pet("P2", "Dingo", "Dog")

def process_three():
    logging.info("Called process_three().")
    insert_pet("P3", "Emma", "Rabbit")
    insert_pet("P3", "Felix", "Cat")


# ---------------------------------------------------------------------------
# If this is the script we are running, then call some functions and execute code!
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    # log some introductory information
    logging.info(INFO_MESSAGE)

    # start over with a clean database
    recreate_database()

    # define several processes
    # to represent several users
    # accessing the same resource
    p1 = multiprocessing.Process(target=process_one)
    p2 = multiprocessing.Process(target=process_two)
    p3 = multiprocessing.Process(target=process_three)
    
    # start each process
    p1.start()
    p2.start()
    p3.start()
       
    # wait for a processes to finish and rejoin the flow of execution
    p1.join()
    p2.join()
    p3.join()
    
    # if the task duration is 0, then show the success message
    if TASK_DURATION_SECONDS == 0:
        logging.info(SUCCESS_MESSAGE)
   
