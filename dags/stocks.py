from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago
from datetime import timedelta


# Определяем DAG
with DAG(
    dag_id='wildberries_stocks',
    default_args={
        'owner': 'airflow',
        #'retries': 1,
        'retry_delay': timedelta(minutes=1),
    },
    schedule_interval='0 20 * * *',  # Каждый день в 23:00 МСК
    start_date=days_ago(1),  # DAG запускается с даты вчерашнего дня
    catchup=False,  # Не нагоняет пропущенные выполнения
    tags=['wildberries', 'stocks'],
) as dag:
    
    # Операция: запуск shell-скрипта
    run_script = BashOperator(
        task_id="run_wildberries_stocks",
        bash_command="/opt/airflow/projects/wildberries/wildberries_stock.py",  # Укажите полный путь к скрипту
        do_xcom_push=False,
    )

    run_script  # Запуск задачи
