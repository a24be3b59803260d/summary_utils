import json
from argparse import ArgumentParser
import xml.etree.cElementTree as et


class TwitterArchiveGrapher:

    def __init__(self, name):
        self.graph_name = name
        self.users = dict()
        self.tweets = dict()
        self.edge_attr_keys = dict()
        self.node_attr_keys = dict()

        # add override values for attr types
        self.edge_attr_keys['entity_type'] = 'string'
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

        # add tweet to graph first
        se = et.SubElement(
            graph, "node",
            id="tweet_id:%s" % tweet["id_str"])

        et.SubElement(se, 'data', key='entity_type').text = "tweet"

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

        # add retweet edge
        if 'retweeted_user_id' in tweet:

            rtse = et.SubElement(
                graph, "edge",
                id="tweet_id:%s" % tweet["id_str"],
                source="tweet_id:%s" % tweet['id_str'],
                target="tweet_id:%s" % tweet['retweeted_tweet_id'])

            et.SubElement(rtse, 'data', key='entity_type').text = "retweet"

    # extract user(s) from tweet and add them to user dict
    def add_tweets(self, tweets):

        # extract user, retweeted user, and tweet info
        for tweet in tweets:
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
            """
            else:
                tweet['retweeted_user_id'] = 'null'
            """

            tweet['user_id'] = tweet['user']['id_str']
            self.upsert_user(
                tweet.pop('user', None)
            )

            self.upsert_tweet(
                tweet
            )

    # convert stored tweets to graphml format
    def to_graphml(self):
        graphml = et.Element('graphml', xmlns="http://graphml.graphdrawing.org/xmlns")
        graphml.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
        graphml.set("xsi:schemaLocation", "http://graphml.graphdrawing.org/xmlns http://graphml.graphdrawing.org/xmlns/1.0/graphml.xsd")

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
        # create nodes and edges

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


def main():
    parser = ArgumentParser()
    parser.add_argument("-o", "--output", dest='outfile',
                        default=None,
                        help="output graphml filename")
    parser.add_argument("-g", "--graph-name", dest='graph_name',
                        default="Default Graph Name",
                        help="GraphML network name.")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument('infile_paths', nargs='+', metavar='INFILE')

    args = parser.parse_args()

    tager = TwitterArchiveGrapher(args.graph_name)

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


if __name__ == "__main__":
    main()
