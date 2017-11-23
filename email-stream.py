import googleapiclient.discovery
import google.oauth2.credentials

import math
import sys
import time

import boto3
import logging
logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)

import os
API_SERVICE_NAME = 'gmail'
API_VERSION = 'v1'

dynamodb = boto3.resource('dynamodb')
tokens = dynamodb.Table('tokens')
last_interaction = dynamodb.Table('last_interaction')

def get_creds(email_address):
    response = tokens.get_item(Key={'key':email_address})['Item']
    del response['key']
    del response['timestamp']
    creds = google.oauth2.credentials.Credentials(**response)
    return creds

def already_interacting(email_address):
    try:
        item = last_interaction.get_item(Key={"key":email_address})
        if 'Item' in item:
            last_time = item['Item']['time']
            return time.time() - float(last_time) < 3600
        else:
            logging.error("{} did not have a last interaction time.  See: {}".format(email_address,item))
            return False
    except Exception, e:
        logging.error('Issue with already_interacting function')
        logging.error(e)
        return False

def interact_with_user(email_address):
    last_interaction.put_item(Item={'key':email_address,"time":str(time.time())})
    logging.error('we got one!!')
    import email
    import smtplib
    sender_address=os.environ['SENDING_ADDRESS']
    password = os.environ['PASSWORD']
    message = "From: %s\r\nSubject: %s\r\nTo: %s\r\n\r\n" % (sender_address,"Pre-write with SendVibe!",email_address) + \
    "Hey there!  Thanks again for choosing SendVibe!!\n\n"+ \
    "I saw that you started a draft, and so I wanted to introduce you to a pre-writing exercise that I thought might be helpful:\n\n"+ \
    """
It's called "Scripting" and it comes from our friends over at MindTools.

It can often be hard to know how to put your feelings across clearly and confidently to someone when you need to assert yourself. The scripting technique can help here. It allows you to prepare what you want to say in advance, using a four-pronged approach that describes:

1. The event. Tell the other person exactly how you see the situation or problem.

"Janine, the production costs this month are 23 percent higher than average. You didn't give me any indication of this, which meant that I was completely surprised by the news."

2. Your feelings. Describe how you feel about the situation and express your emotions clearly.

"This frustrates me, and makes me feel like you don't understand or appreciate how important financial controls are in the company."

3. Your needs. Tell the other person exactly what you need from her so that she doesn't have to guess.

"I need you to be honest with me, and let me know when we start going significantly over budget on anything."

4. The consequences. Describe the positive impact that your request will have for the other person or the company if your needs are met successfully.

"If you do this we will be in a good position to hit our targets and may get a better end-of-year bonus."



Now it's YOUR turn!  Hit reply to this email and scroll down so you can type your answers in the spaces below:

1. The event. Tell the other person exactly how you see the situation or problem.




2. Your feelings. Describe how you feel about the situation and express your emotions clearly.




3. Your needs. Tell the other person exactly what you need from her so that she doesn't have to guess.




4. The consequences. Describe the positive impact that your request will have for the other person or the company if your needs are met successfully.




Send your email to me after you type your answers in the spaces above!  It's okay if it's still a rough draft when you send it to me. After you're done with your pre-writing, you can go back to drafting your original email with assertive confidence!

If you liked this pre-writing tool, you should know it was shamelessly plagiarized from our friends over at MindTools.  Check our more tools from them by visiting <https://www.mindtools.com/pages/article/Assertiveness.htm>

Best,
SendVibe
    """

    s = smtplib.SMTP(host='smtp.gmail.com', port=587)
    s.starttls()
    s.login(sender_address, password)
    s.sendmail(sender_address,email_address,message)
    return None

def lambda_handler(event, context):
    logging.error(event)
    for record in event['Records']:
        ## Here's a sample sub-record: {u'emailAddress': {u'S': u'send.vibe@gmail.com'}, u'historyId': {u'N': u'27385'}}
        ## Extract the data from the record
        try:
            old = record['dynamodb']['OldImage']
            email_address = old['emailAddress']['S']
            historyId = old['historyId']['N']
        except Exception, e:
            logging.error("Something wrong with record")
            logging.error(record)
            logging.error(e)
            continue

        if already_interacting(email_address):
            logging.error("already interacting!")
            continue

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
                        interact_with_user(email_address)
                        return "Now we are interacting"
                except Exception, e:
                    logging.error("Issue with email responses")
                    logging.error(e)
                    continue

    logging.error("Nothing of note")
    return 'Hello from Lambda email-stream!'
