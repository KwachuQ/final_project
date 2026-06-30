import pytest
from moto import mock_aws


@mock_aws
def test_upload_and_retrieve(mock_s3):
    from app.s3 import upload_file, get_s3_client
    from app.settings import get_settings
    upload_file("test.csv", b"hello")
    obj = get_s3_client().get_object(Bucket=get_settings().AWS_BUCKET_NAME, Key="test.csv")
    assert obj["Body"].read() == b"hello"

@mock_aws
def test_delete_file(mock_s3):
    from app.s3 import upload_file, delete_file, get_s3_client
    from app.settings import get_settings
    upload_file("del.csv", b"data")
    delete_file("del.csv")
    import botocore.exceptions
    with pytest.raises(botocore.exceptions.ClientError):
        get_s3_client().get_object(Bucket=get_settings().AWS_BUCKET_NAME, Key="del.csv")
