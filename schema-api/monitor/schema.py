import graphene
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField

from api.models import Task, Executor, MountPoint, Env, TempTag


class TaskType(DjangoObjectType):
    class Meta:
        model = Task


class ExecutorType(DjangoObjectType):
    class Meta:
        model = Executor


class MountPointType(DjangoObjectType):
    class Meta:
        model = MountPoint


class EnvType(DjangoObjectType):
    class Meta:
        model = Env


class TagType(DjangoObjectType):
    class Meta:
        model = TempTag


class Query(graphene.ObjectType):
    tasks = graphene.List(TaskType)
    executors = graphene.List(ExecutorType)

    def resolve_tasks(self, info):
        return Task.objects.all()

    def resolve_executors(self, info):
        return Executor.objects.all()


schema = graphene.Schema(query=Query)
