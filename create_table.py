import psycopg2
from config import config

def create_configurations_table():
    sql = '''
            CREATE TABLE configurations (
                id SERIAL PRIMARY KEY,
                connection INTEGER,
                name VARCHAR(255) NOT NULL,
                description VARCHAR(255),
                config json,
                type VARCHAR(50),
                infra_type VARCHAR(50),
                PORT_channel_id INTEGER,
                max_Frame_size INTEGER
        )
    '''
    try:
        params = config()
        conn = psycopg2.connect(**params)
        cur = conn.cursor()
        cur.execute(sql)
        conn.commit()
        cur.close()
        conn.close()

    except (Exception, psycopg2.DatabaseError) as error:
        print(error)

    finally:
        if conn is not None:
            conn.close()


if __name__ == '__main__':
    create_configurations_table()