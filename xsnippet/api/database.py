"""
    xsnippet.api.database
    ---------------------

    Provides a factory function that creates a database connection
    ready to be used by application instance.

    :copyright: (c) 2016 The XSnippet Team, see AUTHORS for details
    :license: MIT, see LICENSE for details
"""

import asyncio
import copy

from motor.motor_asyncio import AsyncIOMotorClient
import pymongo


def create_connection(conf):
    """Create and return a database connection.

    :param conf: a settings to be used to create an application instance
    :type conf: :class:`dict`

    :return: a database connection
    :rtype: :class:`motor.motor_asyncio.AsyncIOMotorDatabase`
    """
    mongo = AsyncIOMotorClient(conf['database']['connection'])

    # get_default_database returns a database from the connection string
    db = mongo.get_default_database()

    # ID incrementer is used to auto increment record ID if nothing
    # is explicitly passed.
    #
    # ID processor is used for auto converting domain IDs to and from
    # database ones (i.e. 'id' -> '_id' and vice versa).
    #
    # SON manipulators are applied in reversed order.
    db.add_son_manipulator(_IdIncrementer())
    db.add_son_manipulator(_IdProcessor())

    return db


async def setup(app):
    """Perform setup actions on application startup.

    This function is expected to inject the `db` key to the application
    instance, that must point to a properly initialized DB connection. Some
    operations (e.g. ensuring of indexes) may be performed asynchronously.
    """

    db = create_connection(app['conf'])
    app['db'] = db

    # ensure necessary indexes exist. background=True allows operations
    # read/write operations on collections while indexes are being built
    futures = [
        db.snippets.create_index('title',
                                 name='title_idx',
                                 # create a partial index to skip null values -
                                 # this is supposed to make the index smaller,
                                 # so that there is a higher chance it's kept
                                 # in the main memory
                                 partialFilterExpression={
                                    'title': {'$type': 'string'}
                                 },
                                 background=True),
        db.snippets.create_index('tags',
                                 name='tags_idx',
                                 background=True),
        db.snippets.create_index([('created_at', pymongo.DESCENDING)],
                                 name='created_idx',
                                 background=True),
        db.snippets.create_index([('updated_at', pymongo.DESCENDING)],
                                 name='updated_idx',
                                 background=True)
    ]
    return await asyncio.gather(*futures)


class _IdProcessor(pymongo.son_manipulator.SONManipulator):
    """SON manipulator that converts ID column to and from DB notation.

    Encode procedure: rename ``id`` into ``_id`` if any.
    Decode procedure: rename ``_id`` into ``id`` if any.
    """

    def transform_incoming(self, son, collection):
        # we want to make a shallow copy in order to prevent modification
        # of passed documents (no implicit injection of '_id')
        son = copy.copy(son)

        if son and 'id' in son:
            son['_id'] = son.pop('id')
        return son

    def transform_outgoing(self, son, collection):
        if son and '_id' in son:
            son['id'] = son.pop('_id')
        return son


class _IdIncrementer(pymongo.son_manipulator.SONManipulator):
    """SON manipulator that implements autoincrement behaviour for ID.

    If no ``_id`` is specified in SON, then a new one is picked using
    autoincrement approach. That last used ID is stored in a special
    MongoDB collection that's called ``_autoincrement_ids``.
    """

    def transform_incoming(self, son, collection):
        # we want to make a shallow copy in order to prevent modification
        # of passed documents (no implicit injection of '_id')
        son = copy.copy(son)

        if son and '_id' not in son:
            son['_id'] = self._get_next_id(collection)
        return son

    def _get_next_id(self, collection):
        result = collection.database['_autoincrement_ids'].find_and_modify(
            query={'_id': collection.name},
            update={'$inc': {'next': 1}},
            upsert=True,
            new=True)
        return result['next']
