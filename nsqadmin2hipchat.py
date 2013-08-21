#!/usr/bin/env python

import urllib
import json
import logging
import nsq
import argparse
import functools

def post_to_hipchat(txt, args, user):
    params = {
        'auth_token' : args.hipchat_auth_token,
        'from' : user or 'NSQ Admin',
        'color' : 'gray',
        'room_id' : args.hipchat_room_id,
        'message_format' : 'text',
        'message' : txt
    }
    url = "https://api.hipchat.com/v1/rooms/message"
    return urllib.urlopen(url + '?' + urllib.urlencode(params))

action_text_map = {
    'create_topic' : 'Created',
    'create_channel' : 'Created',
    'delete_topic' : 'Deleted',
    'delete_channel' : 'Deleted',
    'empty_channel' : 'Emptied',
    'pause_channel' : 'Paused',
    'unpause_channel' : 'Unpaused',
    'tombstone_topic_producer': 'Tombstoned Topic Producer',
}
def text_from_nsq_body(body):
    try:
        event = json.loads(body)
        topic_txt = 'topic %s' % event['topic']
        channel_txt = 'channel %s in ' % event['channel'] if event['channel'] else ''
        return action_text_map.get(event['action'], event['action']) + " " + channel_txt + topic_txt, event['user']
    except ValueError:
        logging.exception("Invalid json from nsq")


def process_message(message, args):
    msg_txt, user = text_from_nsq_body(message.body)
    if args.verbose:
        logging.warn(msg_txt)
    response = post_to_hipchat(msg_txt, args, user)
    if args.verbose:
        logging.warn(response.read())
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--hipchat-auth-token', required=True)
    parser.add_argument('--hipchat-room-id', required=True)
    parser.add_argument('--nsq-topic', required=True)
    parser.add_argument('--nsq-channel', default='nsqadmin2hipchat')
    parser.add_argument('-v', '--verbose', action='store_true')
    sources = parser.add_mutually_exclusive_group(required=True)
    sources.add_argument('--nsqd-tcp-address', action='append')
    sources.add_argument('--lookupd-http-address', action='append')
    args = parser.parse_args()
    kwargs = {
        'topic': args.nsq_topic,
        'channel': args.nsq_channel,
        'message_handler' : functools.partial(process_message, args=args)
    }
    if args.lookupd_http_address:
        addresses = [a if a.startswith("http") else "http://%s" % a for a in args.lookupd_http_address]
        kwargs['lookupd_http_addresses'] = addresses
    else:
        kwargs['nsqd_tcp_addresses'] = args.nsqd_tcp_address
    r = nsq.Reader(**kwargs)
    nsq.run()
