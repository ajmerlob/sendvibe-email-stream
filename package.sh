rm lambda-email-stream.zip
cd env/lib/python2.7/site-packages/
zip -r9 ../../../../lambda-email-stream.zip *
cd ../../../../
zip -g lambda-email-stream.zip email-stream.py
