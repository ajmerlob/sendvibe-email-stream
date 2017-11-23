import googleapiclient.discovery
import google.oauth2.credentials

import math
import sys

import boto3
import logging
logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)

API_SERVICE_NAME = 'gmail'
API_VERSION = 'v1'

dynamodb = boto3.resource('dynamodb')
tokens = dynamodb.Table('tokens')

def get_creds(email_address):
    response = tokens.get_item(Key={'key':email_address})['Item']
    del response['key']
    del response['timestamp']
    creds = google.oauth2.credentials.Credentials(**response)
    return creds

def lambda_handler(event, context):
    logging.error(event)
    for record in event['Records']:
        ## Here's a sample sub-record: {u'emailAddress': {u'S': u'send.vibe@gmail.com'}, u'historyId': {u'N': u'27385'}}
        ## Extract the data from the record
        old = record['dynamodb']['OldImage']
        email_address = old['emailAddress']['S']
        historyId = old['historyId']['N']

        ## Trade the email address for gmail credentials
        creds = get_creds(email_address)
        gmail = googleapiclient.discovery.build(API_SERVICE_NAME, API_VERSION, credentials=creds)

        ## Trade the gmail credentials for the history list
        history_response = gmail.users().history().list(userId='me',startHistoryId=historyId).execute()
        for change in history_response['history']:
            for message in change['messages']:
                email_id = message['id']
                try:
                    ## Extract the email metadata
                    email_response = gmail.users().messages().get(userId='me',id=email_id,format='metadata').execute()
                    if 'DRAFT' not in email_response['labelIds']:
                        continue
                    else:
                        logging.error('we got one!!')
                except Exception, e:
                    logging.error("Issue with email responses")
                    logging.error(e)
                    continue

    return 'Hello from Lambda email-stream!'
