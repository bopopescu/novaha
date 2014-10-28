# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import MetaData
from sqlalchemy import String
from sqlalchemy import Table

from nova.openstack.common.gettextutils import _
from nova.openstack.common import log as logging
from nova.openstack.common import timeutils

LOG = logging.getLogger(__name__)


def upgrade(migrate_engine):
    meta = MetaData()
    meta.bind = migrate_engine

    nPar_resource = Table('nPar_resource', meta,
        Column('id', Integer, primary_key=True, nullable=False),
        Column('created_at', DateTime, default=timeutils.utcnow),
        Column('updated_at', DateTime, onupdate=timeutils.utcnow),
        Column('deleted_at', DateTime),
        Column('ip_addr', String(length=255), nullable=False),
        Column('vcpus', Integer, nullable=True),
        Column('vcpus_used', Integer, nullable=True),
        Column('memory', Integer, nullable=True),
        Column('memory_used', Integer, nullable=True),
        Column('disk', Integer, nullable=True),
        Column('disk_used', Integer, nullable=True),
        Column('deleted', Integer, default=0, nullable=False),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )
    shadow_nPar_resource = Table('shadow_nPar_resource', meta,
        Column('id', Integer, primary_key=True, nullable=False),
        Column('created_at', DateTime),
        Column('updated_at', DateTime),
        Column('deleted_at', DateTime),
        Column('ip_addr', String(length=255), nullable=False),
        Column('vcpus', Integer, nullable=True),
        Column('vcpus_used', Integer, nullable=True),
        Column('memory', Integer, nullable=True),
        Column('memory_used', Integer, nullable=True),
        Column('disk', Integer, nullable=True),
        Column('disk_used', Integer, nullable=True),
        Column('deleted', String(length=36)),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    try:
        # Drop the compute_node_stats table and add a 'stats' column to
        # compute_nodes directly.  The data itself is transient and doesn't
        #  need to be copied over.
        table_names = ('nPar_resource', 'shadow_nPar_resource')
        for table_name in table_names:
            table = Table(table_name, meta, autoload=True)
            table.create()

    except Exception:
        LOG.info(repr(nPar_resource))
        LOG.exception(_('Exception while creating table.'))
        raise


def downgrade(migrate_engine):
    meta = MetaData()
    meta.bind = migrate_engine

    table_name = ('nPar_resource')
    table = Table(table_name, meta, autoload=True)
    table.drop()
    table_name = ('shadow_nPar_resource')
    table = Table(table_name, meta, autoload=True)
    table.drop()
