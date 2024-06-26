import datetime

import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from rest_framework.exceptions import NotFound

from api_auth.constants import AuthEntityType
from api_auth.models import AuthEntity
from util.exceptions import ApplicationError


class UploadService:

    def __init__(self, auth_entity: AuthEntity):
        if auth_entity.entity_type != AuthEntityType.USER:
            raise ApplicationError(
                f'{self.__class__.__name__} depends on an AuthEntity of type {AuthEntityType.USER}'
            )
        self.auth_entity = auth_entity
        self.bucket = str(self.auth_entity.uuid)

        self.s3_client = boto3.client('s3',
                                      endpoint_url=settings.S3['URL'],
                                      aws_access_key_id=settings.S3['ACCESS_KEY_ID'],
                                      aws_secret_access_key=settings.S3['SECRET_ACCESS_KEY'],
                                      config=boto3.session.Config(signature_version='s3v4'),
                                      verify=settings.S3['USE_SSL'],
                                      use_ssl=settings.S3['USE_SSL']
                                      )

    def create_upload_request(self, size: int, file_path: str):
        validity_period_seconds = settings.S3['VALIDITY_PERIOD_SECONDS']
        validity_period = datetime.timedelta(seconds=validity_period_seconds)

        current_ref_ts = datetime.datetime.now()
        key = file_path
        expiry = current_ref_ts + validity_period

        max_part_size = settings.S3['MAX_PART_SIZE_BYTES']

        self._create_bucket_if_not_exists()

        if size > max_part_size:
            # Calculate sizes
            part_sizes = [max_part_size] * (size // max_part_size) + [size % max_part_size]

            # Issue new multipart upload creation=
            response = self.s3_client.create_multipart_upload(Bucket=self.bucket, Key=key, Expires=expiry)

            upload_id = response['UploadId']

            urls = []
            for i in range(len(part_sizes)):
                url = self.s3_client.generate_presigned_url(ClientMethod='upload_part',
                                                       Params={'Bucket': self.bucket, 'Key': key, 'PartNumber': i + 1,
                                                               'UploadId': upload_id, 'ContentLength': part_sizes[i]},
                                                       ExpiresIn=validity_period_seconds)
                urls.append({'part': i + 1, 'url': url, 'n_bytes': part_sizes[i]})

            complete_url = self.s3_client.generate_presigned_url(ClientMethod='complete_multipart_upload',
                                                            Params={'Bucket': self.bucket, 'Key': key,
                                                                    'UploadId': upload_id},
                                                            ExpiresIn=validity_period_seconds
                                                            )
            return {
                'type': 'multipart',
                'expiry': expiry,
                'urls': {
                    'parts': urls,
                    'finalize': complete_url
                }
            }
        url = self.s3_client.generate_presigned_url(ClientMethod='put_object',
                                               Params={'Bucket': self.bucket, 'Key': key, 'ContentLength': size},
                                               ExpiresIn=validity_period_seconds)
        return {
            'type': 'simple',
            'expiry': expiry,
            'url': url
        }

    def create_download_request(self, file_path: str):
        key = file_path
        validity_period_seconds = settings.S3['VALIDITY_PERIOD_SECONDS']
        validity_period = datetime.timedelta(seconds=validity_period_seconds)
        current_ref_ts = datetime.datetime.now()
        expiry = current_ref_ts + validity_period
        try:
            self.s3_client.head_object(Bucket=self.bucket, Key=key)
        except ClientError as ex:
            if ex.response['Error']['Code'] == 'NotFound':
                raise NotFound
            raise
        return {
            'expiry': expiry,
            'url': self.s3_client.generate_presigned_url(
                ClientMethod='get_object',
                Params={'Bucket': self.bucket, 'Key': key},
                ExpiresIn=validity_period_seconds
            )
        }

    def _create_bucket_if_not_exists(self):
        try:
            self.s3_client.head_bucket(Bucket=self.bucket)
        except ClientError as ex:
            if ex.response['Error']['Code'] == '404':
                self.s3_client.create_bucket(Bucket=self.bucket)
            else:
                raise
