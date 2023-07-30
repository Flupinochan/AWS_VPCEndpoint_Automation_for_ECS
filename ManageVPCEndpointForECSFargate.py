"""
▼Title
    Automation VPC Endpoints
▼Author
    Flupinochan
▼Version
    1.0
▼Execution Environment
    Python 3.10 / For Lambda
▼Overview
    Automate the creation and deletion of VPC Endpoints needed for AWS ECS using CloudFormation
▼Remarks
    ★Caution
    Gateway endpoints for Amazon S3 must be created in advance and manually
    Service Name : com.amazonaws.{region_name}.s3
"""

import os
import sys
import boto3

from botocore.exceptions import ClientError, BotoCoreError
from botocore.config import Config
from LoggingClass import LoggingClass



# ----------------------------------------------------------------------
# Constant Definition
# ----------------------------------------------------------------------

# Log level (default is INFO)
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

# Retry counts for client or resource API use
RETRY_COUNT = int(os.environ.get('RETRY_COUNT', 3))

# Used for VPC Endpoint(CloudFormation)
VPC_ID = os.environ['VPC_ID']
SUBNET_IDS = os.environ['SUBNET_IDS'].split(',')
SECURITY_GROUP_IDS = os.environ['SECURITY_GROUP_IDS'].split(',')
REGION = os.environ['REGION']

# create or delete
OPERATION = os.environ['OPERATION']



# ----------------------------------------------------------------
# Global Variable Definition
# ----------------------------------------------------------------

# Set arguments like retry counts and region when using client or resource API
config = Config(
    region_name=REGION,
    retries={
        'max_attempts': RETRY_COUNT,
        'mode': 'standard'
    }
)



# ----------------------------------------------------------------------
# Logger Configuration
# ----------------------------------------------------------------------

# Get Logger object. Use this for log output

logger = LoggingClass(LOG_LEVEL)
log = logger.get_logger()

# Usage Example
# log.info("Test")

# CloudFormation API & Template
client = boto3.client('cloudformation')

stack_name = 'VPCEndpointforECS'

template = """
Parameters:
  Region:
    Type: String
    Description: The AWS region for the VPC Endpoints
    Default: {region}

Resources:
  CloudWatchLogsEndpoint:
    Type: AWS::EC2::VPCEndpoint
    Properties:
      VpcId: '{vpc_id}'
      ServiceName: !Sub 'com.amazonaws.{region}.logs'
      VpcEndpointType: Interface
      SubnetIds: {subnet_ids}
      SecurityGroupIds: {security_group_ids}
      PrivateDnsEnabled: true

  ECRApiEndpoint:
    Type: AWS::EC2::VPCEndpoint
    Properties:
      VpcId: '{vpc_id}'
      ServiceName: !Sub 'com.amazonaws.{region}.ecr.api'
      VpcEndpointType: Interface
      SubnetIds: {subnet_ids}
      SecurityGroupIds: {security_group_ids}
      PrivateDnsEnabled: true

  ECRDkrEndpoint:
    Type: AWS::EC2::VPCEndpoint
    Properties:
      VpcId: '{vpc_id}'
      ServiceName: !Sub 'com.amazonaws.{region}.ecr.dkr'
      VpcEndpointType: Interface
      SubnetIds: {subnet_ids}
      SecurityGroupIds: {security_group_ids}
      PrivateDnsEnabled: true
""".format(region=REGION, vpc_id=VPC_ID, subnet_ids=SUBNET_IDS, security_group_ids=SECURITY_GROUP_IDS)



# ----------------------------------------------------------------------
# Main Process
# ----------------------------------------------------------------------
def main():

    # sys._getframe().f_code.co_name) will give the function name
    log.debug("{}() Process start".format(sys._getframe().f_code.co_name))

    # create or delete VPC Endpoints
    if OPERATION == 'create':
        create_endpoints()
    elif OPERATION == 'delete':
        delete_endpoints()



    log.debug("{}() Process end".format(sys._getframe().f_code.co_name))









def create_endpoints():
    response = client.create_stack(
        StackName=stack_name,
        TemplateBody=template,
        Capabilities=[
            'CAPABILITY_IAM',
            'CAPABILITY_NAMED_IAM',
            'CAPABILITY_AUTO_EXPAND',
        ],
    )

def delete_endpoints():
    response = client.delete_stack(
        StackName=stack_name
    )












# ----------------------------------------------------------------------
# Entry Point (program starting point)
# ----------------------------------------------------------------------
def lambda_handler_entrypoint(event, context):

    log.debug("{}() Process start".format(sys._getframe().f_code.co_name))

    try:
        main()

    except ClientError as e:
        # Error handling for AWS API
        error_message = e.response['Error']['Message']
        log.error("An error occurred with the AWS API.")
        log.error(error_message, exc_info=True)

    except BotoCoreError as e:
        # Error handling for boto3 SDK
        error_message = str(e)
        log.error("An error occurred with the boto3 library.")
        log.error(error_message, exc_info=True)

    except Exception as e:
        # Error handling for other unexpected errors
        error_message = str(e)
        log.error("An unexpected error occurred. There may be a syntax error in the code.")
        log.error(error_message, exc_info=True)

    finally:
        log.debug("{}() Process end".format(sys._getframe().f_code.co_name))
        log.info('Processing completed successfully')
