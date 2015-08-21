#!/usr/bin/env python

import urllib2
import json
import logging
import nsq
import argparse
import functools


def post_to_slack(txt, args, user):
    params = {
        'username' : user or 'NSQ Admin',
        'channel' : args.slack_channel_id,
        'message' : txt, #TODO: txt[0]
        #'icon_emoji': txt[1]
    }
    url = "https://hooks.slack.com/services/" + args.slack_auth_token
    data = json.dumps(params)
    req = urllib2.Request(url, data)
    return urllib2.urlopen(req)


action_text_map = {
    'create_topic' : 'Created topic', #new
    'create_channel' : 'Created channel', #hatching_chick
    'delete_topic' : 'Deleted topic', #recycle
    'delete_channel' : 'Deleted channel', #poultry_leg or egg
    'empty_channel' : 'Emptied channel', #toilet
    'empty_topic' : 'Emptied topic', #cyclone
    'pause_channel' : 'Paused channel', #fuji / construction (sleeping)
    'unpause_channel' : 'Unpaused channel', #volcano / bullettrain_side  (relieved)
    'pause_topic' : 'Paused topic', #non-potable_water
    'unpause_topic' : 'Unpaused topic', #ocean
    'tombstone_topic_producer': 'Tombstoned Topic Producer', #skull
}


def text_from_nsq_body(body):
    try:
        event = json.loads(body)
        topic_txt = event.get('topic', '')
        channel_txt = event.get('channel', '')
        if channel_txt:
            #TODO: make the values tuples and then make it "get" the first index, with the second one
            # being an emoji
            return action_text_map.get(event['action'], event['action']) + " " + channel_txt +\
                " in topic " + topic_txt, event.get('user', 'unknown user')
        else:
            return action_text_map.get(event['action'], event['action']) + " " + topic_txt,\
                event.get('user', 'unknown user')
    except ValueError:
        logging.exception("Invalid json from nsq")


def process_message(message, args):
    msg_txt, user = text_from_nsq_body(message.body)
    if args.verbose:
        logging.warn(msg_txt)
    response = post_to_slack(msg_txt, args, user)
    if args.verbose:
        logging.warn(response.read())
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--slack-auth-token', required=True)
    parser.add_argument('--slack-channel-id', required=True)
    parser.add_argument('--nsq-topic', required=True)
    parser.add_argument('--nsq-channel', default='nsqadmin2slack')
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
