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
        ・create/delete com.amazonaws.ap-northeast-1.logs    for CloudWatchLogs
        ・create/delete com.amazonaws.ap-northeast-1.ecr.api for ECR
        ・create/delete com.amazonaws.ap-northeast-1.ecr.dkr for ECR
▼Remarks
    ★Caution
    Gateway endpoints for Amazon S3 must be created in advance and manually
    Service Name : com.amazonaws.{region_name}.s3
"""

import os
import sys
import boto3
import time

from botocore.exceptions import ClientError, BotoCoreError
from botocore.config import Config
from LoggingClass import LoggingClass

## proxy container code 137 out of memory because not alpine
## ['./run.sh'] or bash -c ./run.sh
## squid shutdown time must be less than 10 seconds → shutdown_lifetime 1 seconds
## ECS "stopTimeout": 60
## other container is essential false
###### ECS code 137 → stopping by essential true is a specification so stepfunctions catch


# ----------------------------------------------------------------------
# Constant Definition
# ----------------------------------------------------------------------

try:
    # Log level (default is INFO)
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

    # Retry counts for client or resource API use
    RETRY_COUNT = int(os.environ.get('RETRY_COUNT', 3))

    # Used for VPC Endpoint(CloudFormation)
    # Subnets and Security Groups can be specified multiple times, separated by commas
    VPC_ID = os.environ['VPC_ID']
    SUBNET_IDS = os.environ['SUBNET_IDS'].split(',')
    SECURITY_GROUP_IDS = os.environ['SECURITY_GROUP_IDS'].split(',')
    REGION = os.environ['REGION']

except KeyError as e:
    raise Exception("Required environment variable not set : {}".format(e))



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

# CloudFormation API & Template
client = boto3.client('cloudformation')

stack_name = 'VPCEndpointsForECS-Stack'

# Please note that tags cannot be attached
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
# Logger Configuration
# ----------------------------------------------------------------------

# Get Logger object. Use this for log output

logger = LoggingClass(LOG_LEVEL)
log = logger.get_logger()

# Usage Example
# log.info("Test")



# ----------------------------------------------------------------------
# Main Process
# ----------------------------------------------------------------------
def main(operation):

    # sys._getframe().f_code.co_name) will give the function name
    log.debug("{}() Process start".format(sys._getframe().f_code.co_name))

    # create or delete VPC Endpoints
    if operation == 'create':
        create_endpoints()
        wait_for_create_endpoints_complete()

    elif operation == 'delete':
        delete_endpoints()

    log.debug("{}() Process end".format(sys._getframe().f_code.co_name))



# ----------------------------------------------------------------------
# Create VPC Endpoints
# ----------------------------------------------------------------------
def create_endpoints():

    log.debug("{}() Process start".format(sys._getframe().f_code.co_name))

    response = client.create_stack(
        StackName=stack_name,
        TemplateBody=template,
        Tags=[
            {
                'Key': 'Name',
                'Value': stack_name
            }
        ]
    )

    log.info("create stack name : {}".format(stack_name))
    log.info("create stack id : {}".format(response['StackId']))

    log.debug("{}() Process end".format(sys._getframe().f_code.co_name))



# ----------------------------------------------------------------------
# Delete VPC Endpoints
# ----------------------------------------------------------------------
def delete_endpoints():

    log.debug("{}() Process start".format(sys._getframe().f_code.co_name))

    client.delete_stack(
        StackName=stack_name
    )

    log.info("delete stack name : {}".format(stack_name))

    log.debug("{}() Process end".format(sys._getframe().f_code.co_name))



# ----------------------------------------------------------------------
# Wait for create_endpoints() completed(Check CloudFormation Stack Status)
# ----------------------------------------------------------------------
def wait_for_create_endpoints_complete():

    log.debug("{}() Process start".format(sys._getframe().f_code.co_name))

    while True:
        response = client.describe_stacks(StackName=stack_name)
        stack_status = response['Stacks'][0]['StackStatus']

        if stack_status == 'CREATE_COMPLETE':
            log.info('Stack creation completed to create VPC Endpoints')
            break

        elif 'FAILED' in stack_status or stack_status == 'ROLLBACK_COMPLETE':
            log.error('Stack creation failed to create VPC Endpoints')
            break

        else:
            log.debug('Stack creation in progress...')
            time.sleep(30)

    log.debug("{}() Process end".format(sys._getframe().f_code.co_name))



# ----------------------------------------------------------------------
# Entry Point (program starting point)
# ----------------------------------------------------------------------
def lambda_handler_entrypoint(event, context):

    # 'create' or 'delete' from StepFunctions Parameters
    operation = event['Payload']['operation']

    log.debug("{}() Process start".format(sys._getframe().f_code.co_name))

    try:
        main(operation)

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