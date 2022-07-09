
# Serverless Framework: Image Converter

This lambda function will resize an image posted to an S3 bucket. The image will be resized to a specified image size provided by the user based on the configuration settings.

We then expose an Amazon API Gateway that one can call to get details about the loaded.

The project was done as part of the Udemy Course by Paulo Dichone - Check it awesome content. [Check it out](https://www.udemy.com/course/aws-lambda-serverless/).

### **Architecture**

![](https://koremarcelblog.blob.core.windows.net/box-blog/ELT%20Project.png)


### **Usage**

The main handler function is `handler` and it contains a couple of functions that are used to resize the image.

* get_s3_image : This function will get the s3 image from the bucket.
* image_to_thumbnail : This function will receive an image and resize it (convert to thumbnail)
* new_filename :  This function renames the file by adding an postfix _thumbnail.png
* upload_to_s3 : This function uploads and image to s3 and retrieves the URL
* image_converter : This is the main function that is called to resize the image and upload the resize image to s3


### **Deployment**

In order to deploy the example, you need to run the following command:

```
$ serverless deploy

# to deploy changes related to a specific function
$ serverless deploy --function image-converter
```

After running deploy, you should see output similar to:

```bash
Deploying aws-python-project to stage dev (us-east-1)

✔ Service deployed to stack aws-python-project-dev (112s)

functions:
  hello: aws-python-project-dev-hello (1.5 kB)
```

### **Invocation**

After successful deployment, you can invoke the deployed function by using the following command:

```bash
serverless invoke --function image-converter
```

Which should result in response similar to the following:

```json
{
    "statusCode": 200,
    "body": "{\"message\": \"Go Serverless v3.0! Your function executed successfully!\", \"input\": {}}"
}
```

### **Local development**

You can invoke your function locally by using the following command:

```bash
serverless invoke local --function hello
```

Which should result in response similar to the following:

```
{
    "statusCode": 200,
    "body": "{\"message\": \"Go Serverless v3.0! Your function executed successfully!\", \"input\": {}}"
}
```

### **Bundling dependencies**

In case you would like to include third-party dependencies, you will need to use a plugin called `serverless-python-requirements`. You can set it up by running the following command:

```bash
serverless plugin install -n serverless-python-requirements
```

Running the above will automatically add `serverless-python-requirements` to `plugins` section in your `serverless.yml` file and add it as a `devDependency` to `package.json` file. The `package.json` file will be automatically created if it doesn't exist beforehand. Now you will be able to add your dependencies to `requirements.txt` file (`Pipfile` and `pyproject.toml` is also supported but requires additional configuration) and they will be automatically injected to Lambda package during build process. For more details about the plugin's configuration, please refer to [official documentation](https://github.com/UnitedIncome/serverless-python-requirements).
