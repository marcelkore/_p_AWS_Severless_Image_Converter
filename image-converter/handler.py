import json
import logging
import os
import random
import sys
import uuid
from datetime import datetime
from io import BytesIO
from turtle import st

import boto3
import requests
from aws_lambda_typing import context as context_
from aws_lambda_typing import events
from PIL import Image, ImageOps

# get the current file name
script_name = os.path.basename(sys.argv[0])

# aws logging uses print statements to log directly to CloudWatch
print(f"Starting {script_name} Script")

# handler for s3 bucket
s3: str = boto3.client("s3")

# thumbnail size set at the environment level
size: str = int(os.environ["THUMBNAIL_SIZE"])

# dynamodb table name set at the environment level
dbtable: str = str(os.environ["DYNAMODB_TABLE"])

# handler for dynamo db
dynamodb = boto3.resource(
    "dynamodb", region_name=str(os.environ["REGION_NAME"])
)


def get_s3_image(bucket: str, key: str) -> Image:
    """Gets an image from S3

    Args:
        bucket (str): bucket name
        key (str): Link to the image

    Returns:
        _type_: PIL Image object
    """

    try:
        response = s3.get_object(Bucket=bucket, Key=key)

    except Exception as e:
        print(e)
        raise e
    # read the image from the response
    image_content = response["Body"].read()
    # get the results in bytes and create an image
    file = BytesIO(image_content)

    # create a PIL image from the file
    image = Image.open(file)

    return image


def image_to_thumbnail(image: str) -> Image:
    """Function receives an image and returns a thumbnail

    Args:
        image (str): image to be converted to thumbnail

    Returns:
        Image: resized image
    """
    return ImageOps.fit(image, (size, size), Image.ANTIALIAS)


def new_filename(key: str) -> str:
    """Generates a new filename for the thumbnail

    Args:
        key (str):  Link to the image

    Returns:
        (str): a new filename with postfix _thumbnail.png
    """

    key_split = key.rsplit(".", 1)
    return key_split[0] + "_thumbnail.png"


def upload_to_s3(bucket: str, key: str, image: str, img_size: int) -> str:
    """Uploads an image to S3

    Args:
        bucket (str): bucket name
        key (str): Link to the image
        image (str): image to be uploaded
        image_size (int): size of the image
    Returns:
        (str): URL to the image
    """

    # save the image to a BytesIO object
    out_thumbnail = BytesIO()

    image.save(out_thumbnail, "PNG")
    out_thumbnail.seek(0)

    response = s3.put_object(
        Bucket=bucket,
        ACL="public-read",
        Key=key,
        Body=out_thumbnail,
        ContentType="image/png",
    )

    print(response)

    url = "{}/{}/{}".format(s3.meta.endpoint_url, bucket, key)

    # save image url to dynamoDB
    save_thumbnail_url_to_dynamodb(url, img_size)

    return url


def image_converter(event: events, context: context_.Context) -> str:
    """Main handler function for the Lambda function.

    Calls all helper functions to convert the image.

    Args:
        event (events): data that is passed to the function
        context (context_.Context): provides contextual information to the function

    Returns:
        (str): json string with response
    """

    print("EVENT:::", event)

    # parse event data
    bucket = event["Records"][0]["s3"]["bucket"]["name"]
    key = event["Records"][0]["s3"]["object"]["key"]
    img_size = event["Records"][0]["s3"]["object"]["size"]

    if not key.endswith("_thumbnail.png"):
        image = get_s3_image(bucket, key)

        # resize the image
        thumbnail = image_to_thumbnail(image)

        thumbnail_key = new_filename(key)

        url = upload_to_s3(bucket, thumbnail_key, thumbnail, img_size)

        return url


def save_thumbnail_url_to_dynamodb(url_path: str, img_size: int) -> str:
    """Saves the thumbnail url to dynamodb

    Args:
        url_path (str): path to the thumbnail in s3
        image_size(str): size of the image

    Returns:
        (str): json string with response
    """
    # get ratio of the bigger image and the thumbnail - approx
    toint = float(img_size * 0.53) / 1000

    table = dynamodb.Table(dbtable)

    response = table.put_item(
        Item={
            "id": str(uuid.uuid4()),
            "url": str(url_path),
            "approxReducedSize": str(toint) + str(" KB"),
            "createdAt": str(datetime.now()),
            "updatedAt": str(datetime.now()),
        }
    )

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(response),
    }


def s3_get_time(event: events, context: context_.Context) -> str:
    """Get the time of the last image in the S3 bucket

    Args:
        event (events): data that is passed to the function
        context (context_.Context): provides contextual information to the function

    Returns:
        (str): json string with response
    """
    table = dynamodb.Table(dbtable)

    response = table.get_item(Key={"id": event["pathParameters"]["id"]})

    item = response["Item"]

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(item),
        "isBase64Encoded": False,
    }


def s3_delete_item(event: events, context: context_.Context) -> str:
    """Function to delete an record from the dynamodb table

    Args:
        event (events): data that is passed to the function
        context (context_.Context): provides contextual information to the function

    Returns:
        (str): json string with response
    """
    item_id = event["pathParameters"]["id"]

    # set the default error response
    response = {
        "statusCode": 500,
        "body": json.dumps(
            {f"message": "Internal Server Error deleting {item_id}"}
        ),
    }

    table = dynamodb.Table(dbtable)

    response = table.delete_item(Key={"id": item_id})

    all_good_response = {"deleted": True, "itemDeletedId": item_id}

    # if delete was successful, return a success response
    if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
        response = {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(all_good_response),
        }
    return response


def s3_get_thumbnail_urls(event: events, context: context_.Context) -> str:
    """Gets all the thumbnail urls from the dynamodb table

    Args:
        event (events): data that is passed to the function
        context (context_.Context): provides contextual information to the function

    Returns:
        (str): json string with returned data
    """
    table = dynamodb.Table(dbtable)

    # list of items retrieved from dynamodb
    response = table.scan()

    data = response["Items"]

    # paginate through the results in a loop
    while "LastEvaluatedKey" in response:  # while response has a value
        response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        data.extend(response["Items"])

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(data),
    }
