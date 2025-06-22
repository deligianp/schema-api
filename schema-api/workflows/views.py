import base64

from django.conf import settings
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from semantic_version import Version

from api.constants import TaskStatus
from api_auth.auth import ApiTokenAuthentication
from api_auth.permissions import IsUser, IsContextMember
from util.paginators import ApplicationPagination
from workflows.filters import WorkflowFilter
from workflows.serializers import WorkflowSerializer, WorkflowsListQPSerializer, WorkflowsFullListSerializer, \
    WorkflowsDetailedListSerializer, WorkflowsBasicListSerializer, WorkflowDefinitionSerializer
from workflows.services import WorkflowService, WorkflowDefinitionService


# Create your views here.
class WorkflowsAPIView(APIView):
    authentication_classes = [ApiTokenAuthentication] if settings.USE_AUTH else []
    permission_classes = [IsAuthenticated, IsUser, IsContextMember] if settings.USE_AUTH else []

    @extend_schema(
        summary='Submit a new workflow.',
        description='Submits a new workflow in native SCHEMA workflow specification',
        tags=['Workflows'],
        request=WorkflowSerializer,
        responses={
            201: OpenApiResponse(
                description='Submitted workflow specification was validated and successfully parsed'
            ),
            400: OpenApiResponse(
                description='Workflow request was invalid. Response will contain information about potential errors in the '
                            'request.'
            ),
            401: OpenApiResponse(
                description='Authentication failed. API could not determine the identity of the requesting entity'
            ),
            403: OpenApiResponse(
                description='Authorization failed. Either requesting entity does not have necessary permissions or '
                            'the requested resource claims exceed the currently approved quotas'
            )
        }
    )
    def post(self, request):
        workflow_executor_serializer = WorkflowSerializer(data=request.data)
        workflow_executor_serializer.is_valid(raise_exception=True)

        validated = workflow_executor_serializer.validated_data

        ws = WorkflowService(request.user, request.context)
        workflow= ws.submit_workflow(**validated)

        return Response(status=status.HTTP_201_CREATED, data=WorkflowSerializer(workflow).data)

    @extend_schema(
        summary='List submitted workflows',
        description='List all workflows that have been submitted',
        tags=['Workflows'],
        parameters=[
            OpenApiParameter('search', OpenApiTypes.STR, OpenApiParameter.QUERY,
                             description='Name or UUID part to filter workflows on', required=False,
                             allow_blank=False, many=False, ),
            OpenApiParameter('status', OpenApiTypes.STR, OpenApiParameter.QUERY,
                             description='Status to filter workflows on', required=False,
                             allow_blank=False, many=False, enum=[x.label for x in TaskStatus]),
            OpenApiParameter('before', OpenApiTypes.DATETIME, OpenApiParameter.QUERY,
                             description='Retrieve workflows submitted before this date', required=False,
                             allow_blank=False, many=False),
            OpenApiParameter('after', OpenApiTypes.DATETIME, OpenApiParameter.QUERY,
                             description='Retrieve workflows submitted after this date', required=False,
                             allow_blank=False, many=False),
            OpenApiParameter('order', OpenApiTypes.STR, OpenApiParameter.QUERY,
                             description='Order of returned workflows', required=False,
                             allow_blank=False, many=False,
                             enum=['uuid', '-uuid', 'status', '-status', 'submitted_at', '-submitted_at'])

        ],
        responses={
            200: OpenApiResponse(
                description='A list of the filtered workflows is returned',
                response=WorkflowsFullListSerializer(many=True)
            ),
            400: OpenApiResponse(
                description='Workflow request was invalid. Response will contain information about potential errors in the '
                            'request.'
            ),
            401: OpenApiResponse(
                description='Authentication failed. API could not determine the identity of the requesting entity'
            ),
            403: OpenApiResponse(
                description='Authorization failed. Either requesting entity does not have necessary permissions or '
                            'the requested resource claims exceed the currently approved quotas'
            )
        }
    )
    def get(self, request):
        workflows_service = WorkflowService(request.user, request.context)
        workflows = workflows_service.get_workflows()

        wf_filter = WorkflowFilter(request.GET, queryset=workflows)
        if not wf_filter.is_valid():
            raise ValidationError(wf_filter.errors)
        filtered_qs = wf_filter.qs

        paginator = ApplicationPagination()
        paginated_workflows = paginator.paginate_queryset(filtered_qs, request)


        workflows_query_params_serializer = WorkflowsListQPSerializer(data=request.query_params.dict())
        workflows_query_params_serializer.is_valid(raise_exception=True)
        query_params = workflows_query_params_serializer.validated_data

        if query_params['view'] == 'basic':
            serializer_class = WorkflowsBasicListSerializer
        elif query_params['view'] == 'detailed':
            serializer_class = WorkflowsDetailedListSerializer
        else:
            serializer_class = WorkflowsFullListSerializer

        # Serialize data
        serializer = serializer_class(paginated_workflows, many=True)

        # Return paginated response
        return paginator.get_paginated_response(serializer.data)


class WorkflowDetailsAPIView(APIView):

    authentication_classes = [ApiTokenAuthentication] if settings.USE_AUTH else []
    permission_classes = [IsAuthenticated, IsUser, IsContextMember] if settings.USE_AUTH else []

    @extend_schema(
        summary='Retrieve a submitted workflows',
        description='Retrieve a submitted workflow based on its assigned UUID',
        tags=['Workflows'],
        responses={
            200: OpenApiResponse(
                description='The retrieved workflow is returned',
                response=WorkflowSerializer
            ),
            400: OpenApiResponse(
                description='Workflow request was invalid. Response will contain information about potential errors in the '
                            'request.'
            ),
            401: OpenApiResponse(
                description='Authentication failed. API could not determine the identity of the requesting entity'
            ),
            403: OpenApiResponse(
                description='Authorization failed. Either requesting entity does not have necessary permissions or '
                            'the requested resource claims exceed the currently approved quotas'
            ),
            404: OpenApiResponse(
                description='No workflow with the provided UUID was found, for the authenticated user, inside the '
                            'corresponding execution context'
            )
        }
    )
    def get(self, request, uuid):
        ws = WorkflowService(request.user, request.context)
        workflow = ws.get_workflow(uuid)

        return Response(status=status.HTTP_200_OK, data=WorkflowSerializer(workflow).data)


class WorkflowCancelAPIView(APIView):
    authentication_classes = [ApiTokenAuthentication] if settings.USE_AUTH else []
    permission_classes = [IsAuthenticated, IsContextMember] if settings.USE_AUTH else []

    def post(self, request, uuid):
        ws = WorkflowService(request.user, request.context)
        ws.cancel(uuid)

        return Response(status=status.HTTP_202_ACCEPTED)


class WorkflowDefinitionAPIView(APIView):
    authentication_classes = [ApiTokenAuthentication] if settings.USE_AUTH else []
    permission_classes = [IsAuthenticated, IsContextMember] if settings.USE_AUTH else []

    def post(self, request):
        workflow_definition_serializer = WorkflowDefinitionSerializer(data=request.data)
        workflow_definition_serializer.is_valid(raise_exception=True)

        validated = workflow_definition_serializer.validated_data

        version = Version(validated['version']) if validated.get('version', None) else None
        definition = base64.b64decode(validated['content'].encode('utf-8')).decode('utf-8')

        wss = WorkflowDefinitionService(request.user, request.context)
        workflow = wss.run_workflow(definition=definition, language=validated['language'], version=version)

        return Response(status=status.HTTP_201_CREATED, data=WorkflowSerializer(workflow).data)