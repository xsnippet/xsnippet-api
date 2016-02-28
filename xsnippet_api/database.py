"""
    xsnippet_api.database
    ---------------------

    Provides a factory function that creates a database connection
    ready to be used by application instance.

    :copyright: (c) 2016 The XSnippet Team, see AUTHORS for details
    :license: MIT, see LICENSE for details
"""

import asyncio

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.son_manipulator import SONManipulator


def create_connection(conf, loop=None):
    """Create and return a database connection.

    :param conf: a settings to be used to create an application instance
    :type conf: :class:`dict`

    :param loop: an event loop to run in
    :type loop: :class:`asyncio.BaseEventLoop` or None

    :return: a database connection
    :rtype: :class:`motor.motor_asyncio.AsyncIOMotorDatabase`
    """

    # NOTE(malor): motor won't use the default event loop if None is passed.
    # Use a workaround here, until it's fixed in upstream.
    if loop is None:
        loop = asyncio.get_event_loop()

    mongo = AsyncIOMotorClient(conf['database']['connection'], io_loop=loop)

    # get_default_database returns a database from the connection string
    db = mongo.get_default_database()

    # By historical reasons snippet's ID is integer, but MongoDB's native
    # one is not. In order to fix that each time we insert records to
    # database we need to pass explicitly desired ID. This SON manipulator
    # is doing this implicitly for us on application level.
    db.add_son_manipulator(_AutoincrementId())

    return db


class _AutoincrementId(SONManipulator):

    def transform_incoming(self, son, collection):
        if son and '_id' not in son:
            son['_id'] = self._get_next_id(collection)
        return son

    def _get_next_id(self, collection):
        result = collection.database._autoincrement_ids.find_and_modify(
            query={'_id': collection.name},
            update={'$inc': {'next': 1}},
            upsert=True,
            new=True
        )
        return result['next']
