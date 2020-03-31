import boto3, os
import pandas as pd

def create_bucket(bucket_name, connection):
    '''
    function to create and S3 Bucket in your current region
    
    input: the naming for your bucket, connection
    output: bucket name, response
    '''
    
    # start a session
    session = boto3.session.Session()
    # current region
    region = session.region_name
    # create the bucket
    try:
        bucket_resp = connection.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={
            'LocationConstraint': region})
    except:
        print('Error creating bucket. Possibilities:')
        print('\tbucket name may be already taken')
        print('\tyou may already have created')
        bucket_resp = None
    print(bucket_name, region)
    return bucket_name, bucket_resp

def available_files(bucket_name = 'geniuslyrics'):
    '''
    show what files are available in the s3 bucket!
    output: list of file names
    '''
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(bucket_name)
    file_names = [x.key for x in bucket.objects.all()]
    return file_names

def download_file(file_name, bucket_name = 'geniuslyrics', save=True):
    
    '''
    download an object from S3, and load into a df
    
    Save: boolean, True - will save to local storage
                   False - will only load to memory
    '''
    s3 = boto3.resource('s3')
    s3_object = s3.Object(bucket_name=bucket_name,
                          key=file_name)
    
    if save:
        s3_object.download_file(file_name)
        df = pd.read_pickle(file_name)
    else:
        s3_object.download_file(file_name)
        df = pd.read_pickle(file_name)
        os.remove(file_name)
        
    df.name = file_name
    
    return df

def upload_file(dataframe, remove = True, bucket_name = 'geniuslyrics'):
    '''
    uploading a dataframe to S3
    must have df.name assigned as the file name
    input: the name of the file, the contents of the file
    '''
    s3 = boto3.resource('s3')
    
    def upload(name, s3=s3):
        s3_object = s3.Object(bucket_name=bucket_name,
                              key=name)
        with open('df', 'wb') as f:
            dataframe.to_pickle(name)
            s3_object.upload_file(name)
            if remove:
                os.remove(name)
            f.close()
        return name
    
    try:
        name = dataframe.name
        name = upload(name=name)
    except AttributeError:
        q = input(prompt='What would you like to call the file?')
        name = upload(name=q)
    
    print(f'{name} successfully uploaded!')
    
def delete_file(file_name, bucket_name = 'geniuslyrics'):
    '''
    delete a file from S3
    input: the name of file you wish to delete
    '''
    
    s3 = boto3.resource('s3')
    s3_object = s3.Object(bucket_name = bucket_name,
                          key = file_name)
    s3_object.delete()
    print(f'{file_name} deleted')