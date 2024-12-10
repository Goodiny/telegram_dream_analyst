import logging.config

import psycopg2

from db.execute_query import execute_query_pg

logger = logging.getLogger(__name__)


# Инициализация базы данных
def database_initialize():
    """
    Инициализация базы данных
    """
    try:
        # execute_query('''
        #     CREATE DATABASE IF NOT EXISTS sleep_bot_database
        #         WITH
        #         OWNER = postgres
        #         ENCODING = 'UTF8'
        #         LC_COLLATE = 'C'
        #         LC_CTYPE = 'C'
        #         TABLESPACE = pg_default
        #         CONNECTION LIMIT = -1
        #         IS_TEMPLATE = False;
        # ''')

        # Таблица users
        execute_query_pg('''
            CREATE TABLE IF NOT EXISTS public.users(
                id bigint NOT NULL,
                username text COLLATE pg_catalog."default",
                first_name text COLLATE pg_catalog."default",
                last_name text COLLATE pg_catalog."default",
                phone_number text COLLATE pg_catalog."default",
                city_name text COLLATE pg_catalog."default",
                sleep_goal real DEFAULT 8.0,
                wake_time text COLLATE pg_catalog."default",
                has_provided_location integer DEFAULT 0,
                CONSTRAINT users_pkey PRIMARY KEY (id)
            )
            
            TABLESPACE pg_default;
            
            ALTER TABLE IF EXISTS public.users
                OWNER to postgres;
        ''')

        execute_query_pg('''
            CREATE SEQUENCE IF NOT EXISTS public.sleep_records_id_seq
                INCREMENT 1
                START 1
                MINVALUE 1
                MAXVALUE 9223372036854775807
                CACHE 1;

            ALTER SEQUENCE public.sleep_records_id_seq
                OWNER TO postgres;
        ''')

        # Таблица sleep_records
        execute_query_pg('''      
            CREATE TABLE IF NOT EXISTS public.sleep_records(
                id integer NOT NULL DEFAULT nextval('sleep_records_id_seq'::regclass),
                user_id bigint NOT NULL,
                sleep_time text COLLATE pg_catalog."default" NOT NULL,
                wake_time text COLLATE pg_catalog."default",
                sleep_quality integer,
                mood integer,
                CONSTRAINT sleep_records_pkey PRIMARY KEY (id),
                CONSTRAINT sleep_records_user_id_fkey FOREIGN KEY (user_id)
                    REFERENCES public.users (id) MATCH SIMPLE
                    ON UPDATE NO ACTION
                    ON DELETE CASCADE
            );
            
            ALTER TABLE IF EXISTS public.sleep_records
                OWNER to postgres;
                
            ALTER SEQUENCE public.sleep_records_id_seq
                OWNED BY public.sleep_records.id;
        ''')


        # Таблица reminders
        execute_query_pg('''
            CREATE TABLE IF NOT EXISTS public.reminders(
                user_id bigint NOT NULL,
                reminder_time text COLLATE pg_catalog."default" NOT NULL,
                CONSTRAINT reminders_pkey PRIMARY KEY (user_id),
                CONSTRAINT reminders_user_id_fkey FOREIGN KEY (user_id)
                    REFERENCES public.users (id) MATCH SIMPLE
                    ON UPDATE NO ACTION
                    ON DELETE CASCADE
            );
            
            ALTER TABLE IF EXISTS public.reminders
                OWNER to postgres;
        ''')
        logger.info("База данных проинициализирована")
    except psycopg2.DatabaseError as e:
        logger.error(f"Ошибка при создании баззы данных: {e}")   



def create_triggers_db():
    """
    Создание триггеров
    """
    try:
        execute_query_pg('''
            CREATE TRIGGER IF NOT EXISTS update_existing_sleep_time
            BEFORE INSERT ON public.sleep_records
            FOR EACH ROW
            WHEN (SELECT COUNT(*) FROM public.sleep_records WHERE user_id = NEW.user_id AND wake_time IS NULL) > 0
            BEGIN
                UPDATE public.sleep_records
                SET sleep_time = NEW.sleep_time
                WHERE user_id = NEW.user_id AND wake_time IS NULL;
                SELECT RAISE(IGNORE);
            END;
        ''')

        execute_query_pg('''
            CREATE TRIGGER after_sleep_records_insert_new_user 
            AFTER INSERT ON public.sleep_records
            FOR EACH ROW
            WHEN (SELECT COUNT(id) FROM public.users WHERE id=NEW.user_id) = 0
            BEGIN
            INSERT INTO public.users (id)
            VALUES (NEW.user_id);
            END
        ''')
        logger.info("Триггеры созданы")
    except psycopg2.DatabaseError as e:
        logger.error(f"Ошибка при создании триггеров: {e}")


if __name__ == '__main__':
    pass
