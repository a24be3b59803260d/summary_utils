import json
from argparse import ArgumentParser
import xml.etree.cElementTree as et


class TwitterArchiveGrapher:

    def __init__(self, args):
        self.graph_name = args.graph_name
        self.mentions = args.mentions
        self.urls = args.urls
        self.tlds = args.tlds
        self.verbose = args.verbose
        if args.all:
            self.mentions = True
            self.urls = True
            self.tlds = True

        if self.verbose:
            print("Args: %s" % args)

        self.users = dict()
        self.tweets = dict()
        self.entities = dict()
        self.entities['hashtags'] = set()
        self.entities['symbols'] = set()
        self.entities['urls'] = dict()
        self.entities['tlds'] = set()
        self.edge_attr_keys = dict()
        self.node_attr_keys = dict()

        # add override values for attr types
        self.edge_attr_keys['source'] = 'string'
        self.edge_attr_keys['target'] = 'string'
        self.edge_attr_keys['entity_type'] = 'string'
        self.edge_attr_keys['interaction'] = 'string'
        self.edge_attr_keys['shared interaction'] = 'string'
        self.node_attr_keys['entity_type'] = 'string'

        pttgt = dict()
        pttgt[str] = 'string'
        pttgt[None] = 'string'
        self.pytype_to_graphml_type = pttgt

    def upsert_user(self, user):

        user['nice_label'] = user['screen_name']

        if user['id_str'] not in self.users:
            user.pop('id')
            self.users[user['id_str']] = user

        # add keynames/types to attr info
        for k in user:

            type_str = 'string'

            if type(user[k]) in self.pytype_to_graphml_type:
                type_str = self.pytype_to_graphml_type[
                    type(user[k])
                ]

            self.node_attr_keys[k] = type_str

        # TODO finish upsert

    def upsert_tweet(self, tweet):

        tweet['nice_label'] = tweet['text']

        if tweet['id_str'] not in self.tweets:
            tweet.pop('id')
            self.tweets[tweet['id_str']] = tweet

        # add keynames/types to attr info
        for k in tweet:

            type_str = 'string'

            if type(tweet[k]) in self.pytype_to_graphml_type:
                type_str = self.pytype_to_graphml_type[
                    type(tweet[k])
                ]

            self.node_attr_keys[k] = type_str

        # TODO finish upsert

    def __tweet_to_node_and_edges(self, graph, tweet):
        """ All nodes must be added before edges for Cytoscape
        to correctly insert everything """

        # add tweet to graph first
        se = et.SubElement(
            graph, "node",
            id="tweet_id:%s" % tweet["id_str"])

        et.SubElement(se, 'data', key='entity_type').text = "tweet"
        et.SubElement(se, 'data', key='name').text = tweet['nice_label']

        for k in tweet:
            et.SubElement(
                se, 'data',
                key=k
            ).text = str(tweet[k])

        # add direct tweet edge
        se = et.SubElement(
            graph, "edge",
            id="tweet_id:%s" % tweet["id_str"],
            source="user_id:%s" % tweet['user_id'],
            target="tweet_id:%s" % tweet['id_str'])

        et.SubElement(se, 'data', key='entity_type').text = "tweeted"

        et.SubElement(se, 'data', key='interaction').text = "tweet"

        # add retweet edge
        if 'retweeted_user_id' in tweet:

            rtse = et.SubElement(
                graph, "edge",
                id="tweet_id:%s" % tweet["id_str"],
                source="tweet_id:%s" % tweet['id_str'],
                target="tweet_id:%s" % tweet['retweeted_tweet_id'])

            et.SubElement(rtse, 'data', key='entity_type').text = "retweet"

            et.SubElement(rtse, 'data', key='interaction').text = "retweet"

        # add urls, symbols, and hashtags to and edge(s)

        # hashtags
        for e in tweet['entities']['hashtags']:

            ese = et.SubElement(
                graph, "edge",
                source="tweet_id:%s" % tweet['id_str'],
                target="hashtag:%s" % e['text'])

            et.SubElement(
                ese, 'data',
                key='entity_type').text = "used_hashtag"

            et.SubElement(
                ese, 'data',
                key='interaction').text = "used_hashtag"

        # symbols
        for e in tweet['entities']['symbols']:

            ese = et.SubElement(
                graph, "edge",
                source="tweet_id:%s" % tweet['id_str'],
                target="symbol:%s" % e['text'])

            et.SubElement(
                ese, 'data',
                key='entity_type').text = "used_symbol"

            et.SubElement(
                ese, 'data',
                key='interaction').text = "used_symbol"

        # handle user mentions
        if self.mentions:
            for e in tweet['entities']['user_mentions']:

                ese = et.SubElement(
                    graph, "edge",
                    source="tweet_id:%s" % tweet['id_str'],
                    target="user_id:%s" % e['id_str'])

                et.SubElement(
                    ese, 'data',
                    key='entity_type').text = "user_mention"

                et.SubElement(
                    ese, 'data',
                    key='interaction').text = "user_mention"

        # handle URLs (TLDs below) and edges
        if self.urls:
            for e in self.entities['urls']:

                ese = et.SubElement(
                    graph, "edge",
                    source="tweet_id:%s" % tweet['id_str'],
                    target="url:%s" % e)

                et.SubElement(
                    ese, 'data',
                    key='entity_type').text = "linked_url"

                et.SubElement(
                    ese, 'data',
                    key='interaction').text = "linked_url"

        # handle TLDs edges
        if self.tlds:
            for tld in self.entities['tlds']:

                # ignore twitter.com for sanity
                if "twitter.com" != tld:

                    ese = et.SubElement(
                        graph, "edge",
                        source="tweet_id:%s" % tweet['id_str'],
                        target="tld:%s" % tld)

                    et.SubElement(
                        ese, 'data',
                        key='entity_type').text = "linked_tld"

                    et.SubElement(
                        ese, 'data',
                        key='interaction').text = "linked_tld"

    # extract user(s) from tweet and add them to user dict
    def add_tweets(self, tweets):

        # extract user, retweeted user, and tweet info
        for tweet in tweets:

            # ignore rate limit tweets
            if 'limit' not in tweet:

                # if retweeted
                if "retweeted_status" in tweet:
                    retweet = tweet.pop('retweeted_status')
                    tweet['retweeted_tweet_id'] = retweet['id_str']
                    retweet['user_id'] = retweet['user']['id_str']
                    tweet['retweeted_user_id'] = retweet['user_id']
                    self.upsert_user(
                        retweet.pop('user', None))
                    self.upsert_tweet(
                        retweet
                    )

                tweet['user_id'] = tweet['user']['id_str']
                self.upsert_user(
                    tweet.pop('user', None)
                )

                self.upsert_tweet(
                    tweet
                )

    # convert stored tweets to graphml format
    def to_graphml(self):
        graphml = et.Element(
            'graphml', xmlns="http://graphml.graphdrawing.org/xmlns")
        graphml.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
        graphml.set("xsi:schemaLocation", "http://graphml.graphdrawing.org/xmlns \
            http://graphml.graphdrawing.org/xmlns/1.0/graphml.xsd")

        # generate node attributes
        for k in self.edge_attr_keys:
            se = et.SubElement(
                graphml, 'key')
            se.set('for', 'edge')
            se.set('id', k)
            se.set('attr.name', k)
            se.set('attr.type', 'string')

        # generate attributes
        for k in self.node_attr_keys:
            se = et.SubElement(
                graphml, 'key')
            se.set('for', 'node')
            se.set('id', k)
            se.set('attr.name', k)
            se.set('attr.type', 'string')

        # set up graph node
        graph = et.SubElement(
            graphml, 'graph', id=self.graph_name, edgedefault="directed")

        ###################
        # create nodes BEFORE edges

        # hashtag, symbol, user_mention, url, tld nodes
        for tweet_id in self.tweets:
            # self.entities['hashtags'].add(e['text'])
            tweet = self.tweets[tweet_id]
            hashtags = [x['text'] for x in tweet['entities']['hashtags']]
            self.entities['hashtags'].update(hashtags)
            symbols = [x['text'] for x in tweet['entities']['symbols']]
            self.entities['symbols'].update(symbols)

            if self.mentions:
                # add any missing users from mentions by tweet
                # since we have already extracted all users we only need
                # add mention (partial user info) for those missing keys
                for um in tweet['entities']['user_mentions']:
                    if um['id_str'] not in self.users:
                        self.upsert_user(um)

            # extract urls and TLDs
            for url in tweet['entities']['urls']:
                # using expanded url as key (this might be dangerous)
                if self.urls:
                    self.entities['urls'][url['expanded_url']] = url

                if self.tlds:
                    tld = url['display_url'].split('/')[0]
                    self.entities['tlds'].add(tld)

        # user nodes
        for user_id in self.users:
            user = self.users[user_id]
            se = et.SubElement(
                graph, "node",
                id="user_id:%s" % user_id)

            et.SubElement(se, 'data', key='entity_type').text = "user"

            for k in user:
                et.SubElement(
                    se, 'data',
                    key=k
                ).text = str(user[k])

        # hashtags
        for ht in self.entities['hashtags']:
            se = et.SubElement(
                graph, "node",
                id="hashtag:%s" % ht)
            et.SubElement(se, 'data', key='entity_type').text = "hashtag"

        # symbols
        for s in self.entities['symbols']:
            se = et.SubElement(
                graph, "node",
                id="symbol:%s" % s)
            et.SubElement(se, 'data', key='entity_type').text = "symbol"

        # urls
        if self.urls:
            for u in self.entities['urls']:
                se = et.SubElement(
                    graph, "node",
                    id="url:%s" % u)
                et.SubElement(se, 'data', key='entity_type').text = "url"

        # TLDs
        if self.tlds:
            for tld in self.entities['tlds']:

                # ignore twitter.com for sanity
                if "twitter.com" != tld:
                    se = et.SubElement(
                        graph, "node",
                        id="tld:%s" % tld)
                    et.SubElement(se, 'data', key='entity_type').text = "tld"

        # TODO mentions
        # this might be handled by updated user code

        # tweet nodes and edges
        for tweet_id in self.tweets:
            tweet = self.tweets[tweet_id]
            self.__tweet_to_node_and_edges(graph, tweet)

        tree = et.ElementTree(graphml)
        return tree

    def get_num_processed_tweets(self):
        return len(self.tweets.keys())

    def get_num_users(self):
        return len(self.users.keys())

    def get_num_hashtags(self):
        return len(self.entities['hashtags'])

    def get_num_urls(self):
        return len(self.entities['urls'])

    def get_num_tlds(self):
        return len(self.entities['tlds'])


def main():
    parser = ArgumentParser()
    parser.add_argument("-o", "--output", dest='outfile',
                        default=None,
                        help="output graphml filename")
    parser.add_argument("-g", "--graph-name", dest='graph_name',
                        default="Default Graph Name",
                        help="GraphML network name.")
    parser.add_argument("-m", "--mentions", action="store_true",
                        help="Add nodes and edges for mentions")
    parser.add_argument("-u", "--urls", action="store_true",
                        help="Add nodes and edges for full urls")
    parser.add_argument("-t", "--tlds", action="store_true",
                        help="Add nodes and edges for TLDs")
    parser.add_argument("-a", "--all", action="store_true",
                        help="Node and edges for everything. \
                             WARNING! This creates very large graph files")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument('infile_paths', nargs='+', metavar='INFILE')

    args = parser.parse_args()

    tager = TwitterArchiveGrapher(args)

    for infile in args.infile_paths:
        tweets = [json.loads(t) for t in open(
            infile, 'r', encoding='utf-8')]

        tager.add_tweets(tweets)

    graph = tager.to_graphml()

    # if outfile is supplied, write derivative filename of input
    if args.outfile is None:
        graph.write(args.infile_paths[0] + ".graphml")
    else:
        graph.write(args.outfile)

    print("Tweets Processed: %d" % tager.get_num_processed_tweets())
    print("Users extracted: %d" % tager.get_num_users())
    print("Hashtags extracted: %d" % tager.get_num_hashtags())
    print("TLDs extracted: %d" % tager.get_num_tlds())
    print("Urls extracted: %d" % tager.get_num_urls())

if __name__ == "__main__":
    main()
