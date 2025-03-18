#!/usr/bin/env python
# coding: utf-8

# In[30]:


import requests
import pandas as pd
from datetime import datetime, timedelta
from clickhouse_driver import Client
import clickhouse_connect
from clickhouse_driver.errors import ServerException
import os
from dotenv import load_dotenv, dotenv_values


# In[27]:


print(f'начало работы скрипта, {datetime.utcnow() + timedelta(hours = 7)}')


# In[13]:


API_URL_TEMPLATE = "https://card.wb.ru/cards/v2/detail?appType=1&curr=rub&dest=-1257786&spp=99&nm="

# Список товаров
nmld = [
    293363765, 293378862, 295739458, 263038976, 287293767,
    267672429, 265116995, 268759087, 284439349, 274048350
]

# Список для хранения данных
stock_data = []

for product_id in nmld:
    url = API_URL_TEMPLATE + str(product_id)
    response = requests.get(url)
    
    # Достаём список товаров
    products = response.json().get('data', {}).get('products', [])

    if products:
        # Достаём список размеров товара
        sizes = products[0].get('sizes', [])

        total_stock = 0
        
        for size in sizes:
            stocks = size.get('stocks', [])
                
        for stock in stocks:
            qty = stock.get('qty', 0)
                    
            total_stock += qty

        stock_data.append({'nmld': product_id, 'stock': total_stock})
    else:
        stock_data.append({'nmld': product_id, 'stock': 0})

# Создаём DataFrame
df = pd.DataFrame(stock_data)

df


# In[14]:


start = datetime.utcnow()


# In[15]:


start


# In[16]:


start + timedelta(hours = 7)


# In[17]:


time = (start + timedelta(hours = 7))


# In[18]:


df['date'] = time


# In[19]:


df1 = df[['date', 'nmld', 'stock']]


# In[20]:


stock = df1.rename(columns={'stock' : 'orders'})


# In[21]:


stock


# In[22]:


stock['date'] = pd.to_datetime(stock['date']).dt.date 


# In[23]:


stock['orders'] = stock['orders'].astype('int32')


# In[24]:


stock


# In[50]:


print(stock.dtypes)


# # Подключение к БД

# In[31]:


load_dotenv() 


# In[32]:


host = os.getenv('host')
port = os.getenv('port')
database = os.getenv('database')
user = os.getenv('user')
password = os.getenv('password')


# In[33]:


client = Client(host=host, port=port, user=user, password=password, database=database, settings={'use_numpy': True,
                                                                                                'allow_experimental_lightweight_delete': True})


# In[34]:


table = 'stock'


# In[35]:


table_exists = bool(client.execute(f"SELECT name FROM system.tables WHERE name = '{table}'"))


# In[36]:


table_exists


# # Создание таблицы

# In[37]:


client.execute('''
CREATE TABLE IF NOT EXISTS default.stock (
    date Date,
    nmld Int64,
    orders Int32
) ENGINE = MergeTree()
ORDER BY date;
''')


# # Удаление повторяющихся строк

# In[38]:


client.execute(f"""
delete from stock where date = '{stock['date'].min().strftime('%Y-%m-%d')}'
""")


# # Залив данных в БД

# In[39]:


client.insert_dataframe(f'INSERT INTO {database}.{table} VALUES', stock)


# In[40]:


print(f'данные выгружены в БД, {datetime.utcnow() + timedelta(hours = 7)}')


# In[ ]:




