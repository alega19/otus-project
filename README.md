# otus-project

This web application allow searching for communities (vk.com) with audience that you are interested in.


## Requirements:
* Python 3.6
* aiohttp 2.3.3
* psycopg2 2.7.3.2
* Django 1.11.7
* PostgreSQL 10.1

## Guide:
1. Execute schema.sql
2. Execute insert_empty_communities.sql
3. Get access_token (https://vk.com/dev/access_token) and insert it into "account" table (you'll need account on vk.com)
4. Start vkapi/main.py. This app collect information about the communities.
5. Start Django app in vksearch/
