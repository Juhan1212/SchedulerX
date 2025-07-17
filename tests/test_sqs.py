import boto3
from dotenv import load_dotenv
load_dotenv()

sqs = boto3.client('sqs', region_name='ap-northeast-2')

queue_url = sqs.get_queue_url(QueueName='testQueue')['QueueUrl']

response = sqs.send_message(
    QueueUrl=queue_url,
    MessageBody='테스트 메시지'
)
print(f"Message sent: {response['MessageId']}")