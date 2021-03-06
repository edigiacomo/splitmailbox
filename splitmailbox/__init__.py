#!/usr/bin/env python

# splitmailbox.py - Simple tool to split your mailbox
#
# Copyright (C) 2015,2019  Emanuele Di Giacomo <emanuele@digiacomo.cc>
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 59 Temple
# Place, Suite 330, Boston, MA  02111-1307  USA
#
# Author: Emanuele Di Giacomo <emanuele@digiacomo.cc>

import os.path
import mailbox
import email.utils
from datetime import datetime
import logging

import pkg_resources


try:
    __version__ = pkg_resources.get_distribution('splitmailbox').version
except pkg_resources.DistributionNotFound:
    __version__ = 'devel'


logger = logging.getLogger("splitmail")


def splitbox(mailpath, mailcls, fmt, filtermsg=None, copy=True, dry_run=False):
    box = mailcls(mailpath)

    for k, m in box.iteritems():
        if filtermsg is None or not filtermsg(m):
            continue
        h = dict(m.items())
        t = email.utils.parsedate_tz(m.get('Date'))
        h['Date'] = datetime.utcfromtimestamp(email.utils.mktime_tz(t))
        f = fmt.format(**h)
        logger.info("Saving message %s (%s) in mailbox %s", k, h['Date'], f)
        if not dry_run:
            outbox = mailcls(f, create=True)
            outbox.lock()
            outbox.add(m)
            outbox.unlock()
            outbox.close()

        if not copy:
            logger.info("Removing message %s (%s)", k, h['Date'])
            if not dry_run:
                box.lock()
                box.discard(k)
                box.unlock()

    box.close()


def parse_datetime(s):
    return datetime.strptime(s, '%Y-%m-%d')


def create_filtermsg(untildate):
    def wrapper(m):
        if untildate is None:
            return True
        t = email.utils.parsedate_tz(m.get('Date'))
        d = datetime.utcfromtimestamp(email.utils.mktime_tz(t))
        return d < untildate
    return wrapper

def parse_mailformat(name):
    return {
        "mailbox": mailbox.mbox,
        "maildir": mailbox.Maildir,
    }[name]


def main():
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('--version', action='version',
                        version='%(prog)s ' + __version__)
    parser.add_argument('-o', '--output-dir', metavar='PATH', default=None,
                        help='output directory')
    parser.add_argument('-a', '--archive-name', metavar='NAME', default=None,
                        help='archive name')
    parser.add_argument('-p', '--prefix', metavar='NAME', default='',
                        help='prefix format')
    parser.add_argument('-s', '--suffix', metavar='NAME', default='_{Date:%Y}',
                        help='suffix format')
    parser.add_argument('-c', '--copy', action='store_true', default=False,
                        help='copy instead of move mail')
    parser.add_argument('-n', '--dry-run', action='store_true', default=False,
                        help='dry run')
    parser.add_argument('-D', '--date', type=parse_datetime, default=None,
                        help=('process mails older than this date only '
                              '(%%Y-%%m-%%d)'))
    parser.add_argument('--mailformat', help="mail format",
                        choices=["mailbox", "maildir"],
                        default="maildir",
                        type=parse_mailformat)
    parser.add_argument('mailpath', help="mailbox/maildir path")

    args = parser.parse_args()

    logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)

    if args.archive_name is None:
        args.archive_name = os.path.basename(args.mailpath)

    if args.output_dir is None:
        args.output_dir = os.path.dirname(args.mailpath)

    fmt = os.path.join(args.output_dir,
                       args.prefix + args.archive_name + args.suffix)
    splitbox(args.mailpath, args.mailformat, fmt,
             filtermsg=create_filtermsg(args.date),
             copy=args.copy, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
